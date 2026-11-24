"""Small allowlist of read-only tools exposed to either model provider."""

import json

from . import catalog, orders, policy


DEFINITIONS = [catalog.DEFINITION, orders.DEFINITION,
               policy.GET_POLICY, policy.CHECK_INSTALLMENT]
HANDLERS = {
    "search_products": catalog.execute,
    "get_order": orders.execute,
    "get_policy": policy.get_policy,
    "check_installment": policy.check_installment,
}


def run_tool(store, name: str, arguments: str, customer_message: str = "",
             customer_messages: list[str] | None = None) -> str:
    try:
        payload = json.loads(arguments)
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object")
        handler = HANDLERS.get(name)
        if name == "search_products":
            result = catalog.execute(store, payload, customer_message)
        elif name == "get_order":
            result = orders.execute(store, payload, customer_messages or [customer_message])
        else:
            result = handler(store, payload) if handler else {"error": "Unknown tool"}
        return json.dumps(result, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        return json.dumps({"error": f"Invalid arguments: {exc}"})
