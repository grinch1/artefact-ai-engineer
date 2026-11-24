"""CLI service agent using OpenAI Responses function calling."""

import argparse
import json
import os
import re
from decimal import Decimal
from pathlib import Path

from agent_tools import DEFINITIONS as TOOLS, run_tool
from agent_tools.catalog import requested_promotion_listing
from store import Store, customer_safe_policy_text, normalize


def agent_instructions(store: Store) -> str:
    """Compose the runtime prompt from reviewed agent and application rules."""
    if hasattr(store, "agent_policies") and hasattr(store, "application_rules"):
        rules, capabilities = store.agent_policies, store.application_rules
    else:  # Lightweight test doubles use the same versioned policy file.
        config = json.loads(Path(__file__).resolve().with_name("policies.json").read_text(encoding="utf-8"))
        rules = config["agent_policies"]["rules"]
        capabilities = config["application_rules"]["capabilities"]
    lines = [rule["text_pt"] for rule in rules]
    lines.append("Capacidades desta aplicação:")
    lines.extend("Não posso " + item["action_pt"] + ". " + item["guidance_pt"]
                 for item in capabilities if not item["available"])
    return "\n".join(lines)


def default_policy_facts() -> dict:
    """Used by direct validator calls in tests; runtime passes Store.policy_facts."""
    config = json.loads(Path(__file__).resolve().with_name("policies.json").read_text(encoding="utf-8"))
    return {item["section"]: item.get("facts", {})
            for item in config["company_policies"]["sections"]}


def default_application_rules() -> list[dict]:
    config = json.loads(Path(__file__).resolve().with_name("policies.json").read_text(encoding="utf-8"))
    return config["application_rules"]["capabilities"]


def number_pattern(number: int) -> str:
    words = {6: "seis", 7: "sete", 8: "oito", 10: "dez", 12: "doze", 30: "trinta", 90: "noventa"}
    return "(?:" + str(number) + ("|" + words[number] if number in words else "") + ")"


