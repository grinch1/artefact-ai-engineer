import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api


class FakeStore:
    def get_policy(self, topic):
        return {"matches": [{"page": 4, "text": "7 dias corridos"}]}

    def get_order(self, order_id, email):
        return {"error": "Order not found or identity not verified."}


class ApiTests(unittest.TestCase):
    def setUp(self):
        api.sessions.clear()
        self.store_patch = patch.object(api, "get_store", return_value=FakeStore())
        self.mode_patch = patch.dict(os.environ, {"AGENT_MODE": "offline"})
        self.store_patch.start()
        self.mode_patch.start()
        self.client = TestClient(api.app)

    def tearDown(self):
        self.store_patch.stop()
        self.mode_patch.stop()
        api.sessions.clear()

    def test_page_and_health(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_order_without_email_stays_private(self):
        result = self.client.post("/chat", json={"session_id": "demo", "message": "Meu pedido 9 já foi enviado?"})
        self.assertEqual(result.status_code, 200)
        self.assertIn("e-mail", result.json()["answer"])
        self.assertNotIn("confirmado", result.json()["answer"])

    def test_rejects_invalid_session_identifier(self):
        result = self.client.post("/chat", json={"session_id": "../other", "message": "Oi"})
        self.assertEqual(result.status_code, 422)


if __name__ == "__main__":
    unittest.main()
