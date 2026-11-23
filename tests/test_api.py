import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api


class FakeStore:
    pass


class FakeAgent:
    def ask(self, message):
        return f"model received: {message}"


class ApiTests(unittest.TestCase):
    def setUp(self):
        api.sessions.clear()
        self.store_patch = patch.object(api, "get_store", return_value=FakeStore())
        self.agent_patch = patch.object(api, "OllamaAgent", return_value=FakeAgent())
        self.mode_patch = patch.dict(os.environ, {"AGENT_MODE": "ollama"})
        self.store_patch.start()
        self.agent_patch.start()
        self.mode_patch.start()
        self.client = TestClient(api.app)

    def tearDown(self):
        self.store_patch.stop()
        self.agent_patch.stop()
        self.mode_patch.stop()
        api.sessions.clear()

    def test_page_and_health(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/style.css").status_code, 200)
        self.assertEqual(self.client.get("/app.js").status_code, 200)
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/mode").json()["mode"], "ollama")
        self.assertTrue(self.client.get("/mode").json()["model"])

    def test_chat_delegates_to_model(self):
        result = self.client.post("/chat", json={"session_id": "demo", "message": "Qual é a garantia?"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["answer"], "model received: Qual é a garantia?")

    def test_rejects_invalid_session_identifier(self):
        result = self.client.post("/chat", json={"session_id": "../other", "message": "Oi"})
        self.assertEqual(result.status_code, 422)

    def test_offline_response_mode_is_removed(self):
        with patch.dict(os.environ, {"AGENT_MODE": "offline"}):
            result = self.client.post("/chat", json={"session_id": "oldmode", "message": "Oi"})
        self.assertEqual(result.status_code, 503)


if __name__ == "__main__":
    unittest.main()
