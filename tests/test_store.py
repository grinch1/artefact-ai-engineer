import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store, customer_safe_policy_text


class StoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store.__new__(Store)
        cls.store.tables = {
            "products": [
                {"product_id": "1", "name": "Violão Teste", "description": "Aço", "category_id": "1", "price_brl": "1000", "stock_quantity": "2", "status": "active"},
                {"product_id": "2", "name": "Ukulele Teste", "description": "Parece violão", "category_id": "2", "price_brl": "200", "stock_quantity": "3", "status": "active"},
                {"product_id": "3", "name": "Violão Sem Estoque", "description": "", "category_id": "1", "price_brl": "500", "stock_quantity": "0", "status": "active"},
                {"product_id": "4", "name": "Violão Pix", "description": "Teste de centavos", "category_id": "1", "price_brl": "579.90", "stock_quantity": "1", "status": "active"},
            ],
            "orders": [{"order_id": "9", "customer_id": "7", "status": "confirmed", "order_date": "2025-11-01", "estimated_delivery": "", "tracking_code": ""}],
            "customers": [{"customer_id": "7", "email": "demo@example.com"}],
        }
        cls.store.categories = {"1": "Violões", "2": "Ukuleles"}
        cls.store.promotions = {"1": [{"discount_percent": "20"}]}
        cls.store.policy_sections = [{"page": 4, "section": "4.1",
                                      "title": "Direito de Arrependimento",
                                      "text": "Devolução em 7 (sete) dias após o recebimento."}]
        policy = json.loads((Path(__file__).resolve().parents[1] / "policies.json").read_text())
        cls.store.policy_facts = {item["section"]: item.get("facts", {})
                                  for item in policy["company_policies"]["sections"]}
        cls.store._build_db()

    def test_available_guitars_under_budget(self):
        result = self.store.search_products("violao", 1000, in_stock_only=True)
        self.assertGreater(result["total_matches"], 0)
        self.assertEqual(result["returned_count"], len(result["results"]))
        self.assertGreaterEqual(result["total_matches"], result["returned_count"])
        self.assertTrue(all(r["category"] == "Violões" and r["stock_quantity"] > 0
                            for r in result["results"]))

    def test_active_promotion_uses_current_price(self):
        result = self.store.search_products("Violão Teste")
        self.assertEqual(result["results"][0]["price_brl"], "R$ 800,00")
        self.assertEqual(result["results"][0]["discount_percent"], 20.0)
        self.assertEqual(result["results"][0]["original_price_brl"], "R$ 1.000,00")
        self.assertEqual(result["results"][0]["pix_price_brl"], "R$ 800,00")
        self.assertFalse(result["results"][0]["pix_discount_stacks"])

    def test_sale_filter_runs_before_pagination(self):
        result = self.store.search_products("", limit=1, on_sale_only=True)
        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(result["returned_count"], 1)
        self.assertEqual(result["results"][0]["name"], "Violão Teste")

    def test_pix_uses_decimal_cent_rounding(self):
        result = self.store.search_products("Violão Pix")["results"][0]
        self.assertEqual(result["pix_price_brl"], "R$ 550,91")

    def test_order_requires_matching_email(self):
        self.assertEqual(self.store.get_order("9", "demo@example.com")["status"], "confirmed")
        self.assertIn("error", self.store.get_order("9", "wrong@example.com"))
        self.assertEqual(self.store.get_order("9", "")["missing"], ["email"])

    def test_installment_calculation_uses_structured_policy(self):
        denied = self.store.check_installment(800, 10)
        self.assertFalse(denied["allowed"])
        self.assertEqual(denied["installment_brl"], "R$ 80,00")
        self.assertEqual(denied["minimum_installment_brl"], "R$ 100,00")
        self.assertTrue(self.store.check_installment(800, 8)["allowed"])
        self.assertIsNone(self.store.check_installment(40, 2)["allowed"])
        self.assertIn("error", self.store.check_installment(float("nan"), 10))

    def test_policy_returns_relevant_section_with_source(self):
        result = self.store.get_policy("arrependimento compra online")
        self.assertEqual(result["matches"][0]["section"], "4.1")
        self.assertEqual(result["matches"][0]["page"], 4)
        self.assertIn("7 (sete) dias", result["matches"][0]["text"])

    def test_policy_ranking_ignores_word_fragments_and_generic_product(self):
        store = Store.__new__(Store)
        store.policy_sections = [
            {"page": 3, "section": "3.1", "title": "Regras de parcelamento",
             "text": "Parcelamento em 10x: parcela mínima de R$ 100,00."},
            {"page": 6, "section": "7", "title": "Atendimento",
             "text": "Atendimento de produto na loja."},
        ]
        self.assertEqual(store.get_policy("Posso parcelar 10x um produto?")["matches"][0]["section"], "3.1")
        self.assertEqual(store.get_policy("até")["matches"], [])

    def test_policy_routes_customer_phrasings_to_evidence(self):
        store = Store.__new__(Store)
        store.policy_sections = [
            {"page": 2, "section": "1.2", "title": "Dados da empresa",
             "text": "Endereço: Rua Central, Campo Grande."},
            {"page": 2, "section": "2", "title": "Horário de funcionamento",
             "text": "Segunda a sábado, horário de funcionamento."},
            {"page": 4, "section": "5.1", "title": "Frete em Campo Grande",
             "text": "Frete local para Campo Grande."},
            {"page": 5, "section": "5.2", "title": "Entregas para outras cidades",
             "text": "Envios para cidades fora da região metropolitana."},
            {"page": 8, "section": "9", "title": "Privacidade",
             "text": "Exclusão de dados pessoais mediante solicitação."},
        ]
        examples = {
            "Onde fica a loja?": "1.2",
            "Quando vocês abrem?": "2",
            "Como apago meus dados pessoais?": "9",
            "Quanto sai o frete para fora de Campo Grande?": "5.2",
        }
        for question, section in examples.items():
            with self.subTest(question=question):
                self.assertEqual(store.get_policy(question)["matches"][0]["section"], section)

    def test_conflicting_manual_contacts_are_not_sent_to_model(self):
        text = "WhatsApp (67) 3341 - 4444 e contato@empóriodamusica.com.br"
        safe = customer_safe_policy_text(text)
        self.assertNotIn("3341", safe)
        self.assertNotIn("@", safe)


if __name__ == "__main__":
    unittest.main()
