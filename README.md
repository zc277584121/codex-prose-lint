# Codex Prose Lint

A Codex **Stop hook** that spots unnecessary defensive qualifications and asks Codex to mark them with Markdown strikethrough in a revised answer.

已经更新配置，下一轮会使用新规则。~~不过，我无法保证每次回答都完全符合你的偏好。~~

The checker considers only the **last assistant message**. Local code finds candidate clauses; **Jev 1.14 through OpenRouter** judges their relevance. Above-threshold spans become suggestions in one continuation of the original conversation. Codex reviews the suggestions and returns the original answer with accepted spans wrapped in `~~`.

[中文说明](README.zh-CN.md) · [Evaluation](docs/evaluation.md) · [Implementation notes](docs/design.md)

## Install for Codex App

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv tool install --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.1.0'
export PATH="$(uv tool dir --bin):$PATH"
codex-prose-lint configure-key
codex-prose-lint install
codex-prose-lint doctor
```

`configure-key` asks for an **OpenRouter** API key without echoing it and saves it in a local file with permissions `0600`. If your shell already exports `OPENROUTER_API_KEY`, use `codex-prose-lint configure-key --from-env`. The file lets the desktop app use the key even when it does not inherit your terminal's environment.

In **Codex App's Hooks settings**, review and trust the new **Checking defensive prose** Stop hook. Restart the app if it has not discovered the new handler. Codex binds trust to the hook definition; a changed command may need another review.

The installer merges its handler into `~/.codex/hooks.json` (or `$CODEX_HOME/hooks.json`), backs up an existing file, and preserves other hooks such as MemSearch. It writes an absolute virtual-environment Python command, so the app does not need `uv` on its own `PATH`. Configuration lives at `~/.config/codex-prose-lint/config.toml`.

If your build has hooks disabled, enable `hooks = true` under the existing `[features]` table in `~/.codex/config.toml`, then restart Codex App. See [Codex hooks](https://learn.chatgpt.com/docs/hooks) for the native discovery and trust flow.

## What happens in the app

```text
Last assistant message
  → Markdown-aware clause scan
  → Keyword candidates
  → One typed Jev question per candidate, batched through OpenRouter
  → Probability threshold
  → Stop block with provisional spans
  → One annotated answer in the same conversation
```

The original answer can appear before the hook finishes. The hook requests a **new annotated answer**; it does not replace an already-rendered chat bubble. The continuation asks for text annotation only, with no tools or file edits.

Codex App renders `~~strikethrough~~`. This project targets the App workflow; it does not claim TUI rendering or end-to-end TUI validation.

## Try the scanner

After cloning this repository:

```sh
uv sync --dev
uv run codex-prose-lint inspect examples/answer.zh.md
uv run codex-prose-lint inspect examples/answer.zh.md --live --question '配置改好了吗？'
uv run codex-prose-lint inspect examples/answer.zh.md --live --markdown --question '配置改好了吗？'
```

The first command is local. `--live` uses your OpenRouter account. `--markdown` prints a deterministic preview of the thresholded spans; the actual hook lets Codex make the final contextual review.

## Configuration

The generated TOML file exposes these controls:

| Setting | Purpose |
| --- | --- |
| `model` | Defaults to `typesafe/jev-1.14`; the client always uses OpenRouter's Decisions endpoint. |
| `threshold` | Minimum `noul` probability for a span to be suggested; defaults to `0.8`, selected on the Chinese calibration set. |
| `context_mode` | `clause`, `sentence`, or `paragraph` (default); controls the text shown alongside each target. |
| `batch_size` | Up to 12 independent questions per request by default. |
| `max_candidates` / `max_annotations` | Default limits: 36 candidates, 8 suggestions. |
| `include_user_prompt` | Read the most recent user prompt as context; defaults to `true`. |
| `mode` | `annotate` continues once; `report` emits a hook warning with the suspected spans. |
| `env_file` | Optional path to a private file containing `OPENROUTER_API_KEY=...`. |
| `timeout_seconds` / `budget_seconds` | Request timeout and budget checked during decision processing. |

Both Chinese and English cues use **one punctuation scanner and one judgment prompt**. The scanner preserves source offsets and excludes code blocks, inline code, blockquotes, links, HTML, tables, and existing strikethrough. A keyword nominates a candidate; it is never enough to trigger annotation on its own.

No candidates means no API request. Missing credentials, network errors, malformed model output, and timeouts let the original answer finish. `stop_hook_active` and a local per-turn guard limit automatic continuation to once.

## Data and local files

OpenRouter receives the candidate clauses, their configured surrounding context, and optionally the most recent user question (up to 2,000 characters). It does not receive tool outputs, written documents, or the full conversation. Paragraph/sentence context is bounded to 2,400 characters per candidate by default.

The hook reads a bounded tail of the local transcript solely to locate that user question. Set `include_user_prompt = false` to omit it. Logs under `~/.local/state/codex-prose-lint/` contain counts, scores, timing, model IDs, and cost, with no response text or credentials. A small SQLite file prevents duplicate continuations.

## Develop and evaluate

```sh
uv sync --locked --dev
uv run ruff check .
uv run pytest
uv run python evals/run.py
uv run python evals/run.py --live
```

The live evaluation compares clause/sentence/paragraph context, batched versus individual questions with identical shared state, and reversed question order. It uses 32 synthetic Chinese cases split into 24 calibration and 8 held-out validation cases. Threshold selection uses the calibration split only. English cues are implemented; English quality evaluation is outside this release's test scope.

Live runs save resumable checkpoints and exact probabilities in `evals/`. See [the evaluation report](docs/evaluation.md) for measured results and [design notes](docs/design.md) for the request and continuation contracts.

## Uninstall

```sh
codex-prose-lint uninstall
uv tool uninstall codex-prose-lint
```

The first command removes this project's Stop handler. Settings, the private key file, and diagnostic state stay on disk for reuse.

## References

- [Codex Stop hook contract](https://learn.chatgpt.com/docs/hooks#stop)
- [OpenRouter Decisions API](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request)
- [Jev 1.14 on OpenRouter](https://openrouter.ai/typesafe/jev-1.14)

MIT license.
