import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_tools import DEFINITIONS, HANDLERS, run_tool


class FakeStore:
    def search_products(self, **kwargs):
        return {"catalog_query": kwargs["query"], "sale_only": kwargs.get("on_sale_only", False),
                "limit": kwargs["limit"], "max_price": kwargs.get("max_price"),
                "in_stock_only": kwargs.get("in_stock_only")}

    def get_order(self, **kwargs):
        return {"order_id": kwargs["order_id"]}

    def get_policy(self, **kwargs):
        return {"topic": kwargs["topic"]}

    def check_installment(self, **kwargs):
        return {"installments": kwargs["installments"]}


class ToolTests(unittest.TestCase):
    def test_small_strict_tool_allowlist(self):
        names = [item["name"] for item in DEFINITIONS]
        self.assertEqual(names, ["search_products", "get_order", "get_policy", "check_installment"])
        self.assertEqual(set(names), set(HANDLERS))
        for item in DEFINITIONS:
            with self.subTest(tool=item["name"]):
                self.assertTrue(item["strict"])
                self.assertFalse(item["parameters"]["additionalProperties"])
                self.assertEqual(set(item["parameters"]["properties"]),
                                 set(item["parameters"]["required"]))

    def test_dispatch_is_read_only_and_allowlisted(self):
        store = FakeStore()
        self.assertEqual(json.loads(run_tool(store, "get_policy", '{"topic":"frete"}')),
                         {"topic": "frete"})
        self.assertEqual(json.loads(run_tool(store, "check_installment",
                                             '{"price_brl":800,"installments":10}')),
                         {"installments": 10})
        self.assertIn("error", json.loads(run_tool(store, "delete_order", '{}')))

    def test_explicit_customer_category_survives_blank_model_query(self):
        result = json.loads(run_tool(FakeStore(), "search_products",
            '{"query":"","max_price":1000,"limit":10,"in_stock_only":true}',
            "Quais violões vocês têm por até R$ 1.000?"))
        self.assertEqual(result["catalog_query"], "violão")
        self.assertEqual(result["applied_query"], "violão")

    def test_all_discounted_products_forces_sale_filter_before_page(self):
        result = json.loads(run_tool(FakeStore(), "search_products",
            '{"query":"desconto","max_price":500,"limit":1,"in_stock_only":true,"on_sale_only":false}',
            "Quais todos os produtos com desconto?"))
        self.assertEqual(result["catalog_query"], "")
        self.assertTrue(result["sale_only"])
        self.assertEqual(result["limit"], 12)
        self.assertIsNone(result["max_price"])
        self.assertFalse(result["in_stock_only"])

    def test_order_tool_requires_customer_supplied_identifiers(self):
        args = '{"order_id":"1","email":"buyer@example.com"}'
        no_email = json.loads(run_tool(FakeStore(), "get_order", args,
                                        "Consulte o pedido 1 sem e-mail."))
        self.assertEqual(no_email["missing"], ["email"])
        substituted_email = json.loads(run_tool(FakeStore(), "get_order", args,
            "Meu pedido é 1; o e-mail é other@example.com."))
        self.assertEqual(substituted_email["missing"], ["email"])
        two_turns = json.loads(run_tool(FakeStore(), "get_order", args,
            "O e-mail é buyer@example.com.",
            ["Meu pedido é 1.", "O e-mail é buyer@example.com."]))
        self.assertEqual(two_turns["order_id"], "1")
        malformed = json.loads(run_tool(FakeStore(), "get_order",
            '{"order_id":1,"email":"buyer@example.com"}',
            "Meu pedido é 1, e-mail buyer@example.com."))
        self.assertIn("error", malformed)


if __name__ == "__main__":
    unittest.main()
