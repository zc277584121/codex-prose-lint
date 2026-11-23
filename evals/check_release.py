"""Check Chinese fixtures at the release defaults, with optional live judgments."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from run import evaluate, metrics

from codex_prose_lint import __version__
from codex_prose_lint.config import Config, api_key, load_config
from codex_prose_lint.judge import PROMPT_HASH
from codex_prose_lint.scan import scan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize OpenRouter API usage.")
    parser.add_argument("--output", type=Path, default=Path(f"evals/results.v{__version__}.zh.json"))
    args = parser.parse_args()
    config = Config()
    sources = {"baseline": Path("evals/cases.zh.jsonl"), "expanded_cues": Path("evals/cases.expanded.zh.jsonl")}
    cases = []
    for dataset, path in sources.items():
        for line in path.read_text().splitlines():
            case = json.loads(line)
            assert set(case["expected"]) <= {item.text for item in scan(case["answer"])}, case["id"]
            cases.append({**case, "dataset": dataset})
    if not args.live:
        print(f"Validated {len(cases)} Chinese fixtures; add --live to call OpenRouter.")
        return
    key = api_key(load_config())

    def run_case(case: dict) -> dict:
        return {**evaluate(case, config.context_mode, "batch", key), "dataset": case["dataset"]}

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(run_case, cases))
    result = {"version": __version__, "timestamp_utc": datetime.now(UTC).isoformat(),
              "prompt_hash": PROMPT_HASH, "config": asdict(config),
              "dataset_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sources.items()},
              "scanner_sha256": hashlib.sha256(Path("src/codex_prose_lint/scan.py").read_bytes()).hexdigest(),
              "cases": len(cases), "total_requests": sum(row["requests"] for row in rows),
              "total_cost_usd": sum(row["cost_usd"] for row in rows),
              "median_seconds": statistics.median(row["elapsed_seconds"] for row in rows if row["requests"]),
              "summaries": {dataset: metrics([r for r in rows if r["dataset"] == dataset], config.threshold)
                            for dataset in sources}, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
