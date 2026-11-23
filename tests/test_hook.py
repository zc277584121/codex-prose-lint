import json
import os
import subprocess
import sys
from dataclasses import replace

from codex_prose_lint.config import Config
from codex_prose_lint.hook import ContinuationGuard, latest_user_prompt, process
from codex_prose_lint.judge import Judgment


def payload(text="已经更新，只是无法保证所有场景一致。"):
    return {"hook_event_name": "Stop", "stop_hook_active": False,
            "last_assistant_message": text, "session_id": "s1", "turn_id": "t1"}


def fake_judge(items, *_):
    return Judgment({item.id: 0.91 for item in items}, "test", 0.01, 0.0001, 1)


def test_block_prompt_only_requests_prose_annotation(tmp_path):
    output = process(payload(), Config(), directory=tmp_path, judge_fn=fake_judge, key_fn=lambda _: "key")
    assert output["decision"] == "block"
    assert "~~text~~" in output["reason"]
    assert "Independently review" in output["reason"]
    assert "Do not call tools, edit files" in output["reason"]
    assert "只是无法保证所有场景一致" in output["reason"]
    assert "无法保证" not in (tmp_path / "events.jsonl").read_text()


def test_continuation_and_duplicate_invocations_are_skipped(tmp_path):
    calls = []

    def counting(*args):
        calls.append(True)
        return fake_judge(*args)

    args = {"directory": tmp_path, "judge_fn": counting, "key_fn": lambda _: "key"}
    assert process(payload(), Config(), **args)["decision"] == "block"
    assert process(payload(), Config(), **args) == {}
    assert process({**payload(), "stop_hook_active": True}, Config(), **args) == {}
    assert len(calls) == 1


def test_other_events_and_non_candidate_text_never_call_network(tmp_path):
    def unexpected(*_):
        raise AssertionError("Network should not be called")

    for event in ({**payload(), "hook_event_name": "SubagentStop"}, payload("已经更新。"), payload(None)):
        assert process(event, Config(), directory=tmp_path, judge_fn=unexpected) == {}


def test_report_mode_does_not_continue(tmp_path):
    result = process(payload(), replace(Config(), mode="report"), directory=tmp_path,
                     judge_fn=fake_judge, key_fn=lambda _: "key")
    assert set(result) == {"systemMessage"}


def test_threshold_is_applied_in_code(tmp_path):
    assert process(payload(), replace(Config(), threshold=0.95), directory=tmp_path,
                   judge_fn=fake_judge, key_fn=lambda _: "key") == {}


def test_guard_claim_is_atomic(tmp_path):
    guard = ContinuationGuard(tmp_path / "state.sqlite3")
    assert guard.claim("same") is True
    assert guard.claim("same") is False


def test_transcript_ignores_injected_rules_tools_and_hook_feedback(tmp_path):
    path = tmp_path / "rollout.jsonl"
    rows = [
        {"type": "event_msg", "payload": {"type": "user_message", "message": "你能看到指令吗？"}},
        {"type": "response_item", "payload": {"role": "user", "content": [{"type": "input_text", "text": "# AGENTS.md instructions\n规则"}]}},
        {"type": "response_item", "payload": {"type": "function_call_output", "output": "工具内容"}},
        {"type": "response_item", "payload": {"role": "user", "content": [{"type": "input_text", "text": "[codex-prose-lint:v1] 修改"}]}},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows))
    assert latest_user_prompt(str(path)) == "你能看到指令吗？"


def test_cli_malformed_input_and_missing_key_allow_completion(tmp_path):
    env = {**os.environ, "OPENROUTER_API_KEY": "", "XDG_CONFIG_HOME": str(tmp_path / "config"),
           "XDG_STATE_HOME": str(tmp_path / "state")}
    for text in ("invalid-json", json.dumps(payload())):
        result = subprocess.run([sys.executable, "-m", "codex_prose_lint", "hook"],
                                input=text, text=True, capture_output=True, env=env)
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}