def answer_issue(message: str, answer: str, tool_names=(), policy_facts: dict | None = None,
                 application_rules: list[dict] | None = None,
                 customer_messages: list[str] | None = None,
                 tool_results: list[dict] | None = None) -> str | None:
    """Reject known unsupported claims while keeping the wording model-generated."""
    facts = policy_facts if policy_facts is not None else default_policy_facts()
    capabilities = {item["id"]: item["available"] for item in
                    (application_rules if application_rules is not None else default_application_rules())}
    unavailable = lambda name: not capabilities.get(name, False)
    normalized_message = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", normalize(message)))
    normalized_answer = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", normalize(answer)))
    customer_messages = customer_messages or [message]
    verified_orders = [item["result"] for item in (tool_results or [])
                       if item["name"] == "get_order" and "status" in item["result"]]
    if verified_orders and (re.search(r"\bdata de entrega\b(?!\s+(?:estimada|prevista))",
                                      normalized_answer)
                            or re.search(r"\bentregue em\s+\d", normalized_answer)):
        return "O CSV só informa uma previsão de entrega. Não apresente essa data como a data efetiva do recebimento."
    if re.search(r"troca\s+por\s+defeit\w*.{0,85}\bgarantia\s+(?:do\s+)?fabricante\b",
                 normalized_answer):
        return "A janela de troca por defeito da loja é distinta da garantia contratual do fabricante."
    if re.search(r"\b(?:pecas|acessorios)\s+de\s+sopro\b.{0,35}\bnao\s+(?:sao\s+)?troc",
                 normalized_answer):
        return "A exclusão de troca vale para boquilhas de sopro, não para todas as peças de sopro."
    if re.search(r"\b(?:valor|minimo)\s+minimo\s+por\s+parcela\s+r\s*0\b",
                 normalized_answer):
        return "Para uma a três parcelas, diga 'sem mínimo por parcela'; não apresente R$ 0 como valor mínimo."
    installment_question = bool(re.search(r"\b(?:parcel\w*|pagar|pagamento|\d+\s*x)\b", normalized_message))
    if "search_products" in tool_names and "pix" not in normalized_message and "pix" in normalized_answer:
        return "A pergunta é sobre o catálogo, não sobre forma de pagamento. Omita os valores PIX não solicitados."
    if "metropolitan area" in normalized_answer:
        return "Responda inteiramente em português; use 'região metropolitana'."
    return_days = facts.get("4.1", {}).get("return_window_calendar_days")
    if (isinstance(return_days, int)
            and re.search(r"\b(?:devol|arrepend|desist|compr)\w*\b", normalized_message)
            and re.search(rf"\b{number_pattern(return_days)} dias uteis\b", normalized_answer)):
        return f"O prazo de arrependimento online é de {return_days} dias corridos, não úteis. Corrija a unidade."
    exchange_days = facts.get("4.2", {}).get("store_exchange_window_calendar_days")
    if (isinstance(exchange_days, int)
            and re.search(r"\b(?:defeit|troc|garant)\w*\b", normalized_message)
            and re.search(rf"\b{number_pattern(exchange_days)} dias uteis\b", normalized_answer)):
        return f"A janela de troca por defeito é de {exchange_days} dias corridos, não úteis. Corrija a unidade."
    if (isinstance(exchange_days, int)
            and facts.get("4.2", {}).get("store_exchange_start_event") == "purchase"
            and re.search(r"\b(?:defeit|troc)\w*\b", normalized_message)
            and re.search(rf"\b{number_pattern(exchange_days)} dias(?: corridos)?\b"
                          r".{0,38}\b(?:recebimento|entrega)\b", normalized_answer)):
        return f"A janela de troca de {exchange_days} dias começa na compra, não no recebimento. Corrija o marco inicial."
    legal_days = facts.get("8.1", {}).get("legal_warranty_calendar_days")
    reported_days = re.search(r"\b(\d{1,3})\s+dias\b", normalized_message)
    if (facts.get("4.2", {}).get("legal_warranty_conflict_requires_confirmation")
            and isinstance(exchange_days, int) and isinstance(legal_days, int)
            and reported_days and exchange_days < int(reported_days[1]) <= legal_days
            and re.search(r"\b(?:defeit|troc|garant)\w*\b", normalized_message)):
        if not re.search(rf"\b{number_pattern(exchange_days)}\s+dias\b", normalized_answer):
            return f"Explique também a janela de {exchange_days} dias corridos para troca por defeito na loja."
        if "confirm" not in normalized_answer:
            return ("Para defeito entre a janela de troca da loja e a garantia legal, "
                    "a relação entre as regras precisa ser confirmada pela equipe humana. "
                    "Não negue a troca nem direcione definitivamente ao fabricante.")
        if ("garantia legal" not in normalized_answer or not re.search(
                rf"\bgarantia legal\b.{{0,100}}\b{number_pattern(legal_days)}\s+dias\b",
                normalized_answer)):
            return (f"Mantenha a regra completa: a garantia legal é de {legal_days} dias "
                    "a partir do recebimento; a relação com a troca da loja exige confirmação humana.")
        if "fabricante" in normalized_answer:
            return "Para defeitos entre 31 e 90 dias, explique os dois prazos e peça confirmação humana sem sugerir o fabricante como próximo passo."
    bands = facts.get("3.1", {}).get("installment_bands", [])
    highest_band = max(bands, key=lambda item: item["from"], default=None)
    if (highest_band and highest_band["from"] > 1
            and installment_question
            and re.search(rf"\b{number_pattern(highest_band['from'] - 1)} (?:a|ate) "
                          rf"{number_pattern(highest_band['to'])} (?:parcelas|vezes)\b", normalized_answer)):
        return (f"A faixa de R$ {highest_band['minimum_installment_brl']} por parcela começa em "
                f"{highest_band['from']} parcelas. Corrija o limite ou omita a faixa.")
    if installment_question and re.search(
            r"\bcompras?\s+de\s+ate\s+r\s*\d+", normalized_answer):
        return "O mínimo por parcela não cria um valor máximo de compra. Reescreva sem dizer 'compras de até'."
    if installment_question and not re.search(r"\bpedido\D{0,6}\d+\b", message, re.IGNORECASE) and re.search(
            r"\b(?:informe|informar|envie|precisamos?)\b.{0,65}"
            r"\b(?:e[‑-]?mail|n[uú]mero\s+do\s+pedido)\b", answer,
            re.IGNORECASE | re.DOTALL):
        return "Parcelamento é uma pergunta geral. Não solicite e-mail nem número do pedido; oriente a confirmação humana sem coletar dados."
    if re.search(r"\bgaranti\w*\b|\bdefeit\w*\b", normalized_message) and re.search(
            r"\bgarantia legal do fabricante\b", normalized_answer):
        return "A garantia legal e a garantia contratual do fabricante são regras distintas. Corrija a atribuição."
    if re.search(r"\b(?:fabricante|suporte do fabricante)\b.{0,35}\b(?:sob|pela|atraves da)\s+garantia legal\b",
                 normalized_answer):
        return "A garantia legal não deve ser atribuída ao fabricante. Separe as regras e peça confirmação humana para o procedimento entre 31 e 90 dias."
    prices = re.findall(r"R\$\s*([\d.]+(?:,\d{2})?)", message, re.IGNORECASE)
    counts = re.findall(r"\b(\d{1,2})\s*(?:x\b|vezes\b)", message, re.IGNORECASE)
    if len(prices) == len(counts) == 1:
        amount = Decimal(prices[0].replace(".", "").replace(",", "."))
        count = int(counts[0])
        band = next((item for item in bands if item["from"] <= count <= item["to"]), None)
        threshold = band.get("purchase_below_brl_requires_confirmation") if band else None
        if (threshold is not None and amount < Decimal(str(threshold))
                and re.match(r"^(?:sim|pode|e permitido)\b", normalized_answer)):
            return "A política exige confirmação humana para esse valor. Não comece com uma aprovação definitiva."
        if (threshold is not None and amount < Decimal(str(threshold))
                and re.search(r"\b(?:ate|em)\s*(?:12|doze)\s*(?:x|vezes|parcelas)\b", normalized_answer)):
            return "Para essa compra de baixo valor, responda apenas à quantidade solicitada e à necessidade de confirmação humana."
    if re.search(r"(?m)^\|\s*[-:| ]{3,}\|\s*$", answer):
        return "A interface não renderiza tabelas Markdown. Reescreva como lista simples."
    if "**" in answer:
        return "A interface mostra Markdown como texto. Remova marcações de negrito e use texto simples."
    if (not re.search(r"devol|arrepend|troca", normalize(message))
            and re.search(r"\bpedido\D{0,6}\d+\b", message, re.IGNORECASE)
            and re.search(
            r"\b(?:informe|informar|preciso|qual)\b.{0,55}\bn[uú]mero\b|\bn[uú]mero completo\b",
            answer, re.IGNORECASE | re.DOTALL)):
        return "O número do pedido já foi informado. Peça apenas o e-mail da compra."
    if (re.search(r"devol|arrepend|troca", normalize(message))
            and not re.search(r"\bpedido\D{0,6}\d+\b", message, re.IGNORECASE)
            and re.search(r"\b(?:precis\w*|informe|informar|envie)\b.{0,110}"
                          r"\b(?:n[uú]mero\s+do\s+pedido|e[‑-]?mail|dados)\b",
                          answer, re.IGNORECASE | re.DOTALL)):
        return "A pergunta é sobre a regra geral de devolução ou troca. Não peça identificadores pessoais; explique a regra e oriente a equipe humana."
    if not facts.get("1.2", {}).get("contact_details_confirmed", False):
        answer_emails = {value.casefold() for value in
                         re.findall(r"[\w.+-]+@[\w.-]+\.[\w-]+", answer)}
        customer_emails = {value.casefold() for text in customer_messages for value in
                           re.findall(r"[\w.+-]+@[\w.-]+\.[\w-]+", text)}
        order_context = any(re.search(r"\bpedido\b", normalize(text)) for text in customer_messages)
        if (re.search(r"\(?\d{2}\)?\s*\d{4,5}\s*[-–]\s*\d{4}", answer)
                or answer_emails - customer_emails or (answer_emails and not order_context)):
            return "Há contato telefônico ou e-mail não confirmado no manual. Reescreva sem esses dados."
    if unavailable("external_shipping_quote") and re.search(r"frete|entrega|envio", message, re.IGNORECASE) and re.search(
            r"\b(?:posso|podemos)\b.{0,45}\b(?:estimar|cotar|calcular)\b", answer,
            re.IGNORECASE | re.DOTALL):
        return "Não existe ferramenta de cotação de frete. Reescreva sem oferecer estimativa ou cálculo."
    if unavailable("external_shipping_quote") and re.search(
            r"\b(?:fizemos|fiz|ja|consultei|consultamos|verifiquei|verificamos)\b"
            r".{0,30}\b(?:consulta|cotacao|consult\w*|verific\w*)\b.{0,55}"
            r"\b(?:transportadora\w*|correios|jadlog)\b|"
            r"\b(?:consultei|consultamos|verifiquei|verificamos)\b.{0,55}"
            r"\b(?:transportadora\w*|correios|jadlog)\b", normalize(answer)):
        return "Nenhuma transportadora foi consultada. Descreva apenas as regras do frete e a limitação desta aplicação."
    if unavailable("external_shipping_quote") and re.search(r"\b(?:frete|envio|entrega)\b",
                                                             normalized_message) and re.search(
            r"\bnao\s+consigo\s+(?:calcular|estimar|cotar)\b.{0,70}"
            r"\b(?:pois|porque|falta)\b.{0,70}\b(?:peso|dimens\w*|informac\w*)\b",
            normalized_answer):
        return "A limitação é a falta de integração de cotação, não apenas a ausência de peso ou dimensões."
    if (unavailable("external_shipping_quote")
            and re.search(r"\b(?:cotac\w*|valor exato|preco exato|quanto (?:sai|custa))\b",
                          normalized_message)
            and not re.search(r"\b(?:integrac\w*|ferramenta|acesso\s+(?:a|as|ao)\s+"
                              r"(?:sistema|transportadora))\b", normalized_answer)):
        return "Para uma cotação exata, esclareça que este chat não tem integração de cotação ou acesso ao sistema da transportadora."
    if unavailable("external_shipping_quote") and re.search(r"frete|entrega|envio", message, re.IGNORECASE) and re.search(
            r"\b(?:basta\s+(?:me\s+)?informar|me\s+informe|pode\s+(?:me\s+)?informar)\b"
            r".{0,100}\b(?:cep|dimens[oõ]es|peso)\b", answer,
            re.IGNORECASE | re.DOTALL):
        return "Não peça CEP, dimensões ou peso para uma cotação que esta aplicação não realiza."
    if unavailable("open_return") and re.search(r"devol|arrepend|troca", normalize(message)) and re.search(
            r"(?<!nao )\b(?:posso|podemos|vou|vamos|consigo|farei|irei)\b.{0,50}"
            r"\b(?:iniciar|abrir|registrar|solicitar|emitir|gerar)\b", normalized_answer):
        return "Não há ferramenta para iniciar a devolução nem emitir etiqueta. Explique a regra sem oferecer essa ação."
    if unavailable("open_return") and re.search(r"devol|arrepend|troca", normalize(message)) and re.search(
            r"\b(?:qual|informe|envie|(?<!nao )precis\w*)\b.{0,90}\b(?:e mail|email)\b",
            normalized_answer):
        return "Este chat não inicia devoluções. Não peça e-mail para uma ação que não pode executar."
    if unavailable("open_return") and re.search(
            r"\b(?:registr\w*|inici\w*|abr\w*|ger\w*|emit\w*)\b.{0,70}"
            r"\b(?:devol\w*|etiqueta)\b", normalize(message)) and re.search(
            r"\be\s*mail\b|\bemail\b", normalized_answer):
        return "Esta aplicação não registra devoluções. Não peça e-mail nem descreva coleta de dados para iniciar essa ação."
    if unavailable("open_return") and re.search(
            r"\b(?:registr\w*|inici\w*|abr\w*|ger\w*|emit\w*)\b.{0,70}"
            r"\b(?:devol\w*|etiqueta)\b", normalize(message)) and not re.search(
            r"\bnao\b.{0,25}\b(?:consigo|posso|inici\w*|registr\w*|ger\w*|emit\w*|e possivel)\b",
            normalize(answer)):
        return "O cliente pediu uma ação indisponível. Diga explicitamente que este chat não registra devoluções nem emite etiquetas."
    if unavailable("open_return") and re.search(r"devol|arrepend|troca", message, re.IGNORECASE) and re.search(
            r"(?:ajuda\s+para|ajudar?\s+a)\s+iniciar.{0,30}devolu[cç][aã]o", answer,
            re.IGNORECASE | re.DOTALL):
        return "Não ofereça iniciar a devolução. Oriente o cliente a procurar a equipe humana."
    if unavailable("open_return") and re.search(r"devol|arrepend|troca", normalize(message)) and re.search(
            r"\bse\s+(?:quiser|desejar|precisar)\s+iniciar.{0,35}devolu[cç][aã]o"
            r".{0,40}\bbasta\s+(?:falar|avisar|dizer)\b", answer,
            re.IGNORECASE | re.DOTALL):
        return "Este chat não inicia devoluções. Remova o convite e oriente o cliente a procurar a equipe humana."
    if unavailable("live_tracking") and "get_order" in tool_names and re.search(
            r"\b(?:posso|podemos|vou)\b.{0,55}\b(?:acompanhar|avisar|notificar|monitorar)\b|"
            r"\bacompanhar\s+(?:a\s+)?evolu[cç][aã]o\b", answer,
            re.IGNORECASE | re.DOTALL):
        return "O pedido vem de um snapshot, sem acompanhamento ao vivo. Reescreva sem oferecer monitoramento ou aviso futuro."
    if unavailable("forward_request") and re.search(r"\b(?:posso|podemos)\s+encaminhar\b|"
                 r"\bencaminh\w*\s+(?:sua|a)\s+solicita[cç][aã]o\b",
                 answer, re.IGNORECASE):
        return "Não há integração de encaminhamento. Oriente o cliente a procurar a equipe humana, sem afirmar que você fará o envio."
    if unavailable("process_data_deletion") and re.search(r"(?:exclu|apag).{0,20}dados|dados\s+pessoais", message,
                 re.IGNORECASE) and re.search(
            r"(?:pode\s+me\s+informar|me\s+informe|antes\s+de\s+encaminhar)", answer,
            re.IGNORECASE):
        return "Não colete dados pessoais nem prometa encaminhar a exclusão neste chat. Oriente a procurar a equipe humana."
    if unavailable("contact_directory") and re.search(r"\b(?:site|portal|website)\b", normalized_answer) and re.search(
            r"\b(?:canal|atendimento|contato|oficial)\b", normalized_answer):
        return "Nenhum site oficial de atendimento foi confirmado. Oriente a equipe humana sem indicar um canal específico."
    if unavailable("contact_directory") and re.search(r"(?:exclu|apag).{0,20}dados|dados\s+pessoais", message,
                 re.IGNORECASE) and re.search(
            r"\b(?:visite|acesse|consulte|procure)\b.{0,35}\b(?:site|website|portal)\b|"
            r"\b(?:site|website|portal)\b.{0,65}\b(?:encontrar|canais|contato)\b",
            answer, re.IGNORECASE | re.DOTALL):
        return "Nenhum site oficial foi fornecido. Não indique um canal de atendimento não verificado."
    if unavailable("contact_directory") and re.search(r"(?:exclu|apag).{0,20}dados|dados\s+pessoais", message,
                 re.IGNORECASE) and re.search(
            r"\b(?:posso|podemos)\b.{0,55}\b(?:indicar|mostrar|localizar)\b.{0,45}"
            r"\b(?:canais|contato|informac[aã]o)\b", answer, re.IGNORECASE | re.DOTALL):
        return "Não ofereça indicar canais de atendimento que não foram confirmados. Oriente a procurar a equipe humana."
    if unavailable("warranty_certificate") and re.search(r"garanti\w*", message, re.IGNORECASE) and re.search(
            r"consultar\s+o\s+cat[aá]logo\s+para\s+confirmar", answer, re.IGNORECASE):
        return "O catálogo não contém prazo de garantia por produto. A condição específica depende do certificado do fabricante."
    if unavailable("warranty_certificate") and re.search(r"garanti\w*", message, re.IGNORECASE) and re.search(
            r"\b(?:posso|podemos)\b.{0,70}\b(?:verificar|confirmar)\b.{0,35}\bcertificado\b",
            answer, re.IGNORECASE | re.DOTALL):
        return "Não há acesso ao certificado individual. Informe que o prazo específico consta nele."
    if unavailable("warranty_certificate") and re.search(r"garanti\w*", message, re.IGNORECASE) and re.search(
            r"\bbasta\s+me\s+(?:dizer|informar|passar)\b.{0,45}"
            r"\b(?:instrumento|produto|nome|modelo)\b",
            normalize(answer)):
        return ("Reescreva a resposta completa, mantendo os prazos gerais de garantia legal e do fabricante. "
                "O nome do instrumento não confirma a garantia específica; ela consta no certificado.")
    warranty_days = facts.get("8.1", {}).get("legal_warranty_calendar_days")
    if (isinstance(warranty_days, int) and re.search(r"\bgaranti\w*\b", normalized_message)
            and not re.search(rf"\b{number_pattern(warranty_days)}\s+dias\b", normalized_answer)):
        return (f"Inclua a garantia legal de {warranty_days} dias corridos a partir do recebimento, "
                "além da regra do fabricante consultada.")
    if re.search(r"\b\d{1,2}\s*(?:x|vezes)\b", message, re.IGNORECASE) and re.search(
            r"(?:outras?\s+op[cç][oõ]es|outr[oa]\s+(?:forma|m[eé]todo)\s+de\s+pagamento|"
            r"pagar\s+[aà]\s+vista|m[eé]todos?\s+combinados?|"
            r"(?:prefere|escolher|usar)\s+(?:o\s+)?(?:pix|boleto))", answer, re.IGNORECASE):
        return "A resposta de parcelamento deve tratar apenas a quantidade solicitada, sem oferecer alternativas."
    return None


