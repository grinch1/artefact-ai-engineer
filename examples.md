# Demonstration conversations

These responses were produced by the reproducible `--offline` mode against the supplied static case data. They demonstrate the same read-only lookup functions available to the LLM; they are not presented as live LLM outputs.

## 1. Instruments by budget and availability

**Customer:** Quais violões estão disponíveis por até R$ 1.000?

**Agent:** Sou o assistente virtual da Empório da Música. Consultei o catálogo: Giannini GF-1R Aço Folk Sunburst: R$ 579,90; disponível. Giannini GN-15 Nylon Cedr Natural: R$ 689,00; disponível. Rozini RC-104 Nylon Estudante: R$ 459,90; disponível. Shelby SGD-195E Elétrico Aço Sunburst: R$ 799,00; disponível. Shelby SN-100 Folk Aço Preto: R$ 549,00; disponível. Há mais 7 opções; posso refinar a busca.

**Source:** Product and category CSV snapshot, loaded into SQLite. The interface explains that stock is not live.

## 2. Order without verification

**Customer:** Meu pedido 9 já foi enviado?

**Agent:** Sou o assistente virtual da Empório da Música. Para consultar seu pedido, informe o número e o e-mail usado na compra.

**Source:** The order tool requires both fields. No order status is exposed in this turn.

## 3. Online return

**Customer:** Comprei online e me arrependi. Posso devolver?

**Agent:** Sou o assistente virtual da Empório da Música. Para compra online, o manual prevê solicitar devolução em até 7 dias corridos após o recebimento, com produto na embalagem original e sem sinais de uso. O frete de retorno é da loja nesse caso. A equipe precisa conferir seu pedido antes de iniciar o processo.

**Source:** Policy manual, section 4.1. The agent does not claim to initiate a return.

## 4. Promotion plus PIX policy

**Customer:** O ukulele Ohana CK-20 está com desconto? Se eu pagar no PIX, ganho mais 5%?

**Agent:** Sou o assistente virtual da Empório da Música. Consultei o catálogo: Ohana CK-20 Concert Natural: R$ 439,20 (antes R$ 549,00, 20% de desconto); disponível. Promoções não acumulam com os 5% de desconto do PIX.

**Source:** Product and promotion CSV snapshot plus policy manual, section 6.2.

## 5. Outside the catalog

**Customer:** Vocês vendem cordas para violão?

**Agent:** Sou o assistente virtual da Empório da Música. Trabalhamos com instrumentos musicais, mas não vendemos acessórios como cordas, palhetas, pedais ou amplificadores.

**Source:** Policy manual, sections 1 and 7.1.
