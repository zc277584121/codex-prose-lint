"""Repeat the order-test cases unchanged to estimate ordinary request variation."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from run import evaluate

from codex_prose_lint.config import api_key, load_config
from codex_prose_lint.judge import PROMPT_HASH
from codex_prose_lint.scan import scan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--data", type=Path, default=Path("evals/cases.zh.jsonl"))
    parser.add_argument("--baseline", type=Path, default=Path("evals/results.zh.json"))
    parser.add_argument("--output", type=Path, default=Path("evals/stability.zh.json"))
    args = parser.parse_args()
    if not args.live:
        parser.error("Add --live to authorize OpenRouter usage")
    baseline = json.loads(args.baseline.read_text())
    if baseline["prompt_hash"] != PROMPT_HASH:
        raise ValueError("Baseline uses a different prompt")
    cases = [json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    cases = [case for case in cases if case["split"] == "calibration" and len(scan(case["answer"])) >= 2]
    key = api_key(load_config())
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda case: evaluate(case, "paragraph", "batch", key), cases))
    result = {"timestamp_utc": datetime.now(UTC).isoformat(), "prompt_hash": PROMPT_HASH,
              "baseline": str(args.baseline), "rows": rows,
              "total_requests": sum(row["requests"] for row in rows),
              "total_cost_usd": sum(row["cost_usd"] for row in rows)}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
