import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from store import Store
from policy_guard import guarded_answer
from agent import OllamaAgent


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
        cls.store.policy_pages = [
            "",
            "Trabalhamos com instrumentos. Não comercializamos acessórios como cordas. "
            "Segunda a Sexta-feira 09:00 às 18:00. Sábado 09:00 às 13:00. Domingo e Feriados Fechado.",
            "Parcelamento de 7x a 12x sem juros, parcela mínima de R$ 100,00. "
            "Parcelamento de 4x a 6x sem juros, parcela mínima de R$ 80,00.",
            "4.1 Direito de Arrependimento: até 7 (sete) dias corridos após o recebimento. "
            "Produto na embalagem original. O frete de devolução é por conta da loja. "
            "Frete grátis para pedidos acima de R$ 500,00. Para pedidos abaixo, "
            "taxa fixa de R$ 35,00. Prazo de entrega: 1 a 3 dias úteis.",
            "",
            "Promoções não são cumulativas. O desconto PIX não se aplica sobre preços já promocionais.",
            "Garantia legal de 90 (noventa) dias. Garantia do fabricante de 6 meses a 2 anos.",
        ]
        cls.store._build_db()

    def test_available_guitars_under_budget(self):
        result = self.store.search_products("violao", 1000, in_stock_only=True)
        self.assertGreater(result["total_matches"], 0)
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

    def test_policy_finds_return_rule(self):
        result = self.store.get_policy("arrependimento compra online")
        self.assertTrue(any("7 (sete) dias" in match["text"] for match in result["matches"]))

    def test_order_status_requires_both_identifiers(self):
        answer, tools = guarded_answer(self.store, "Meu pedido 9 já foi enviado?")
        self.assertIn("e-mail usado na compra", answer)
        self.assertEqual(tools, [])
        answer, tools = guarded_answer(self.store, "Meu pedido 9 já foi enviado? demo@example.com")
        self.assertIn("confirmed", answer)
        self.assertEqual(tools, ["get_order"])

    def test_order_followup_uses_prior_number_without_model(self):
        agent = OllamaAgent(self.store, "unused", "http://127.0.0.1:11435/v1")
        self.assertIn("e-mail usado na compra", agent.ask("Meu pedido 9 já foi enviado?"))
        self.assertIn("confirmed", agent.ask("demo@example.com"))
        self.assertEqual(agent.last_path, "policy_guard")
        self.assertEqual(agent.last_tools, ["get_order"])
        self.assertNotIn("demo@example.com", str(agent.history))

    def test_return_uses_verified_policy(self):
        answer, tools = guarded_answer(self.store, "Comprei online e me arrependi. Posso devolver?")
        self.assertIn("7 dias corridos", answer)
        self.assertEqual(tools, ["get_policy"])

    def test_accessory_is_not_sold(self):
        answer, tools = guarded_answer(self.store, "Vocês vendem cordas para violão?")
        self.assertIn("Não vendemos acessórios", answer)
        self.assertEqual(tools, ["get_policy"])

    def test_promotional_pix_price_does_not_stack(self):
        answer, tools = guarded_answer(self.store, "Violão Teste está com desconto? No PIX tem mais 5%?")
        self.assertIn("não acumula", answer)
        self.assertIn("R$ 800,00", answer)
        self.assertEqual(tools, ["get_policy", "search_products"])

    def test_changed_policy_fails_closed(self):
        original = self.store.policy_pages[5]
        try:
            self.store.policy_pages[5] = "Nova regra ainda não revisada."
            answer, _ = guarded_answer(self.store, "No PIX o desconto acumula?")
            self.assertIn("confirmar", answer)
        finally:
            self.store.policy_pages[5] = original

    def test_shipping_and_ambiguous_threshold(self):
        answer, tools = guarded_answer(self.store, "Frete para Campo Grande em pedido de R$ 400?")
        self.assertIn("R$ 35,00", answer)
        self.assertEqual(tools, ["get_policy"])
        answer, _ = guarded_answer(self.store, "Frete para Campo Grande em pedido de R$ 500?")
        self.assertIn("confirmar", answer)

    def test_warranty_and_installment_minimum(self):
        answer, tools = guarded_answer(self.store, "Qual é a garantia dos instrumentos?")
        self.assertIn("90 dias", answer)
        self.assertEqual(tools, ["get_policy"])
        answer, tools = guarded_answer(self.store, "Posso parcelar R$ 800 em 10x?")
        self.assertIn("não atende", answer)
        self.assertEqual(tools, ["get_policy"])


if __name__ == "__main__":
    unittest.main()
