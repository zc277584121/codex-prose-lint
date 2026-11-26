# Project guidance

This is a Python package managed with uv and pyproject.toml.

The runtime reads one Codex Stop hook payload from stdin and writes exactly one JSON object to stdout. Diagnostics go to stderr. Parsing failures allow the original turn to finish. Logs contain version and counts, not user text.

Keep sentence segmentation language-agnostic. Chinese and English cues share one scanner and one review prompt. Protect Markdown code, blockquotes, links, HTML, and existing strikethrough spans. Preserve original character offsets.

The review prompt must place closing strikethrough delimiters before all trailing punctuation, including sequences of punctuation and closing quotes/brackets. Preserve punctuation and whitespace in their original order outside the annotation.

The hook performs local lexical screening only. It must not call an external decision service, load API credentials, or read the transcript. Send candidate text, offsets, and matched cues as advisory references in one Stop continuation. Ask Codex to review the entire previous answer and generously strike every defensive or defensive-leaning prose span, including spans outside the suggestions. The final annotations may be more or fewer than the candidates. Only insert strikethrough delimiters; preserve all original wording, punctuation, whitespace, and formatting. Do not request rewrites, tool calls, or file edits.

Use uv run pytest and uv run ruff check . for local checks. Use uv run python evals/check_local.py to verify Chinese candidate coverage and the review payload. Historical model experiments belong to their version tags; current checks run offline.

Installation merges the owned Stop handler into hooks.json and preserves unrelated hooks. Never fabricate hook trust records or disable another hook. Version upgrades keep the registered command stable when the tool environment path stays the same. Logs and doctor output must identify the running package version.
