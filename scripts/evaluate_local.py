"""Measure nine real model answers against case-specific expectations."""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import OllamaAgent
from store import Store


CASES = [
    ("catalog", "Quais violões vocês têm em estoque por até R$ 1.000?", ["search_products"], ["R$", "viol"]),
    ("order_privacy", "Meu pedido 9 já foi enviado?", [], ["mail"]),
    ("return", "Comprei online e me arrependi. Posso devolver?", ["get_policy"], ["7", "dias"]),
    ("promotion_pix", "O ukulele Ohana CK-20 está com desconto? Se eu pagar no PIX, ganho mais 5%?", ["search_products", "get_policy"], ["439,20", "549,00", "20%"]),
    ("accessory", "Vocês vendem cordas para violão?", ["get_policy"], ["cordas", "não"]),
    ("hours", "Qual é o horário de funcionamento da loja?", ["get_policy"], ["sábado"]),
    ("local_shipping", "Quanto custa o frete para Campo Grande em um pedido de R$ 400?", ["get_policy"], ["35,00"]),
    ("warranty", "Qual é a garantia dos instrumentos?", ["get_policy"], ["fabricante"]),
    ("installments", "Posso parcelar em 10x sem juros um produto de R$ 800?", ["get_policy"], ["R$ 100"]),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435/v1")
    parser.add_argument("--model", default="gpt-oss:20b")
    parser.add_argument("--think", choices=("false", "low", "medium", "high"),
                        help="Ollama reasoning level for this comparison")
    parser.add_argument("--case", choices=[case[0] for case in CASES],
                        help="Run one scenario instead of the full suite")
    args = parser.parse_args()
    store = Store(args.data_dir)
    failed = False
    for name, question, required_tools, required_text in CASES:
        if args.case and name != args.case:
            continue
        agent = OllamaAgent(store, args.model, args.base_url,
                            False if args.think == "false" else args.think)
        started = time.perf_counter()
        try:
            answer = agent.ask(question)
            lowered = re.sub(r"\s+", " ", answer.casefold())
            lowered = re.sub(r"(\d)\s+%", r"\1%", lowered)
            lowered = re.sub(r"r\$\s*", "r$ ", lowered)
            consulted = bool(agent.last_policy_sections)
            observed_tools = set(agent.last_tools) | ({"get_policy"} if consulted else set())
            checks = {"tools": all(t in observed_tools for t in required_tools),
                      "text": all(t.casefold() in lowered for t in required_text)}
            checks["policy_before_answer"] = consulted
            checks["no_markdown_table"] = "|---" not in answer and "|----" not in answer
            if name == "catalog":
                checks["stock_filter"] = any(
                    call["name"] == "search_products" and
                    json.loads(call["arguments"]).get("in_stock_only") is True
                    for call in agent.last_tool_calls
                )
                checks["price_labels"] = "preços já consideram o desconto" not in lowered
            if name == "order_privacy":
                checks["privacy"] = "confirmado" not in lowered and "rastreamento" not in lowered
            if name == "promotion_pix":
                checks["no_extra_discount"] = any(phrase in lowered for phrase in
                    ("não acumula", "não se acumula", "não se aplica", "não é aplicado",
                     "não é aplicável", "não é cumulativo", "não são cumulativos",
                     "não são cumulativas",
                     "não há desconto adicional"))
            if name == "accessory":
                checks["no_partner_offer"] = not any(phrase in lowered for phrase in
                    ("posso indicar lojas", "posso indicar parceiros",
                     "posso recomendar parceiros", "parceiros locais",
                     "posso ajudar a encontrar", "posso procurar lojas"))
            if name == "hours":
                checks["hours"] = bool(re.search(r"18(?::00|h00|h\b)", lowered) and
                                       re.search(r"13(?::00|h00|h\b)", lowered))
            if name == "warranty":
                checks["legal_90_days"] = bool(re.search(r"90\s*(?:\([^)]*\)\s*)?dias", lowered))
            if name == "installments":
                installment_text = re.sub(r"\b7\s*x\s*(?:a|até)\s*12\s*x\b", "faixa de 7 a 12 parcelas", lowered)
                installment_text = re.sub(r"\b7\s*[-‐‑‒–—]\s*12\s*x\b", "faixa de 7 a 12 parcelas", installment_text)
                installment_text = re.sub(r"\b7\s+(?:a|até|e)\s+12\s+vezes\b", "faixa de 7 a 12 parcelas", installment_text)
                checks["rejects_10x"] = any(phrase in lowered for phrase in
                    ("não é possível", "não pode", "não atende", "não seria possível",
                     "10x não", "não está disponível", "não é permitida", "não é permitido"))
                checks["rejects_10x"] |= "não é compatível" in lowered
                checks["no_bad_alternative"] = not re.search(
                    r"6x.{0,25}parcela(?:s)?(?: de)?\s*r\$\s*80(?:[,.]00)?", lowered, re.S
                )
                checks["no_alternative_installments"] = not re.search(
                    r"\b(?!10\s*x\b)(?:[1-9]|1[0-2])\s*x\b|\b(?:parcelar\s+em|em)\s+"
                    r"(?!10\s+vezes\b)(?:[1-9]|1[0-2])\s+vezes\b", installment_text
                )
            ok = all(checks.values())
            failed |= not ok
            print(json.dumps({"case": name, "passed": ok, "checks": checks,
                              "policy_sections": agent.last_policy_sections,
                              "model_tools": agent.last_tools,
                              "model_tool_calls": agent.last_tool_calls,
                              "elapsed_s": round(time.perf_counter() - started, 2),
                              "answer": answer},
                             ensure_ascii=False), flush=True)
        except Exception as exc:
            failed = True
            print(json.dumps({"case": name, "passed": False, "elapsed_s": round(time.perf_counter() - started, 2),
                              "error": type(exc).__name__}), flush=True)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
