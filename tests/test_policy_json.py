import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from store import Store


class PolicyJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((ROOT / "policy.json").read_text(encoding="utf-8"))
        cls.store = Store.__new__(Store)
        cls.store.policy_sections = cls.policy["sections"]
        cls.store.policy_facts = {item["section"]: item["facts"]
                                  for item in cls.policy["sections"]}

    def test_public_index_has_sources_and_no_conflicting_contacts(self):
        self.assertEqual(self.policy["schema_version"], 1)
        self.assertRegex(self.policy["source_pdf_sha256"], r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(len(self.policy["sections"]), 15)
        for item in self.policy["sections"]:
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


if __name__ == "__main__":
    unittest.main()