def is_broad_policy_request(message: str) -> bool:
    """Recognize requests for the store's rules as a whole, not one rule."""
    normalized = normalize(message)
    return bool(re.search(r"\b(?:politicas|regras)\b", normalized)
                and re.search(r"\b(?:loja|emporio|todas|gerais)\b", normalized)
                and not re.search(r"\b(?:pedido|produto|frete|garantia|troca|devolucao|parcelamento)\b",
                                  normalized))


def is_policy_followup(message: str) -> bool:
    normalized = normalize(message).strip()
    return bool(re.fullmatch(r"(?:sim[, ]*)?(?:quero|gostaria|pode|me passe|me diga)?"
                             r"[ ,]*(?:essas?|todas?)?\s*(?:informacoes|detalhes|regras|politicas)"
                             r"[.!? ]*", normalized))


def policy_access_issue(answer: str, sections: list[str]) -> str | None:
    """A sourced answer cannot claim that the supplied policies are unavailable."""
    if sections and re.search(r"nao\s+(?:tenho|temos)\s+acesso\b.{0,70}"
                              r"\b(?:manual|politic\w*|regras?)\b", normalize(answer)):
        return "As políticas foram consultadas e estão no contexto. Resuma as regras relevantes, sem alegar falta de acesso."
    return None


