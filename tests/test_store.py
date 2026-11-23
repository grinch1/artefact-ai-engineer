import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store


class StoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store.__new__(Store)
        cls.store.tables = {
            "products": [
                {"product_id": "1", "name": "Violão Teste", "description": "Aço", "category_id": "1", "price_brl": "1000", "stock_quantity": "2", "status": "active"},
                {"product_id": "2", "name": "Ukulele Teste", "description": "Parece violão", "category_id": "2", "price_brl": "200", "stock_quantity": "3", "status": "active"},
                {"product_id": "3", "name": "Violão Sem Estoque", "description": "", "category_id": "1", "price_brl": "500", "stock_quantity": "0", "status": "active"},
            ],
            "orders": [{"order_id": "9", "customer_id": "7", "status": "confirmed", "order_date": "2025-11-01", "estimated_delivery": "", "tracking_code": ""}],
            "customers": [{"customer_id": "7", "email": "demo@example.com"}],
        }
        cls.store.categories = {"1": "Violões", "2": "Ukuleles"}
        cls.store.promotions = {"1": [{"discount_percent": "20"}]}
        cls.store.policy_pages = ["", "", "", "4.1 Direito de Arrependimento: até 7 (sete) dias após o recebimento."]
        cls.store.policy_sections = cls.store._build_policy_sections()
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

    def test_order_requires_matching_email(self):
        self.assertEqual(self.store.get_order("9", "demo@example.com")["status"], "confirmed")
        self.assertIn("error", self.store.get_order("9", "wrong@example.com"))

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


if __name__ == "__main__":
    unittest.main()
