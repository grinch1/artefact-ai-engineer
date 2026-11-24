"""Exact catalog, price, promotion, and stock lookup."""

import re
import unicodedata

DEFINITION = {
    "type": "function", "name": "search_products",
    "description": "Search instruments in the current CSV snapshot by name, category, price, stock and active promotion. Set on_sale_only=true to list discounted products. Returns exact stored prices; accessories are outside this catalog.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_price": {"type": ["number", "null"]},
            "limit": {"type": "integer"},
            "in_stock_only": {"type": "boolean"},
            "on_sale_only": {"type": "boolean"},
        },
        "required": ["query", "max_price", "limit", "in_stock_only", "on_sale_only"],
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


def requested_promotion_listing(message: str) -> bool:
    normalized = unicodedata.normalize("NFKD", message.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return bool(re.search(r"\b(?:quais|todos|liste|mostre|tem|ha)\b", normalized)
                and re.search(r"\b(?:produtos?|itens?|instrumentos?)\b", normalized)
                and re.search(r"\b(?:desconto|promocao|promocionais?)\b", normalized))


def execute(store, arguments: dict, customer_message: str = "") -> dict:
    arguments = dict(arguments)
    if requested_promotion_listing(customer_message):
        arguments["query"] = ""
        arguments["on_sale_only"] = True
        arguments["limit"] = 12
        if not re.search(r"R\$\s*[\d.,]+", customer_message):
            arguments["max_price"] = None
        if not re.search(r"\b(?:estoque|dispon[ií]ve[il]s?)\b", customer_message,
                         re.IGNORECASE):
            arguments["in_stock_only"] = False
    category = requested_category(customer_message)
    if category and not arguments.get("query", "").strip():
        arguments["query"] = category
    result = store.search_products(**arguments)
    result["applied_query"] = arguments.get("query", "")
    result["applied_on_sale_only"] = arguments.get("on_sale_only", False)
    return result
