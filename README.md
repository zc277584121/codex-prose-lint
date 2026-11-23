# Codex Prose Lint

A local Stop hook that finds possible defensive or unnecessarily negative phrasing in the last assistant message, then asks Codex to review it in the same conversation.

已经更新配置，下一轮会使用新规则。~~不过，我无法保证每次回答都完全符合你的偏好。~~

The scanner sends keyword candidates directly to Codex. Codex can strike redundant defensive text, lightly rephrase useful information into direct language, or retain an appropriate negative statement. The hook uses local text processing and requires no external decision model or API key.

[中文说明](README.zh-CN.md) · [Design](docs/design.md) · [Release notes](CHANGELOG.md)

## Install for Codex App

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

~~~sh
uv tool install --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.2.0'
export PATH="$(uv tool dir --bin):$PATH"
codex-prose-lint install
codex-prose-lint doctor
~~~

Review and trust **Checking defensive prose** in Codex App's Hooks settings. Restart the app if it has not discovered the new handler. If hooks are disabled in your build, enable hooks = true under the existing [features] table in ~/.codex/config.toml.

The installer merges its Stop handler into ~/.codex/hooks.json, preserves existing hooks, and saves a backup. It registers an absolute Python path, so the app can invoke the installed tool outside a terminal. Settings live in ~/.config/codex-prose-lint/config.toml; CODEX_HOME and XDG directories are supported.

## Upgrade

~~~sh
uv tool install --force --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.2.0'
export PATH="$(uv tool dir --bin):$PATH"
codex-prose-lint --version
codex-prose-lint doctor
~~~

The existing hook continues to use the same uv tool environment path. Doctor reports the running version, Python path, module path, and registered hook commands.

Old model, threshold, credential, timeout, context-mode, and annotation-cap settings are accepted and ignored. Doctor lists those legacy fields. Previous private key files stay on disk and are unused by this release. The old configure-key command and inspect --live/--question options have been removed.

## Review flow

~~~text
Last assistant message
  → Protect Markdown regions
  → Split clauses and match cues
  → Stop block with candidate text, offsets, and matched words
  → Codex reviews the candidates in the original conversation
  → One complete answer with strikethrough and/or small local edits
~~~

The review prompt explicitly treats lexical matches as provisional. Redundant disclaimers get strikethrough; useful information expressed through defensive negation can receive a minimal affirmative rewrite. Facts, recommendations, certainty, and unaffected text should remain intact. Appropriate factual negations, real failures, technical constraints, quotations, and examples can be retained.

Every eligible candidate goes to review in source order, up to the configured limit. The original answer may already have streamed before the revised answer appears. If all matches are appropriate, Codex is asked to return the original answer unchanged. Each turn can continue once.

## Scanner and settings

Chinese and English share one punctuation scanner and cue matcher. Chinese cues include 不会, 避免, 没有, 并未, 尚未, 不要, 不应, 不足以, 仅作, 只涉及, and common variants. Code blocks, inline code, blockquotes, links, HTML, tables, and existing strikethrough are protected.

| Setting | Default | Purpose |
| --- | ---: | --- |
| max_candidates | 36 | Maximum candidates sent to review, in source order. |
| max_message_chars | 30000 | Maximum last-message length. |
| max_clause_chars | 800 | Maximum length of an individual candidate. |
| max_context_chars | 2400 | Context length for local inspection output. |
| mode | annotate | Continue for review; report emits a candidate notice instead. |

The hook only scans last_assistant_message. It does not read a transcript or invoke tools to inspect generated files. The existing Codex conversation supplies context for review. The stop_hook_active field and a local per-turn guard prevent repeated continuations.

## Inspect locally

~~~sh
codex-prose-lint inspect examples/answer.zh.md
codex-prose-lint inspect examples/answer.zh.md --markdown
~~~

The first command shows candidate text, offsets, and matched cues. The Markdown preview strikes **every lexical candidate** to show its location; contextual acceptance and small rewrites happen in Codex's review.

Metadata logs in ~/.local/state/codex-prose-lint/events.jsonl record package version, pipeline, counts, and scan time. They contain no answer text. The same directory holds the duplicate-continuation guard.

## Develop and verify

~~~sh
uv sync --locked --dev
uv run ruff check .
uv run pytest
uv run python evals/check_local.py
uv build
~~~

The offline check verifies candidate coverage and review payloads for 56 Chinese examples, including the architecture and pgvector negations. Unit tests cover no-network behavior, legacy configuration, source offsets, Markdown protection, installation, and continuation guards. Codex App strikethrough rendering has been confirmed in conversation; TUI behavior and English quality were left outside the evaluation.

The earlier [model experiment](docs/evaluation.md) and [v0.1.1 evaluation](docs/evaluation-v0.1.1.md) remain historical records. Their runnable code is available at the corresponding version tags.

## Uninstall

~~~sh
codex-prose-lint uninstall
uv tool uninstall codex-prose-lint
~~~

Configuration and diagnostic state stay on disk for reuse.

[Codex Stop hook contract](https://learn.chatgpt.com/docs/hooks#stop) · MIT license.
