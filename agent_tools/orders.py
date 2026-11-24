"""Read-only order lookup with customer-provided identifiers."""

import re

DEFINITION = {
    "type": "function", "name": "get_order",
    "description": "Retrieve one order status only after the customer supplied both order number and purchase email. Never guess either identifier. estimated_delivery is a forecast, not the actual delivery date.",
    "parameters": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}, "email": {"type": "string"}},
        "required": ["order_id", "email"],
        "additionalProperties": False,
    },
    "strict": True,
}


def execute(store, arguments: dict, customer_messages: list[str]) -> dict:
    if not isinstance(arguments.get("order_id"), str) or not isinstance(arguments.get("email"), str):
        return {"error": "Order number and email must be strings."}
    order_id = str(arguments.get("order_id", ""))
    email = str(arguments.get("email", "")).strip().casefold()
    supplied_order = bool(order_id) and any(
        re.search(rf"\b(?:pedido|ordem|order|n[uú]mero)\b\D{{0,28}}\b{re.escape(order_id)}\b",
                  text, re.IGNORECASE)
        or re.match(rf"^\s*#?{re.escape(order_id)}\b", text)
        for text in customer_messages)
    supplied_email = bool(email) and any(
        email in {found.casefold() for found in
                  re.findall(r"[\w.+-]+@[\w.-]+\.[\w-]+", text)}
        for text in customer_messages)
    if not supplied_order or not supplied_email:
        missing = ([] if supplied_order else ["order_id"]) + ([] if supplied_email else ["email"])
        return {"error": "Order lookup requires both identifiers supplied by the customer.",
                "missing": missing}
    return store.get_order(**arguments)
