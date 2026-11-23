"""Measure company-policy retrieval independently of the language model."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from store import Store  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    args = parser.parse_args()
    store = Store(args.data_dir)
    cases = json.loads((ROOT / "eval" / "retrieval_cases.json").read_text(encoding="utf-8"))
    failures = 0
    for case in cases:
        matches = store.get_policy(case["question"])["matches"]
        sections = [item["section"] for item in matches]
        hit = case["expected_section"] in sections
        failures += not hit
        print(json.dumps({"id": case["id"], "question": case["question"],
                          "expected_section": case["expected_section"],
                          "retrieved_sections": sections, "hit_at_3": hit},
                         ensure_ascii=False), flush=True)
    print(json.dumps({"total": len(cases), "hits_at_3": len(cases) - failures,
                      "misses": failures}), file=sys.stderr)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
