"""Exact catalog, price, promotion, and stock lookup."""

import re
import unicodedata

DEFINITION = {
    "type": "function", "name": "search_products",
    "description": "Search instruments in the current CSV snapshot by name, category, price and stock. Returns exact stored prices and active promotions; accessories are outside this catalog.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_price": {"type": ["number", "null"]},
            "limit": {"type": "integer"},
            "in_stock_only": {"type": "boolean"},
        },
        "required": ["query", "max_price", "limit", "in_stock_only"],
        "additionalProperties": False,
    },
    "strict": True,
}


def requested_category(message: str) -> str | None:
    normalized = unicodedata.normalize("NFKD", message.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    for pattern, category in (
        (r"\bviol(?:ao|oes)\b", "violão"),
        (r"\bguitarras?\b", "guitarra"),
        (r"\bbaixos?\b", "baixo"),
        (r"\bbaterias?\b", "bateria"),
        (r"\bteclados?\b", "teclado"),
        (r"\bukuleles?\b", "ukulele"),
    ):
        if re.search(pattern, normalized):
            return category
    return None


def execute(store, arguments: dict, customer_message: str = "") -> dict:
    arguments = dict(arguments)
    category = requested_category(customer_message)
    if category and not arguments.get("query", "").strip():
        arguments["query"] = category
    result = store.search_products(**arguments)
    result["applied_query"] = arguments.get("query", "")
    return result
