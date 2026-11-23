"""Small reproducible fallback for demos when no model API key is available."""

import re

from store import Store


class OfflineAgent:
    def __init__(self, store: Store):
        self.store = store

    def ask(self, message: str) -> str:
        lower = message.casefold()
        if any(word in lower for word in ("cordas", "palhetas", "amplificador", "pedal")):
            self.store.get_policy("escopo acessórios")
            return "Sou o assistente virtual da Empório da Música. Trabalhamos com instrumentos musicais, mas não vendemos acessórios como cordas, palhetas, pedais ou amplificadores."
        if any(word in lower for word in ("pedido", "rastre", "entrega do meu")):
            number = re.search(r"\b(?:pedido\s*(?:n[ºo.]*)?\s*#?)(\d+)\b", lower)
            email = re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", message, re.I)
            if not number or not email:
                return "Sou o assistente virtual da Empório da Música. Para consultar seu pedido, informe o número e o e-mail usado na compra."
            result = self.store.get_order(number.group(1), email.group())
            if "error" in result:
                return "Não consegui confirmar esse pedido com os dados informados. Confira o número e o e-mail ou fale com a equipe."
            delivery = f" Previsão registrada: {result['estimated_delivery']}." if result["estimated_delivery"] else ""
            tracking = f" Código cadastrado: {result['tracking_code']}." if result["tracking_code"] else ""
            return f"Pedido {result['order_id']}: status registrado como {result['status']}.{delivery}{tracking} Não consulto a transportadora em tempo real."
        if any(word in lower for word in ("violão", "violao", "violões", "violoes", "guitarra", "baixo", "teclado", "takamine", "yamaha", "ohana", "produto", "preço", "preco", "custa")):
            budget = re.search(r"(?:r\$\s*|até\s+)([\d.]+)(?:,(\d{1,2}))?", lower)
            max_price = float(budget.group(1).replace(".", "") + "." + (budget.group(2) or "00")) if budget else None
            category = next((c for c in ("violões", "violoes", "violão", "violao", "guitarra", "baixo", "teclado") if c in lower), None)
            model = re.search(r"(takamine\s+[\w-]+|yamaha\s+[\w-]+|ohana\s+[\w-]+)", message, re.I)
            query = model.group() if model else (category or "")
            result = self.store.search_products(query, max_price, limit=5, in_stock_only="dispon" in lower)
            if not result["results"]:
                return "Não encontrei opções correspondentes no catálogo atual. Posso ajudar a buscar outro modelo."
            lines = []
            for item in result["results"]:
                price = item["price_brl"]
                if item["discount_percent"]:
                    price += f" (antes {item['original_price_brl']}, {item['discount_percent']:g}% de desconto)"
                stock = "disponível" if item["stock_quantity"] > 0 else "sem estoque"
                lines.append(f"{item['name']}: {price}; {stock}.")
            more = f" Há mais {result['total_matches'] - len(lines)} opções; posso refinar a busca." if result["total_matches"] > len(lines) else ""
            pix = " Promoções não acumulam com os 5% de desconto do PIX." if "pix" in lower else ""
            return "Sou o assistente virtual da Empório da Música. Consultei o catálogo: " + " ".join(lines) + more + pix
        if any(word in lower for word in ("devol", "arrepend", "troca")):
            self.store.get_policy("direito de arrependimento compras online")
            return ("Sou o assistente virtual da Empório da Música. Para compra online, o manual prevê solicitar devolução "
                    "em até 7 dias corridos após o recebimento, com produto na embalagem original e sem sinais de uso. "
                    "O frete de retorno é da loja nesse caso. A equipe precisa conferir seu pedido antes de iniciar o processo.")
        if any(word in lower for word in ("endereço", "endereco", "horário", "horario", "aberto")):
            self.store.get_policy("endereço horário de funcionamento")
            return ("Sou o assistente virtual da Empório da Música. Estamos na Rua 14 de Maio, 3200, Centro, "
                    "Campo Grande/MS. O horário regular é segunda a sexta, 9h às 18h, e sábado, 9h às 13h. "
                    "Domingos e feriados: fechado. Datas especiais podem ter alteração.")
        return "Sou o assistente virtual da Empório da Música. Posso ajudar com instrumentos, preços, disponibilidade, pedidos e políticas da loja. Qual é sua dúvida?"
