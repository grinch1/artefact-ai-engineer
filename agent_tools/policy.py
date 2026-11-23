"""Versioned policy retrieval and exact payment-rule calculation."""

GET_POLICY = {
    "type": "function", "name": "get_policy",
    "description": "Find relevant customer-facing policy rules from versioned policy.json with source section, page and typed facts.",
    "parameters": {
        "type": "object",
        "properties": {"topic": {"type": "string"}},
        "required": ["topic"],
        "additionalProperties": False,
    },
    "strict": True,
}

CHECK_INSTALLMENT = {
    "type": "function", "name": "check_installment",
    "description": "Evaluate one requested installment count and price against the structured policy, returning the verified amount and minimum.",
    "parameters": {
        "type": "object",
        "properties": {"price_brl": {"type": "number"},
                       "installments": {"type": "integer"}},
        "required": ["price_brl", "installments"],
        "additionalProperties": False,
    },
    "strict": True,
}


def get_policy(store, arguments: dict) -> dict:
    return store.get_policy(**arguments)


def check_installment(store, arguments: dict) -> dict:
    return store.check_installment(**arguments)
