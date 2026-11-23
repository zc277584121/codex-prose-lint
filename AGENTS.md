# Project guidance

This is a Python package managed with uv and pyproject.toml.

The runtime reads one Codex Stop hook payload from stdin and writes exactly one JSON object to stdout. Diagnostics go to stderr. Parsing failures allow the original turn to finish. Logs contain version and counts, not user text.

Keep sentence segmentation language-agnostic. Chinese and English cues share one scanner and one review prompt. Protect Markdown code, blockquotes, links, HTML, and existing strikethrough spans. Preserve original character offsets.

The hook performs local lexical screening only. It must not call an external decision service, load API credentials, or read the transcript. Send candidate text, offsets, and matched cues to the original Codex conversation in one Stop continuation. Ask Codex to strike unnecessary defensive prose and minimally rephrase useful information expressed through defensive negation. Preserve factual meaning and leave appropriate negatives intact. Do not request tool calls or file edits.

Use uv run pytest and uv run ruff check . for local checks. Use uv run python evals/check_local.py to verify Chinese candidate coverage and the review payload. Historical model experiments belong to their version tags; current checks run offline.

Installation merges the owned Stop handler into hooks.json and preserves unrelated hooks. Never fabricate hook trust records or disable another hook. Version upgrades keep the registered command stable when the tool environment path stays the same. Logs and doctor output must identify the running package version.
