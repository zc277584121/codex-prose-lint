# v0.1.1 Chinese vocabulary check

The expanded scanner was checked on 2026-11-23 using the release defaults: paragraph context, batched Jev 1.14 questions through OpenRouter, and a 0.8 threshold. The judgment rubric remains at prompt hash `3b4bbefc50028f2a`.

The run combines the original 32 Chinese examples with [22 additional examples](../evals/cases.expanded.zh.jsonl). The additions pair unnecessary qualifications with user requests that make similar wording relevant, covering `不会`, `避免`, `没有`, `并未`, `尚未`, `请勿`, `仅涉及`, `不足以`, `不作任何保证`, and `有待进一步验证`. Two examples check protected code and existing strikethrough.

| Dataset | Answers | Candidate clauses | Unnecessary clauses flagged | Useful clauses flagged | Useful clauses retained |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original examples with expanded scanner | 32 | 44 | 25/27 | 0 | 17 |
| Added vocabulary examples | 22 | 23 | 12/12 | 0 | 11 |

The two missed original clauses remain the disk-access qualifications described in the [initial evaluation](evaluation.md). The added examples were labeled before this run; the threshold and prompt were kept fixed. These counts describe a small synthetic regression set, before Codex's final review.

There were **48 API requests**, with **0.672 seconds** median judgment time per answer that made a request and **$0.00146286** total reported cost. The resolved model was `typesafe/jev-1.14-20261014`. [Raw results](../evals/results.v0.1.1.zh.json) include probabilities, timing, costs, and hashes of the scanner and datasets.

Reproduce from the v0.1.1 checkout:

```sh
uv sync --locked --dev
uv run python evals/check_release.py
uv run python evals/check_release.py --live --output evals/local/v0.1.1.zh.json
```

The command without `--live` validates local candidate coverage. The live command uses the configured OpenRouter key and runs the current default decision settings.