def promotion_listing_issue(message: str, answer: str, tool_results: list[dict]) -> str | None:
    """Check a claimed complete promotion list against the filtered catalog result."""
    if not requested_promotion_listing(message):
        return None
    if re.search(r"\b(?:hoje|agora)\b|\bao vivo\b", normalize(answer)):
        return "Os preços e descontos vêm de um snapshot de demonstração. Não os descreva como dados ao vivo ou de hoje."
    results = [item["result"] for item in tool_results
               if item["name"] == "search_products" and
               item["result"].get("applied_on_sale_only") is True]
    if not results:
        return "Consulte search_products com on_sale_only=true antes de listar promoções."
    catalog = results[-1]
    if catalog.get("has_more"):
        return "A consulta está paginada. Não afirme que a lista de promoções está completa."
    compact_answer = re.sub(r"[^a-z0-9]", "", normalize(answer))
    missing = [item["name"] for item in catalog.get("results", [])
               if re.sub(r"[^a-z0-9]", "", normalize(" ".join(item["name"].split()[:2])))
               not in compact_answer]
    if missing:
        return "Inclua todos os produtos com desconto ativo retornados pela busca: " + ", ".join(missing)
    return None


def order_lookup_issue(message: str, customer_messages: list[str],
                       tool_results: list[dict]) -> str | None:
    """When both identifiers were supplied, require a verified lookup attempt."""
    if not (re.search(r"\b(?:pedido|status|rastre\w*)\b", normalize(message))
            or re.search(r"[\w.+-]+@[\w.-]+\.[\w-]+", message)):
        return None
    conversation = "\n".join(customer_messages)
    has_order = bool(re.search(r"\b(?:pedido|ordem|order|n[uú]mero)\b\D{0,28}\b\d+\b",
                               conversation, re.IGNORECASE))
    has_email = bool(re.search(r"[\w.+-]+@[\w.-]+\.[\w-]+", conversation))
    if has_order and has_email and not any(item["name"] == "get_order" for item in tool_results):
        return "O cliente já informou número e e-mail. Chame get_order antes de afirmar qualquer resultado ou pedir os dados outra vez."
    return None


