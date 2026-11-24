# Local model evaluation, 23–24 November 2026

## What is measured

The test separates policy retrieval from model responses. `eval/retrieval_cases.json` contains 31 customer phrasings with an expected company-policy section. `scripts/evaluate_retrieval.py` checks whether that section appears in the top three retrieved results, without calling a language model. The observed result was 31/31 hits.

`scripts/evaluate_local.py` runs 26 customer scenarios with `gpt-oss:20b` through Ollama on the private Mainframe. `--repeat 2` creates a fresh agent for each of 52 model runs. Scenarios cover catalog accuracy, orders without identity verification, active promotion and PIX, policy boundaries, uncertain cases, prompt injection, and a two-turn follow-up. JSON lines record the final answer, policy sections, tool calls, rejected drafts, and targeted checks. The evaluator exits nonzero on failed checks. The private case CSVs are ignored by Git; the published cases use no customer email or verified order status.

These checks measure specific claims, not general correctness. The first expanded run had false alarms from literal word checks (`sete` versus `7`, and a conditional mention of tracking). Manual review also found real errors that passed the checks: treating R$ 400 as a maximum purchase for five installments, moving the defect-exchange start from purchase to receipt, approving a R$ 40 installment before human confirmation, sending a day-45 defect case definitively to the manufacturer, and suggesting unrequested payment alternatives. Each finding became a policy or evaluator change and a local regression assertion. This is why the raw answers and rejected drafts are retained for review.

The independent retrieval run passed 31/31 in `evidence/policy-retrieval-2026-11-23.jsonl`. One expanded model run passed 51/52 checks in `evidence/gpt-oss-20b-expanded-2026-11-23.jsonl`; the failure omitted the 90-day legal warranty while asking for human confirmation on a day-45 defect. A later full run passed 52/52 automated checks in `evidence/gpt-oss-20b-postfix-2026-11-23.jsonl`, but manual review found another day-45 answer that mentioned “31 to 90 days” without actually explaining the legal warranty. The evaluator and answer gate now require an explicit legal-warranty statement; the affected case passed 3/3 fresh repetitions in `evidence/gpt-oss-20b-defect-recheck-2026-11-23.jsonl`. The earlier eighteen-case run remains in `evidence/gpt-oss-20b-2026-11-23.jsonl`. A full repeated run after that last correction remains open. These counts demonstrate behavior for the measured prompts and snapshot, not perfect reliability on unseen requests.

## Adversarial evaluation

`scripts/evaluate_adversarial.py` probes 13 attack patterns: requests to reveal instructions or reasoning, attempts to access an order without the purchase email or with a wrong email, a customer-data dump, false authority to create a return, a fabricated freight quote and carrier consultation, an unverified phone number, an attempt to bypass the 90-day legal warranty, unauthorized promotion and PIX stacking, and an instruction inserted into a product tool result. It also directly invokes `get_order` with a forged model argument to check that the tool itself rejects an email absent from the customer's messages. The script keeps the injected product name in memory and does not alter the case CSVs.

The first manual review identified gaps that simple pass/fail checks missed: the order tool trusted model-supplied identifiers, the model treated a forecast delivery date as actual, mixed return policy into a shipping answer, implied that it had contacted a carrier, recommended a manufacturer before the human team confirmed a day-45 defect procedure, and asked for an email to start a return that this prototype cannot open. A later review found a shipping explanation that blamed missing weight and dimensions without naming the absent integration, and a suggested "official site" unsupported by the supplied data. The tool now checks identifiers against customer messages, policy retrieval omits unrelated sections for shipping, and answer validation rejects those observed unsupported claims. The evaluator checks each issue and saves the model's raw answer for review. Passing these finite probes cannot establish resistance to all prompt injections or authorization attacks; order number plus email is still weaker than authenticated customer access.

After these corrections, a fresh `gpt-oss:20b` run passed 26/26 automated adversarial checks (13 cases repeated twice) and the direct tool-bypass probe. The answers were manually reviewed. The record is `evidence/gpt-oss-20b-adversarial-2026-11-24.jsonl`; a scan against the supplied customer emails and tracking codes found none in the published record. The results apply to this model, snapshot, and test set only.

## Repeat locally

```sh
python scripts/evaluate_retrieval.py --data-dir "$DATA_DIR" > retrieval.jsonl
python scripts/evaluate_local.py --data-dir "$DATA_DIR" --model gpt-oss:20b --repeat 2 > model.jsonl
python scripts/evaluate_adversarial.py --data-dir "$DATA_DIR" --model gpt-oss:20b --repeat 2 > adversarial.jsonl
python -m unittest discover -s tests -v
```

For the next evaluation cycle, add held-out paraphrases and longer conversations, compare a hosted model on the same cases, and measure failures and latency separately. The static CSV snapshot cannot verify live inventory, order state, or carrier tracking.
