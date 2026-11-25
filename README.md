# Codex Prose Lint

A local Stop hook that finds possible defensive or unnecessarily negative phrasing in the last assistant message, then asks Codex to review it in the same conversation.

已经更新配置，下一轮会使用新规则。~~不过，我无法保证每次回答都完全符合你的偏好。~~

The scanner sends keyword matches as reference suggestions. Codex reviews the entire previous answer and generously adds strikethrough to defensive or defensive-leaning prose, including passages outside the suggestions. The output preserves the original text and only inserts strikethrough delimiters. The hook uses local text processing and requires no external decision model or API key.

[中文说明](README.zh-CN.md) · [Design](docs/design.md) · [Release notes](CHANGELOG.md)

## Install for Codex App

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

~~~sh
uv tool install --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.2.1'
export PATH="$(uv tool dir --bin):$PATH"
codex-prose-lint install
codex-prose-lint doctor
~~~

Review and trust **Checking defensive prose** in Codex App's Hooks settings. Restart the app if it has not discovered the new handler. If hooks are disabled in your build, enable hooks = true under the existing [features] table in ~/.codex/config.toml.

The installer merges its Stop handler into ~/.codex/hooks.json, preserves existing hooks, and saves a backup. It registers an absolute Python path, so the app can invoke the installed tool outside a terminal. Settings live in ~/.config/codex-prose-lint/config.toml; CODEX_HOME and XDG directories are supported.

## Upgrade

~~~sh
uv tool install --force --python 3.12 'git+https://github.com/zc277584121/codex-prose-lint@v0.2.1'
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
  → Codex reviews the entire answer using the suggestions as references
  → One complete answer with strikethrough added to defensive prose
~~~

The review prompt treats keyword matches as advisory: suggestions may contain false positives and miss other defensive wording. It directs Codex to mark every defensive or defensive-leaning prose span, including mild or borderline cases. The final annotations can be more or fewer than the suggestions. A sentence can carry useful information and still have defensive framing worth marking; its original words remain visible beneath the strikethrough.

An eligible keyword match triggers whole-answer review. Reference suggestions are sent in source order up to the configured limit; that limit does not cap the number of final annotations. The prompt requires only insertion of strikethrough delimiters, preserving every original character and the existing formatting. Ordinary direct factual answers and quoted examples are retained when they contain no defensive framing. The original answer may already have streamed before the annotated answer appears, and each turn can continue once.

## Scanner and settings

Chinese and English share one punctuation scanner and cue matcher. Chinese cues include 不是, 不会, 避免, 没有, 并未, 尚未, 不要, 不应, 不足以, 仅作, 只涉及, and common variants. Code blocks, inline code, blockquotes, links, HTML, tables, and existing strikethrough are protected during scanning.

| Setting | Default | Purpose |
| --- | ---: | --- |
| max_candidates | 36 | Maximum reference suggestions sent, in source order. |
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

The first command shows candidate text, offsets, and matched cues. The Markdown preview strikes **every lexical candidate** to show its location; Codex chooses the final strikethrough spans by reviewing the entire answer.

Metadata logs in ~/.local/state/codex-prose-lint/events.jsonl record package version, pipeline, counts, and scan time. They contain no answer text. The same directory holds the duplicate-continuation guard.

## Develop and verify

~~~sh
uv sync --locked --dev
uv run ruff check .
uv run pytest
uv run python evals/check_local.py
uv build
~~~

The offline check verifies candidate coverage and review payloads for 58 Chinese examples, including standalone 不是, split contrast clauses, and the architecture/pgvector negations. Unit tests cover strikethrough-only instructions, whole-answer review beyond reference limits, no-network behavior, legacy configuration, source offsets, Markdown protection, installation, and continuation guards. Codex App strikethrough rendering has been confirmed in conversation; TUI behavior and English quality were left outside the evaluation.

The earlier [model experiment](docs/evaluation.md) and [v0.1.1 evaluation](docs/evaluation-v0.1.1.md) remain historical records. Their runnable code is available at the corresponding version tags.

## Uninstall

~~~sh
codex-prose-lint uninstall
uv tool uninstall codex-prose-lint
~~~

Configuration and diagnostic state stay on disk for reuse.

[Codex Stop hook contract](https://learn.chatgpt.com/docs/hooks#stop) · MIT license.
