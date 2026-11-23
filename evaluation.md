# Local model evaluation, 23 November 2026

## What is measured

The test separates policy retrieval from model responses. `eval/retrieval_cases.json` contains 31 customer phrasings with an expected company-policy section. `scripts/evaluate_retrieval.py` checks whether that section appears in the top three retrieved results, without calling a language model. The observed result was 31/31 hits.

`scripts/evaluate_local.py` runs 26 customer scenarios with `gpt-oss:20b` through Ollama on the private Mainframe. `--repeat 2` creates a fresh agent for each of 52 model runs. Scenarios cover catalog accuracy, orders without identity verification, active promotion and PIX, policy boundaries, uncertain cases, prompt injection, and a two-turn follow-up. JSON lines record the final answer, policy sections, tool calls, rejected drafts, and targeted checks. The evaluator exits nonzero on failed checks. The private case CSVs remain outside the repository; the published cases use no customer email or verified order status.

These checks measure specific claims, not general correctness. The first expanded run had false alarms from literal word checks (`sete` versus `7`, and a conditional mention of tracking). Manual review also found real errors that passed the checks: treating R$ 400 as a maximum purchase for five installments, moving the defect-exchange start from purchase to receipt, approving a R$ 40 installment before human confirmation, sending a day-45 defect case definitively to the manufacturer, and suggesting unrequested payment alternatives. Each finding became a policy or evaluator change and a local regression assertion. This is why the raw answers and rejected drafts are retained for review.

The independent retrieval run passed 31/31 in `evidence/policy-retrieval-2026-11-23.jsonl`. One expanded model run passed 51/52 checks in `evidence/gpt-oss-20b-expanded-2026-11-23.jsonl`; the failure omitted the 90-day legal warranty while asking for human confirmation on a day-45 defect. A later full run passed 52/52 automated checks in `evidence/gpt-oss-20b-postfix-2026-11-23.jsonl`, but manual review found another day-45 answer that mentioned “31 to 90 days” without actually explaining the legal warranty. The evaluator and answer gate now require an explicit legal-warranty statement; the affected case passed 3/3 fresh repetitions in `evidence/gpt-oss-20b-defect-recheck-2026-11-23.jsonl`. The earlier eighteen-case run remains in `evidence/gpt-oss-20b-2026-11-23.jsonl`. A full repeated run after that last correction remains open. These counts demonstrate behavior for the measured prompts and snapshot, not perfect reliability on unseen requests.

## Repeat locally

```sh
python scripts/evaluate_retrieval.py --data-dir "$DATA_DIR" > retrieval.jsonl
python scripts/evaluate_local.py --data-dir "$DATA_DIR" --model gpt-oss:20b --repeat 2 > model.jsonl
python -m unittest discover -s tests -v
```

For the next evaluation cycle, add held-out paraphrases and longer conversations, compare a hosted model on the same cases, and measure failures and latency separately. The static CSV snapshot cannot verify live inventory, order state, or carrier tracking.
