import json
import os
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from codex_prose_lint import __version__
from codex_prose_lint.config import Config, load_config
from codex_prose_lint.hook import ContinuationGuard, process


def payload(text="已经更新，只是无法保证所有场景一致。"):
    return {"hook_event_name": "Stop", "stop_hook_active": False,
            "last_assistant_message": text, "session_id": "s1", "turn_id": "t1"}


def spans(output):
    return json.loads(output["reason"].splitlines()[-1])["candidate_spans"]


def test_reported_negations_reach_review_without_scoring(tmp_path):
    message = "不能一起归入旧架构。我不会把普通 pgvector 作为这套方案的底座。"
    output = process(payload(message), Config(), directory=tmp_path)
    assert output["decision"] == "block"
    assert [span["text"] for span in spans(output)] == [
        "不能一起归入旧架构", "我不会把普通 pgvector 作为这套方案的底座",
    ]
    for span in spans(output):
        assert message[span["start"]:span["end"]] == span["text"]
        assert span["cues"]
        assert "probability" not in span
    log = (tmp_path / "events.jsonl").read_text()
    assert "pgvector" not in log
    event = json.loads(log)
    assert event["version"] == __version__
    assert event["pipeline"] == "lexical"
    assert event["candidates"] == 2
    assert "scores" not in event


def test_review_contract_allows_strikethrough_and_minimal_rephrasing(tmp_path):
    reason = process(payload(), Config(), directory=tmp_path)["reason"]
    assert "lexical matches, not verified judgments" in reason
    assert "~~text~~" in reason
    assert "small local edit" in reason
    assert "Useful information is not by itself a reason" in reason
    assert "necessary factual negations" in reason
    assert "Do not call tools, edit files" in reason
    assert "complete previous answer" in reason


def test_continuation_and_duplicate_invocations_are_skipped(tmp_path):
    assert process(payload(), Config(), directory=tmp_path)["decision"] == "block"
    assert process(payload(), Config(), directory=tmp_path) == {}
    assert process({**payload(), "stop_hook_active": True}, Config(), directory=tmp_path) == {}
    assert len((tmp_path / "events.jsonl").read_text().splitlines()) == 1


@pytest.mark.parametrize("event", [
    {**payload(), "hook_event_name": "SubagentStop"},
    {**payload(), "hook_event_name": "PostToolUse"},
    {**payload(), "stop_hook_active": True},
    payload("已经更新。"), payload(chr(96) + "不会自动处理" + chr(96)), payload(None),
])
def test_out_of_scope_or_empty_candidates_allow_completion(tmp_path, event):
    assert process(event, Config(), directory=tmp_path) == {}


def test_report_mode_does_not_continue(tmp_path):
    assert set(process(payload(), replace(Config(), mode="report"), directory=tmp_path)) == {"systemMessage"}


def test_legacy_threshold_and_annotation_cap_do_not_filter_candidates(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text("threshold = 1.0\nmax_annotations = 1\nmax_candidates = 12\n")
    message = "。".join(f"不会自动处理第{i}项" for i in range(15)) + "。"
    output = process(payload(message), load_config(path), directory=tmp_path)
    assert len(spans(output)) == 12
    assert spans(output)[-1]["text"] == "不会自动处理第11项"
    assert json.loads((tmp_path / "events.jsonl").read_text())["omitted_candidates"] == 3


def test_no_network_or_credential_or_transcript_access(tmp_path, monkeypatch):
    private = tmp_path / "private.env"
    transcript = tmp_path / "transcript.jsonl"
    path = tmp_path / "settings.toml"
    path.write_text(f'env_file = "{private}"\ninclude_user_prompt = true\nmodel = "unused"\n')
    original_open = Path.open

    def guarded_open(self, *args, **kwargs):
        if self in {private, transcript}:
            raise AssertionError("Unexpected private file access")
        return original_open(self, *args, **kwargs)

    def unexpected_network(*args, **kwargs):
        raise AssertionError("Unexpected network access")

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(socket, "create_connection", unexpected_network)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected_network)
    monkeypatch.setattr(socket.socket, "connect", unexpected_network)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    event = {**payload(), "transcript_path": str(transcript)}
    assert process(event, load_config(path), directory=tmp_path)["decision"] == "block"


def test_guard_claim_is_atomic_across_concurrent_calls(tmp_path):
    guard = ContinuationGuard(tmp_path / "state.sqlite3")
    with ThreadPoolExecutor(max_workers=6) as pool:
        claims = list(pool.map(lambda _: guard.claim("same"), range(6)))
    assert sum(claims) == 1


def test_length_limits_are_logged(tmp_path):
    assert process(payload("不会" * 20), replace(Config(), max_message_chars=20), directory=tmp_path) == {}
    assert process(payload("不会" * 10), replace(Config(), max_clause_chars=10), directory=tmp_path) == {}
    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert events[0]["status"] == "message_too_long"
    assert events[1]["omitted_candidates"] == 1


def test_cli_invalid_payload_fails_open_and_missing_key_still_reviews(tmp_path):
    env = {**os.environ, "OPENROUTER_API_KEY": "", "XDG_CONFIG_HOME": str(tmp_path / "config"),
           "XDG_STATE_HOME": str(tmp_path / "state")}
    for value, expected in (("invalid-json", None), ("[]", None), (json.dumps(payload()), "block")):
        result = subprocess.run([sys.executable, "-m", "codex_prose_lint", "hook"],
                                input=value, text=True, capture_output=True, env=env)
        assert result.returncode == 0
        assert json.loads(result.stdout).get("decision") == expected
