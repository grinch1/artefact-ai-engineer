import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from store import Store
from agent import agent_instructions


class PolicyJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "policies.json").read_text(encoding="utf-8"))
        cls.store = Store.__new__(Store)
        cls.store.policy_sections = cls.policy["company_policies"]["sections"]
        cls.store.policy_facts = {item["section"]: item["facts"]
                                  for item in cls.store.policy_sections}

    def test_public_index_has_sources_and_no_conflicting_contacts(self):
        self.assertEqual(self.policy["schema_version"], 2)
        self.assertRegex(self.policy["company_policies"]["source"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(len(self.store.policy_sections), 15)
        self.assertGreaterEqual(len(self.policy["agent_policies"]["rules"]), 15)
        self.assertGreaterEqual(len(self.policy["application_rules"]["capabilities"]), 5)
        self.assertEqual(len({r["id"] for r in self.policy["agent_policies"]["rules"]}),
                         len(self.policy["agent_policies"]["rules"]))
        self.assertEqual(len({r["id"] for r in self.policy["application_rules"]["capabilities"]}),
                         len(self.policy["application_rules"]["capabilities"]))
        for item in self.store.policy_sections:
            with self.subTest(section=item["section"]):
                self.assertTrue(item["page"] and item["section"] and item["text"])
                self.assertTrue(item["keywords_pt"])
                self.assertNotIn("@", item["text"])
                self.assertIsNone(re.search(r"\(\d{2}\)\s*\d{4,5}", item["text"]))

    def test_customer_questions_find_correct_structured_sections(self):
        examples = {
            "Onde fica a loja?": "1.2",
            "Qual o horário de funcionamento?": "2",
            "Posso parcelar em 10x?": "3.1",
            "Comprei online e me arrependi. Posso devolver?": "4.1",
            "Quanto custa o frete fora de Campo Grande?": "5.2",
            "Qual a garantia dos instrumentos?": "8.1",
            "Como apago meus dados pessoais?": "9",
        }
        for question, expected in examples.items():
            with self.subTest(question=question):
                self.assertEqual(self.store.get_policy(question)["matches"][0]["section"], expected)

    def test_company_agent_and_application_rules_have_distinct_sources(self):
        self.assertEqual(self.policy["company_policies"]["source"]["type"], "supplied_private_pdf")
        self.assertEqual(self.policy["agent_policies"]["source"], "candidate_design_for_this_assistant")
        self.assertEqual(self.policy["application_rules"]["source"],
                         "implemented_prototype_capabilities")
        self.assertEqual(self.store.policy_facts["4.2"]["store_exchange_start_event"], "purchase")
        prompt = agent_instructions(self.store)
        self.assertIn("Não posso cotar frete fora da região metropolitana", prompt)
        self.assertIn("evidências apropriadas", prompt)


if __name__ == "__main__":
    unittest.main()
