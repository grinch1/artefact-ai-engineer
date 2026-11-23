import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import Agent, OllamaAgent


class FakeStore:
    def __init__(self):
        self.topics = []

    def get_policy(self, topic):
        self.topics.append(topic)
        return {"matches": [{"section": "4.1", "page": 4,
                             "text": "Fonte de teste: devolução em sete dias."}]}


class AgentTests(unittest.TestCase):
    def test_ollama_consults_policy_then_returns_model_text(self):
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Resposta do modelo", tool_calls=[]))]
        )
        store = FakeStore()
        with patch("openai.OpenAI", return_value=client):
            agent = OllamaAgent(store, "test-model", "http://localhost:11435/v1")
        self.assertEqual(agent.ask("Posso devolver?"), "Resposta do modelo")
        self.assertEqual(store.topics, ["Posso devolver?"])
        messages = client.chat.completions.create.call_args.kwargs["messages"]
        self.assertIn("Fonte de teste", messages[1]["content"])
        self.assertEqual(agent.last_policy_sections, ["4.1 (p. 4)"])

    def test_local_reasoning_is_model_specific(self):
        with patch("openai.OpenAI"):
            self.assertEqual(OllamaAgent(FakeStore(), "gpt-oss:20b", "http://localhost/v1").think,
                             "medium")
            self.assertFalse(OllamaAgent(FakeStore(), "qwen3:14b", "http://localhost/v1").think)

    def test_hosted_agent_consults_policy_then_returns_model_text(self):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(output=[], output_text="Resposta hospedada")
        store = FakeStore()
        with patch("openai.OpenAI", return_value=client):
            agent = Agent(store, "test-model")
        self.assertEqual(agent.ask("Posso devolver?"), "Resposta hospedada")
        self.assertEqual(store.topics, ["Posso devolver?"])
        instructions = client.responses.create.call_args.kwargs["instructions"]
        self.assertIn("Fonte de teste", instructions)


if __name__ == "__main__":
    unittest.main()
