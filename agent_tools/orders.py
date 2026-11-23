"""Read-only order lookup with customer-provided identifiers."""

DEFINITION = {
    "type": "function", "name": "get_order",
    "description": "Retrieve one order status only after the customer supplied both order number and purchase email. Never guess either identifier.",
    "parameters": {
        "type": "object",
        "properties": {"order_id": {"type": "string"}, "email": {"type": "string"}},
        "required": ["order_id", "email"],
        "additionalProperties": False,
    },
    "strict": True,
}


def execute(store, arguments: dict) -> dict:
    return store.get_order(**arguments)
