"""Opt-in Chinese live evaluation; data and results are safe to publish."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import httpx

from codex_prose_lint.config import Config, api_key, load_config
from codex_prose_lint.judge import PROMPT_HASH, judge
from codex_prose_lint.scan import scan


def metrics(rows: list[dict], threshold: float) -> dict:
    tp = fp = fn = tn = 0
    for row in rows:
        for item in row["candidates"]:
            expected = item["expected"]
            predicted = item["probability"] >= threshold
            tp += bool(expected and predicted)
            fp += bool(not expected and predicted)
            fn += bool(expected and not predicted)
            tn += bool(not expected and not predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f05 = 1.25 * precision * recall / (0.25 * precision + recall) if precision + recall else 0.0
    return {"threshold": threshold, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f0.5": f05}


def evaluate(case: dict, context_mode: str, grouping: str, key: str, reverse: bool = False) -> dict:
    items = scan(case["answer"])
    found = {item.text for item in items}
    missed = set(case["expected"]) - found
    if missed:
        raise ValueError(f"Lexical scan missed labeled spans in {case['id']}: {missed}")
    if reverse:
        items = list(reversed(items))
    config = replace(Config(), context_mode=context_mode)
    retries = 0
    while True:
        try:
            result = judge(items, case["question"], config, key, question_mode=grouping)
            break
        except httpx.TransportError:
            if retries >= 2:
                raise
            retries += 1
            time.sleep(retries)
    return {"case_id": case["id"], "split": case["split"], "context_mode": context_mode,
            "grouping": grouping, "reversed": reverse, "model": result.model,
            "elapsed_seconds": result.elapsed_seconds, "cost_usd": result.cost_usd,
            "requests": result.requests, "transport_retries": retries, "candidates": [
                {"id": item.id, "text": item.text, "start": item.start, "end": item.end,
                 "expected": item.text in case["expected"], "probability": result.scores[item.id]}
                for item in items
            ]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Authorize live OpenRouter API usage.")
    parser.add_argument("--data", type=Path, default=Path("evals/cases.zh.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("evals/results.zh.json"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    for case in cases:
        found = {item.text for item in scan(case["answer"])}
        if set(case["expected"]) - found:
            raise ValueError(f"Missing expected candidates: {case['id']}: {set(case['expected']) - found}")
    if not args.live:
        print(f"Validated {len(cases)} Chinese fixtures; add --live to call OpenRouter.")
        return
    key = api_key(load_config())
    jobs = [(case, mode, grouping, False) for case in cases
            for mode in ("clause", "sentence", "paragraph") for grouping in ("batch", "single")]
    jobs.extend((case, "paragraph", "batch", True) for case in cases
                if case["split"] == "calibration" and len(scan(case["answer"])) >= 2)
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output.with_suffix(".partial.jsonl")
    identity = {"prompt_hash": PROMPT_HASH, "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
                "model": Config().model}
    if checkpoint.exists():
        saved = [json.loads(line) for line in checkpoint.read_text().splitlines() if line.strip()]
        if saved[0] != identity:
            raise ValueError("Checkpoint belongs to a different prompt, model, or dataset; choose another output path")
        rows = saved[1:]
    else:
        checkpoint.write_text(json.dumps(identity) + "\n")
    done = {(r["case_id"], r["context_mode"], r["grouping"], r["reversed"]) for r in rows}
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(evaluate, case, mode, grouping, key, reverse): (case["id"], mode, grouping, reverse)
                   for case, mode, grouping, reverse in jobs
                   if (case["id"], mode, grouping, reverse) not in done}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            with checkpoint.open("a") as stream:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            if len(rows) % 16 == 0:
                print(f"Completed {len(rows)}/{len(jobs)} cases; ${sum(r['cost_usd'] for r in rows):.6f}", flush=True)
    rows.sort(key=lambda row: (row["case_id"], row["context_mode"], row["grouping"], row["reversed"]))
    summaries = []
    thresholds = [0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
    for mode in ("clause", "sentence", "paragraph"):
        for grouping in ("batch", "single"):
            selected = [r for r in rows if r["context_mode"] == mode and r["grouping"] == grouping and not r["reversed"]]
            calibration = [r for r in selected if r["split"] == "calibration"]
            validation = [r for r in selected if r["split"] == "validation"]
            scores = [metrics(calibration, threshold) for threshold in thresholds]
            best = max(scores, key=lambda result: (result["f0.5"], result["precision"], result["threshold"]))
            summaries.append({"context_mode": mode, "grouping": grouping, "calibration": best,
                              "validation": metrics(validation, best["threshold"]),
                              "threshold_sweep": scores,
                              "median_seconds": statistics.median(r["elapsed_seconds"] for r in selected if r["requests"]),
                              "cost_usd": sum(r["cost_usd"] for r in selected),
                              "requests": sum(r["requests"] for r in selected)})
    result = {"timestamp_utc": datetime.now(UTC).isoformat(), "prompt_hash": PROMPT_HASH,
              "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
              "config": asdict(Config()), "cases": len(cases), "total_seconds": time.monotonic() - start,
              "total_cost_usd": sum(r["cost_usd"] for r in rows),
              "total_requests": sum(r["requests"] for r in rows), "summaries": summaries, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