def policy_evidence(store: Store, message: str, broad: bool = False,
                    followup: bool = False) -> tuple[str, list[str]]:
    """Retrieve structured policy evidence before either model is allowed to answer."""
    if (broad or is_broad_policy_request(message)) and hasattr(store, "policy_sections"):
        matches = [dict(item, text=customer_safe_policy_text(item["text"]),
                        facts=getattr(store, "policy_facts", {}).get(item["section"], {}))
                   for item in store.policy_sections]
    else:
        matches = store.get_policy(message).get("matches", [])[:3]
    sections = [f"{item['section']} (p. {item['page']})" for item in matches]
    excerpts = [{"section": item["section"], "page": item["page"],
                 "text": item["text"][:2200], "facts": item.get("facts", {})} for item in matches]
    price = re.findall(r"R\$\s*([\d.]+(?:,\d{2})?)", message, re.IGNORECASE)
    count = re.findall(r"\b(\d{1,2})\s*(?:x\b|vezes\b)", message, re.IGNORECASE)
    calculation = None
    if len(price) == len(count) == 1 and hasattr(store, "check_installment"):
        numeric_price = float(price[0].replace(".", "").replace(",", "."))
        calculation = store.check_installment(numeric_price, int(count[0]))
    followup_instruction = ("O cliente aceitou receber as informações oferecidas no turno anterior. "
                            "Forneça agora os detalhes disponíveis; não peça para ele escolher um assunto. "
                            if followup else "")
    context = ("Regras estruturadas derivadas do manual e consultadas antes desta resposta. Use somente as regras "
               "pertinentes; elas não substituem a consulta ao catálogo ou ao pedido. "
               "Se não houver trecho pertinente, não invente a política. "
               "Se o cliente pedir as políticas da loja em geral, resuma as principais regras por assunto "
               "em português simples. Você tem acesso às regras abaixo; não diga que o manual está indisponível. "
               "Não acrescente condições, exceções, prazos ou promessas sem apoio nas seções consultadas. " +
               followup_instruction + "\n" +
               json.dumps({"sections": excerpts, "verified_installment": calculation}, ensure_ascii=False))
    return context, sections


