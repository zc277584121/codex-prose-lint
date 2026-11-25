"""Offline candidate coverage and Stop review-payload verification."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from codex_prose_lint import __version__
from codex_prose_lint.config import Config
from codex_prose_lint.hook import process, select_candidates


def main() -> None:
    cases = []
    for path in (Path("evals/cases.zh.jsonl"), Path("evals/cases.expanded.zh.jsonl")):
        cases.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    cases.extend([
        {"id": "architecture", "answer": "不能一起归入旧架构。", "expected": ["不能一起归入旧架构"]},
        {"id": "selection", "answer": "我不会把普通 pgvector 作为这套方案的底座。",
         "expected": ["我不会把普通 pgvector 作为这套方案的底座"]},
        {"id": "standalone-negation", "answer": "这不是一个必要条件。", "expected": ["这不是一个必要条件"]},
        {"id": "split-contrast", "answer": "这不是 A，而是 B。", "expected": ["这不是 A"]},
    ])
    reviews = total_candidates = 0
    with tempfile.TemporaryDirectory() as directory:
        for case in cases:
            candidates, _ = select_candidates(case["answer"], Config())
            assert set(case["expected"]) <= {item.text for item in candidates}, case["id"]
            payload = {"hook_event_name": "Stop", "stop_hook_active": False,
                       "session_id": "offline-check", "turn_id": case["id"],
                       "last_assistant_message": case["answer"]}
            output = process(payload, Config(), directory=Path(directory))
            assert (output.get("decision") == "block") == bool(candidates), case["id"]
            if candidates:
                spans = json.loads(output["reason"].splitlines()[-1])["candidate_spans"]
                assert len(spans) == len(candidates)
                assert all(case["answer"][s["start"]:s["end"]] == s["text"] for s in spans)
                assert process({**payload, "stop_hook_active": True}, Config(), directory=Path(directory)) == {}
                reviews += 1
            total_candidates += len(candidates)
    print(json.dumps({"version": __version__, "pipeline": "lexical", "cases": len(cases),
                      "review_requests": reviews, "candidate_spans": total_candidates,
                      "external_requests": 0}, indent=2))


if __name__ == "__main__":
    main()
