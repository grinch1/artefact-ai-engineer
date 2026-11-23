"""Deterministic guardrails for rules that must not depend on model compliance.

These responses are intentionally limited to facts checked against the supplied
policy PDF and the current CSV snapshot. Unknown or changed rules fail closed.
"""

import re
from decimal import Decimal

from store import Store, normalize


ACCESSORIES = ("corda", "cordas", "palheta", "palhetas", "cabo", "cabos",
               "case", "cases", "pedal", "pedais", "amplificador", "amplificadores")


def _policy_has(store: Store, page: int, *phrases: str) -> bool:
    if len(store.policy_pages) < page:
        return False
    source = normalize(" ".join(store.policy_pages[page - 1].split()))
    return all(normalize(phrase) in source for phrase in phrases)


def guarded_answer(store: Store, message: str) -> tuple[str | None, list[str]]:
    """Answer a small set of high-risk intents with verified source facts."""
    lower = normalize(message)
    if re.search(r"\b(?:" + "|".join(ACCESSORIES) + r")\b", lower) and any(
        word in lower for word in ("vende", "voces", "tem ", "comprar", "disponivel")
    ):
        store.get_policy("acessorios nao comercializamos cordas palhetas")
        if not _policy_has(store, 2, "não comercializamos acessórios", "cordas"):
            return "Preciso confirmar a disponibilidade desse item com a equipe.", ["get_policy"]
        return ("Sou o assistente virtual da Empório da Música. Não vendemos acessórios "
                "como cordas, palhetas, cabos, pedais ou amplificadores; trabalhamos com "
                "instrumentos musicais."), ["get_policy"]

    order = ("pedido" in lower or "compra" in lower) and any(
        word in lower for word in ("enviado", "status", "rastre", "minha entrega", "chegou")
    )
    if order:
        number = re.search(r"\bpedido\s*(?:n[ºo.]*)?\s*#?\s*(\d+)\b", lower)
        email = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", message, re.I)
        if not number or not email:
            return ("Sou o assistente virtual da Empório da Música. Para consultar seu pedido, "
                    "informe o número do pedido e o e-mail usado na compra."), []
        result = store.get_order(number.group(1), email.group())
        if "error" in result:
            return "Não consegui confirmar esse pedido com os dados informados. Confira-os ou fale com a equipe.", ["get_order"]
        return (f"Sou o assistente virtual da Empório da Música. Pedido {result['order_id']}: "
                f"status registrado como {result['status']}. "
                "Não consulto a transportadora em tempo real."), ["get_order"]

    if any(word in lower for word in ("arrepend", "devolv", "devolucao")) and "online" in lower:
        store.get_policy("direito de arrependimento compras online")
        if not _policy_has(store, 4, "7 (sete) dias corridos", "embalagem original", "frete de devolução"):
            return "Preciso confirmar a política de devolução com a equipe.", ["get_policy"]
        return ("Sou o assistente virtual da Empório da Música. Em compras online, você pode "
                "solicitar a devolução em até 7 dias corridos após receber o produto, sem "
                "justificativa. Ele deve estar na embalagem original, sem sinais de uso, "
                "com acessórios e manuais. Nesse caso, o frete de retorno fica por conta da "
                "loja; a equipe precisa conferir o pedido para iniciar o processo."), ["get_policy"]

    mentioned_product = any(normalize(row["name"]) in lower for row in store.tables["products"])
    promotion_question = any(word in lower for word in ("desconto", "promoc", "acumula"))
    if "pix" in lower or (promotion_question and mentioned_product):
        store.get_policy("promocoes desconto pix cumulatividade")
        if not _policy_has(store, 6, "promoções não são cumulativas", "não se aplica sobre preços já promocionais"):
            return "Preciso confirmar as regras de desconto com a equipe.", ["get_policy"]
        model = re.search(r"\b[A-Z]{1,8}-?\d[A-Z0-9-]*\b", message, re.I)
        matched_name = next((row["name"] for row in store.tables["products"]
                             if normalize(row["name"]) in lower), None)
        product_query = matched_name or (model.group() if model else None)
        if product_query:
            result = store.search_products(product_query, limit=3)
            products = result["results"]
            if matched_name:
                products = [item for item in products
                            if normalize(item["name"]) == normalize(matched_name)]
            if len(products) == 1:
                product = products[0]
                if product["discount_percent"]:
                    pix_rule = ("O desconto adicional de 5% no PIX não acumula com essa promoção. "
                                if "pix" in lower else "")
                    return (f"Sou o assistente virtual da Empório da Música. "
                            f"{product['name']} está por {product['price_brl']} "
                            f"(antes {product['original_price_brl']}, "
                            f"{product['discount_percent']:g}% de desconto). "
                            f"{pix_rule}"
                            f"Estoque registrado: {product['stock_quantity']} unidade(s)."), ["get_policy", "search_products"]
                if "pix" not in lower:
                    return (f"Sou o assistente virtual da Empório da Música. "
                            f"{product['name']} está por {product['price_brl']}; não há "
                            "promoção ativa para esse produto no catálogo consultado."), ["get_policy", "search_products"]
                return (f"Sou o assistente virtual da Empório da Música. "
                        f"{product['name']} está por {product['price_brl']}, ou "
                        f"{product['pix_price_brl']} no PIX. Não há promoção ativa para "
                        "esse produto no catálogo consultado."), ["get_policy", "search_products"]
        return ("Sou o assistente virtual da Empório da Música. Promoções não acumulam "
                "com o desconto de 5% no PIX. Se me disser o modelo, consulto o preço atual."), ["get_policy"]

    if any(word in lower for word in ("horario", "aberto", "funcionamento", "expediente")):
        store.get_policy("horario de funcionamento")
        if not _policy_has(store, 2, "09:00 às 18:00", "09:00 às 13:00", "Domingo e Feriados Fechado"):
            return "Preciso confirmar o horário de funcionamento com a equipe.", ["get_policy"]
        return ("Sou o assistente virtual da Empório da Música. A loja funciona de segunda a "
                "sexta, das 9h às 18h, e aos sábados, das 9h às 13h. Domingos e feriados: "
                "fechado. Datas especiais podem ter horário alterado."), ["get_policy"]

    if any(word in lower for word in ("frete", "envio", "entrega")) and not any(
        word in lower for word in ("meu pedido", "minha entrega", "rastre")
    ):
        store.get_policy("frete entregas Campo Grande")
        if "campo grande" in lower:
            if not _policy_has(store, 4, "Frete grátis para pedidos acima de R$ 500,00",
                               "taxa fixa de R$ 35,00", "1 a 3 dias úteis"):
                return "Preciso confirmar a política de frete com a equipe.", ["get_policy"]
            amount = re.search(r"r\$\s*([\d.]+(?:,\d{1,2})?)", lower)
            if amount:
                value = Decimal(amount.group(1).replace(".", "").replace(",", "."))
                if value < 500:
                    return ("Sou o assistente virtual da Empório da Música. Para um pedido de "
                            "valor abaixo de R$ 500,00 na região metropolitana de Campo "
                            "Grande, a taxa de frete registrada é R$ 35,00 e o prazo é de "
                            "1 a 3 dias úteis. Confirme a área de entrega com a equipe."), ["get_policy"]
                if value > 500:
                    return ("Sou o assistente virtual da Empório da Música. Para pedidos acima "
                            "de R$ 500,00 na região metropolitana de Campo Grande, o frete é "
                            "grátis e o prazo é de 1 a 3 dias úteis. Confirme a área de entrega "
                            "com a equipe."), ["get_policy"]
                return "Para um pedido exatamente de R$ 500,00, preciso confirmar a regra de frete com a equipe.", ["get_policy"]
            return ("Sou o assistente virtual da Empório da Música. Na região metropolitana de "
                    "Campo Grande, o frete é grátis acima de R$ 500,00; abaixo disso, custa "
                    "R$ 35,00. O prazo informado é de 1 a 3 dias úteis."), ["get_policy"]
        return ("Sou o assistente virtual da Empório da Música. Para entregas fora da região "
                "metropolitana de Campo Grande, preciso confirmar o CEP e as dimensões do "
                "instrumento com a equipe antes de informar um valor de frete."), ["get_policy"]

    if any(word in lower for word in ("garantia", "defeito")):
        store.get_policy("garantia legal fabricante defeitos")
        if not _policy_has(store, 7, "90 (noventa) dias", "6 meses a 2 anos"):
            return "Preciso confirmar a política de garantia com a equipe.", ["get_policy"]
        return ("Sou o assistente virtual da Empório da Música. Os instrumentos têm garantia "
                "legal de 90 dias contra defeitos de fabricação, contados do recebimento. "
                "A garantia do fabricante varia conforme o produto, geralmente de 6 meses "
                "a 2 anos; as condições exatas constam no certificado que o acompanha."), ["get_policy"]

    if any(word in lower for word in ("parcel", "vezes", "10x", "12x", "6x", "3x")):
        store.get_policy("parcelamento cartao credito parcelas minimas")
        if not _policy_has(store, 3, "7x a 12x", "parcela mínima de R$ 100,00",
                           "4x a 6x", "parcela mínima de R$ 80,00"):
            return "Preciso confirmar as condições de parcelamento com a equipe.", ["get_policy"]
        parts = re.search(r"\b(\d{1,2})x\b", lower)
        amount = re.search(r"r\$\s*([\d.]+(?:,\d{1,2})?)", lower)
        if parts and amount:
            count = int(parts.group(1))
            value = Decimal(amount.group(1).replace(".", "").replace(",", "."))
            if count < 1 or count > 12:
                return ("Sou o assistente virtual da Empório da Música. O parcelamento "
                        "previsto vai de 1x a 12x, sujeito às parcelas mínimas."), ["get_policy"]
            minimum = 50 if count <= 3 else 80 if count <= 6 else 100
            if value / count < minimum:
                return ("Sou o assistente virtual da Empório da Música. Nesse valor, "
                        f"{count}x não atende à parcela mínima prevista na política. "
                        "De 7x a 12x, cada parcela deve ser de pelo menos R$ 100,00; "
                        "de 4x a 6x, pelo menos R$ 80,00."), ["get_policy"]
            return ("Sou o assistente virtual da Empório da Música. Esse valor atende à "
                    f"parcela mínima para {count}x sem juros no cartão, conforme a política. "
                    "A equipe deve confirmar a compra e a disponibilidade."), ["get_policy"]
        return ("Sou o assistente virtual da Empório da Música. O cartão de crédito permite "
                "até 12x sem juros, respeitando a parcela mínima: R$ 100,00 de 7x a 12x, "
                "R$ 80,00 de 4x a 6x e R$ 50,00 até 3x."), ["get_policy"]

    if any(word in lower for word in ("politica", "regra", "troca", "devolucao", "reembolso",
                                       "pagamento", "boleto", "privacidade", "lgpd", "endereco",
                                       "promoc", "desconto", "prazo")):
        return ("Sou o assistente virtual da Empório da Música. Para não informar uma regra "
                "incorreta, preciso confirmar esse ponto da política com a equipe."), []

    return None, []
