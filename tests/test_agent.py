import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import Agent, OllamaAgent, answer_issue, default_application_rules, default_policy_facts


class FakeStore:
    def __init__(self):
        self.topics = []

    def get_policy(self, topic):
        self.topics.append(topic)
        return {"matches": [{"section": "4.1", "page": 4,
                             "text": "Fonte de teste: devolução em sete dias."}]}


class AgentTests(unittest.TestCase):
    def test_answer_guard_rejects_unsupported_contact_and_shipping_quote(self):
        self.assertIsNotNone(answer_issue("Como apago meus dados?", "Ligue para (67) 3341-4444."))
        self.assertIsNotNone(answer_issue("Qual o frete?", "Posso ajudar a estimar o valor com seu CEP."))
        self.assertIsNotNone(answer_issue("Posso devolver?", "Posso ajudar a iniciar a devolução."))
        self.assertIsNotNone(answer_issue("Quais violões?", "| Nome | Preço |\n|------|-------|"))
        self.assertIsNotNone(answer_issue("Qual o preço?", "**R$ 100,00**"))
        self.assertIsNotNone(answer_issue("meu@email.com", "Posso acompanhar a evolução do envio.",
                                          ["get_order"]))
        self.assertIsNotNone(answer_issue("Posso devolver?", "Posso encaminhar à equipe."))
        self.assertIsNotNone(answer_issue("Comprei online. Posso devolver?",
                                          "Para iniciar, precisamos do número do pedido e do e-mail da compra."))
        self.assertIsNotNone(answer_issue("Comprei online. Posso devolver?",
                                          "Se quiser iniciar a devolução, basta falar!"))
        self.assertIsNotNone(answer_issue("Qual o frete para outra cidade?",
                                          "Se quiser que encaminhemos sua solicitação à equipe, avise."))
        self.assertIsNotNone(answer_issue("Qual a garantia?", "Posso consultar o catálogo para confirmar."))
        self.assertIsNotNone(answer_issue("Posso parcelar em 10x?", "Posso verificar outras opções."))
        self.assertIsNotNone(answer_issue("Posso parcelar em 5x?", "Você pode pagar à vista ou usar outro método de pagamento."))
        self.assertIsNotNone(answer_issue("Posso parcelar em 13x?", "Há métodos combinados acima de R$ 2.000."))
        self.assertIsNotNone(answer_issue("Como apago meus dados pessoais?",
                                          "Pode me informar seu e-mail antes de encaminhar?"))
        self.assertIsNotNone(answer_issue("Meu pedido 9 já foi enviado?",
                                          "Preciso que você informe o número completo do pedido."))
        self.assertIsNotNone(answer_issue("Posso devolver?",
                                          "Se precisar de ajuda para iniciar a devolução, me avise!"))
        self.assertIsNotNone(answer_issue("Quanto sai o frete?",
                                          "Para estimar, basta informar o CEP e as dimensões."))
        self.assertIsNotNone(answer_issue("Como apago meus dados?",
                                          "Visite nosso site para os canais oficiais."))
        self.assertIsNotNone(answer_issue("Qual é a garantia?",
                                          "Posso ajudar a verificar detalhes do certificado."))
        self.assertIsNotNone(answer_issue("Quais violões têm em estoque?",
                                          "Violão A: R$ 800 (PIX: R$ 760).", ["search_products"]))
        self.assertIsNotNone(answer_issue("O frete para Campo Grande é grátis?",
                                          "Sim, na Campo Grande metropolitan area."))
        self.assertIsNotNone(answer_issue("Como apago meus dados pessoais?",
                                          "Posso indicar onde encontrar os canais de atendimento."))
        self.assertIsNotNone(answer_issue("Qual é a garantia?",
                                          "Para detalhes, basta me dizer qual instrumento é."))
        self.assertIsNotNone(answer_issue("Qual é a garantia?",
                                          "Para detalhes, basta me informar o nome ou modelo."))
        self.assertIsNotNone(answer_issue("Qual é a garantia?",
                                          "O prazo do fabricante está no certificado."))
        self.assertIsNone(answer_issue("Qual o frete?", "O valor depende do CEP, peso e dimensões."))
        self.assertIsNotNone(answer_issue("Comprei presencialmente e me arrependi.",
                                          "A devolução online tem prazo de 7 dias úteis."))
        self.assertIsNotNone(answer_issue("Meu violão deu defeito.",
                                          "A troca pode ser feita em 30 dias úteis."))
        self.assertIsNotNone(answer_issue("Meu violão deu defeito.",
                                          "A troca vale por 30 dias a partir do recebimento."))
        self.assertIsNotNone(answer_issue("O violão deu defeito 45 dias após a compra. Posso trocar?",
                                          "A troca não é possível; procure o fabricante."))
        self.assertIsNone(answer_issue("O violão deu defeito 45 dias após a compra. Posso trocar?",
                                       "A equipe humana precisa confirmar a relação entre troca e garantia legal de 90 dias."))
        self.assertIsNotNone(answer_issue("O violão deu defeito 45 dias após a compra. Posso trocar?",
                                          "A equipe humana precisa confirmar a troca após 30 dias."))
        self.assertIsNotNone(answer_issue("O violão deu defeito 45 dias após a compra. Posso trocar?",
                                          "O prazo de 31 a 90 dias requer confirmação; depois disso deve ser encaminhado ao fabricante."))
        self.assertIsNotNone(answer_issue("Posso parcelar R$ 40,00 em 2x?",
                                          "Sim! Mas a equipe precisa confirmar."))
        self.assertIsNotNone(answer_issue("Posso parcelar R$ 40,00 em 2x?",
                                          "Informe seu e-mail e número do pedido para confirmar."))
        self.assertIsNotNone(answer_issue("Posso parcelar R$ 40,00 em 2x?",
                                          "Compras abaixo de R$ 50 podem ser parceladas em até 12 vezes, com confirmação."))
        self.assertIsNotNone(answer_issue("Meu violão deu defeito após 45 dias.",
                                          "A garantia legal do fabricante é de 90 dias."))
        self.assertIsNotNone(answer_issue("Posso parcelar em 8x?",
                                          "De seis a doze parcelas, o mínimo é R$ 100."))
        self.assertIsNotNone(answer_issue("Posso pagar R$ 400 em 5x?",
                                          "Compras de até R$ 400 podem ser divididas em 5 vezes."))
        self.assertIsNone(answer_issue("Comprei online e me arrependi.",
                                       "A devolução pode ser feita em sete dias corridos."))
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

    def test_numeric_guard_uses_versioned_company_facts(self):
        facts = default_policy_facts()
        changed = {**facts, "4.1": {**facts["4.1"], "return_window_calendar_days": 8}}
        self.assertIsNotNone(answer_issue("Posso devolver?", "O prazo é de 8 dias úteis.", policy_facts=changed))
        self.assertIsNone(answer_issue("Posso devolver?", "O prazo é de 7 dias úteis.", policy_facts=changed))

    def test_capability_guard_uses_versioned_application_rules(self):
        rules = default_application_rules()
        enabled = [dict(item, available=True) if item["id"] == "external_shipping_quote" else item
                   for item in rules]
        answer = "Posso calcular o frete com seu CEP."
        self.assertIsNotNone(answer_issue("Quanto custa o frete?", answer, application_rules=rules))
        self.assertIsNone(answer_issue("Quanto custa o frete?", answer, application_rules=enabled))

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
