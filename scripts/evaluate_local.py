"""Run the five case scenarios against a private local GPU endpoint."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import OllamaAgent
from store import Store


CASES = [
    ("catalog", "Quais violões vocês têm em estoque por até R$ 1.000?", ["search_products"], ["R$", "viol"]),
    ("order_privacy", "Meu pedido 9 já foi enviado?", [], ["e-mail"]),
    ("return", "Comprei online e me arrependi. Posso devolver?", ["get_policy"], ["7", "dias"]),
    ("promotion_pix", "O ukulele Ohana CK-20 está com desconto? Se eu pagar no PIX, ganho mais 5%?", ["search_products", "get_policy"], ["439,20", "não acumula"]),
    ("accessory", "Vocês vendem cordas para violão?", ["get_policy"], ["cordas", "não"]),
    ("hours", "Qual é o horário de funcionamento da loja?", ["get_policy"], ["9h às 18h", "sábado"]),
    ("local_shipping", "Quanto custa o frete para Campo Grande em um pedido de R$ 400?", ["get_policy"], ["35,00", "1 a 3 dias"]),
    ("warranty", "Qual é a garantia dos instrumentos?", ["get_policy"], ["90 dias", "fabricante"]),
    ("installments", "Posso parcelar em 10x sem juros um produto de R$ 800?", ["get_policy"], ["não atende", "R$ 100,00"]),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435/v1")
    parser.add_argument("--model", default="qwen2.5-mainframe:7b")
    args = parser.parse_args()
    store = Store(args.data_dir)
    failed = False
    for name, question, required_tools, required_text in CASES:
        agent = OllamaAgent(store, args.model, args.base_url)
        try:
            answer = agent.ask(question)
            lowered = answer.casefold()
            checks = {"tools": all(t in agent.last_tools for t in required_tools),
                      "text": all(t.casefold() in lowered for t in required_text)}
            if name == "order_privacy":
                checks["privacy"] = "confirmado" not in lowered and "rastreamento" not in lowered
            if name == "promotion_pix":
                checks["no_extra_discount"] = "mais 5%" not in lowered and "não acumula" in lowered
            ok = all(checks.values())
            failed |= not ok
            print(json.dumps({"case": name, "passed": ok, "checks": checks,
                              "path": agent.last_path, "tools": agent.last_tools,
                              "answer": answer}, ensure_ascii=False), flush=True)
        except Exception as exc:
            failed = True
            print(json.dumps({"case": name, "passed": False, "error": type(exc).__name__}), flush=True)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