class Agent:
    def __init__(self, store: Store, model: str):
        from openai import OpenAI
        self.client = OpenAI()
        self.store = store
        self.model = model
        self.instructions = agent_instructions(store)
        self.history = []
        self.user_messages = []
        self.last_tools = []
        self.last_tool_results = []
        self.last_policy_request_was_broad = False

    def ask(self, message: str) -> str:
        self.last_tools = []
        self.last_tool_results = []
        followup = is_policy_followup(message) and self.last_policy_request_was_broad
        broad = is_broad_policy_request(message) or followup
        context, sections = policy_evidence(self.store, message, broad=broad, followup=followup)
        self.last_policy_request_was_broad = broad
        feedback = ""
        # Keep history in process only; no customer messages written to disk.
        self.user_messages = [*self.user_messages[-23:], message]
        self.history.append({"role": "user", "content": message})
        for _ in range(5):
            response = self.client.responses.create(model=self.model, instructions=self.instructions + "\n" + context + feedback,
                                                    tools=TOOLS, input=self.history, store=False)
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                answer = response.output_text.strip() or "Não consegui responder agora. Procure a equipe da loja para confirmar."
                issue = policy_access_issue(answer, sections) or promotion_listing_issue(
                    message, answer, self.last_tool_results) or order_lookup_issue(
                    message, self.user_messages, self.last_tool_results) or answer_issue(
                    message, answer, self.last_tools, getattr(self.store, "policy_facts", None),
                    getattr(self.store, "application_rules", None), self.user_messages,
                    self.last_tool_results)
                if issue:
                    feedback = "\nA resposta anterior foi rejeitada: " + issue
                    continue
                self.history.extend(item.model_dump(exclude_none=True) for item in response.output)
                # No unbounded conversation context.
                self.history = self.history[-30:]
                return answer
            self.history.extend(item.model_dump(exclude_none=True) for item in response.output)
            for call in calls:
                self.last_tools.append(call.name)
                result = run_tool(self.store, call.name, call.arguments, message,
                                  self.user_messages)
                self.last_tool_results.append({"name": call.name, "result": json.loads(result)})
                self.history.append({"type": "function_call_output", "call_id": call.call_id,
                                     "output": result})
        return "Não consegui verificar com segurança. Procure a equipe da loja para confirmar."


