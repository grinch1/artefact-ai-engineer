# Local-model evaluation, 23 November 2026

Model: `gpt-oss:20b` through Ollama on the Mainframe. Each scenario starts with a fresh agent; the promotion follow-up deliberately uses two turns in one conversation. The original CSV snapshot and the reviewed `policy.json` were loaded by the application. No customer email or order status is included here.

The exploratory pass used 19 prompts across opening hours, returns, defect handling, free-shipping and installment boundaries, order privacy, prompt injection, and out-of-scope requests. Manual review found three factual errors: a return window described as business days instead of calendar days, a defect exchange window described as business days, and the R$ 100 installment band described as starting at six rather than seven installments. Some automated exploratory flags were wording mismatches, such as `sete` versus `7`; they were not counted as model failures.

The agent instructions now state those units and boundaries explicitly. `answer_issue` rejects the three observed unsupported claims and asks the model to rewrite its own response. No fixed customer answer was added. The corrected outputs for the three previously failing questions were checked against the real model.

The reproducible evaluator is `scripts/evaluate_local.py`. It checks 18 scenarios, records the model's answer, policy sections, tool calls, and targeted assertions as JSON lines, and exits nonzero on a failed assertion. On this date, the full run passed after manual review of the responses. The 22 unit tests also passed. The full-run count is a regression result for this model and snapshot, not a claim of perfect reliability or coverage of unseen wording.

To repeat with the supplied private case data:

```sh
python scripts/evaluate_local.py --data-dir "$DATA_DIR" --model gpt-oss:20b > evaluation.jsonl
python -m unittest discover -s tests -v
```

The remaining production checks are a larger paraphrase set, repeated runs to measure variability, and a separate comparison with a hosted model. The supplied order and catalog files are snapshots, so these tests do not establish live inventory or carrier tracking.
