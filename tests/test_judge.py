import json
from dataclasses import replace

import httpx
import pytest

from codex_prose_lint.config import Config
from codex_prose_lint.judge import judge, parse_scores
from codex_prose_lint.scan import scan


@pytest.mark.parametrize("answer", [None, {}, {"type": "noul", "noul": True},
    {"type": "noul", "noul": -0.1}, {"type": "noul", "noul": 1.1},
    {"type": "noul", "noul": float("nan")}, {"type": "noul", "noul": "0.9"},
    {"type": "choice", "noul": 0.9}, {"type": "noul", "refusal": "refused"}])
def test_invalid_probabilities_are_rejected(answer):
    with pytest.raises(ValueError):
        parse_scores({"answers": {"c000": answer}}, ["c000"])


def test_same_state_single_questions_matches_batch_contract():
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert str(request.url) == "https://openrouter.ai/api/alpha/decisions"
        return httpx.Response(200, json={"model": "typesafe/jev-1.14-test", "answers": {
            key: {"type": "noul", "noul": 0.91} for key in body["questions"]
        }, "usage": {"cost": 0.0001}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        items = scan("无法保证。需要注意。")
        batch = judge(items, "你更新了吗？", Config(), "test-key", client=client)
        single = judge(items, "你更新了吗？", Config(), "test-key", client=client, question_mode="single")
    assert batch.scores == single.scores
    assert batch.requests == 1 and single.requests == 2
    assert requests[0]["state"] == requests[1]["state"] == requests[2]["state"]


def test_http_failure_does_not_echo_body_or_key():
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(401, text="secret"))) as client:
        with pytest.raises(ValueError, match="^OpenRouter returned HTTP 401$"):
            judge(scan("无法保证。"), "", Config(), "secret", client=client)


def test_batch_size_limits_questions():
    sizes = []

    def handler(request):
        body = json.loads(request.content)
        sizes.append(len(body["questions"]))
        return httpx.Response(200, json={"answers": {key: {"type": "noul", "noul": 0.1} for key in body["questions"]}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        judge(scan("无法保证。不能据此判断。需要注意。"), "", replace(Config(), batch_size=2), "key", client=client)
    assert sizes == [2, 1]