class OllamaAgent:
    """Local-GPU experiment through Ollama's OpenAI-compatible chat endpoint."""

    def __init__(self, store: Store, model: str, base_url: str, think: str | bool | None = None):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url.rstrip("/") + "/", api_key="ollama", timeout=90.0)
        self.store = store
        self.model = model
        self.think = think if think is not None else ("medium" if model.startswith("gpt-oss") else False)
        self.history = [{"role": "system", "content": agent_instructions(store)}]
        self.user_messages = []
        self.last_tools = []
        self.last_tool_calls = []
        self.last_tool_results = []
        self.last_policy_sections = []
        self.last_rejections = []
        self.last_policy_request_was_broad = False
        self.tools = [
            {"type": "function", "function": {key: value for key, value in tool.items() if key != "type"}}
            for tool in TOOLS
        ]

    def ask(self, message: str) -> str:
        self.last_tools = []
        self.last_tool_calls = []
        self.last_tool_results = []
        self.last_rejections = []
        followup = is_policy_followup(message) and self.last_policy_request_was_broad
        broad = is_broad_policy_request(message) or followup
        context, self.last_policy_sections = policy_evidence(self.store, message, broad=broad,
                                                             followup=followup)
        self.last_policy_request_was_broad = broad
        self.user_messages = [*self.user_messages[-23:], message]
        self.history.append({"role": "user", "content": message})
        repair_messages = []
        for _ in range(5):
            messages = [self.history[0], {"role": "system", "content": context},
                        *self.history[1:], *repair_messages]
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, tools=self.tools,
                tool_choice="auto", temperature=0.1, max_tokens=1800 if broad else 800,
                extra_body={"think": self.think},
            )
            reply = response.choices[0].message
            calls = reply.tool_calls or []
            if not calls:
                answer = (reply.content or "").strip() or "Não consegui responder agora. Procure a equipe da loja para confirmar."
                issue = policy_access_issue(answer, self.last_policy_sections) or promotion_listing_issue(
                    message, answer, self.last_tool_results) or order_lookup_issue(
                    message, self.user_messages, self.last_tool_results) or answer_issue(
                    message, answer, self.last_tools, getattr(self.store, "policy_facts", None),
                    getattr(self.store, "application_rules", None), self.user_messages,
                    self.last_tool_results)
                if issue:
                    self.last_rejections.append({"issue": issue, "answer": answer})
                    repair_messages = [{"role": "assistant", "content": answer},
                                       {"role": "user", "content": "Reescreva sua resposta: " + issue}]
                    continue
                self.history.append({"role": "assistant", "content": answer})
                self.history = [self.history[0], *self.history[-24:]]
                return answer
            self.history.append({"role": "assistant", "content": reply.content,
                                 "tool_calls": [{"id": c.id, "type": "function",
                                                 "function": {"name": c.function.name,
                                                              "arguments": c.function.arguments}} for c in calls]})
            for call in calls:
                self.last_tools.append(call.function.name)
                self.last_tool_calls.append({"name": call.function.name,
                                             "arguments": call.function.arguments})
                result = run_tool(self.store, call.function.name, call.function.arguments, message,
                                  self.user_messages)
                self.last_tool_results.append({"name": call.function.name,
                                               "result": json.loads(result)})
                self.history.append({"role": "tool", "tool_call_id": call.id,
                                     "content": result})
            repair_messages = []
        return "Não consegui verificar com segurança. Procure a equipe da loja para confirmar."


def main() -> None:
    parser = argparse.ArgumentParser(description="Empório da Música text agent")
    parser.add_argument("--data-dir", required=True, help="Directory with supplied CSVs and policy PDF")
    parser.add_argument("--model", default=None, help="Override the selected hosted or local model")
    parser.add_argument("--demo", action="store_true", help="Check local retrieval without an API key")
    parser.add_argument("--ollama", action="store_true", help="Use a local/private Ollama-compatible endpoint")
    args = parser.parse_args()
    store = Store(Path(args.data_dir))
    if args.demo:
        examples = [store.search_products("violao", 1000, in_stock_only=True), store.search_products("Takamine GD20"),
                    store.get_policy("direito de arrependimento compra online")]
        for result in examples:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.ollama:
        agent = OllamaAgent(store, args.model or os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                            os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435/v1"))
    elif not os.getenv("OPENAI_API_KEY"):
        parser.error("Set OPENAI_API_KEY, use --ollama for the Mainframe, or use --demo for retrieval")
    else:
        agent = Agent(store, args.model or os.getenv("OPENAI_MODEL", "gpt-5.4-mini"))
    print("Empório da Música (assistente virtual). Digite 'sair' para encerrar.")
    while True:
        try:
            message = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if message.lower() in ("sair", "exit", "quit"):
            break
        if message:
            try:
                print("Assistente:", agent.ask(message))
            except Exception as exc:
                print(f"Falha de consulta: {type(exc).__name__}. Tente novamente ou contate a equipe.")


if __name__ == "__main__":
    main()
