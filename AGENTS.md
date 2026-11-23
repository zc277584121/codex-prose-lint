# Project guidance

This is a Python package managed with uv and pyproject.toml.

The runtime reads one Codex Stop hook payload from stdin and writes exactly one JSON object to stdout. Diagnostics go to stderr. Network and parsing failures must allow the original turn to finish. Never log API keys or full user messages by default.

Keep sentence segmentation language-agnostic. Chinese and English cues share one scanner and one decision prompt. Protect Markdown code, quotes, links, HTML, and existing strikethrough spans. Preserve original character offsets.

Call decision models only through OpenRouter's Decisions API. Use typed `noul` probabilities, validate them, and apply the configured threshold in code. A Stop continuation only asks the original conversation to review flagged spans and add strikethrough; it must not request file edits or tool calls.

Use `uv run pytest` and `uv run ruff check .` for local checks. Live evaluation is explicitly opt-in and uses synthetic Chinese fixtures. Record the model, prompt hash, context mode, request grouping, threshold, latency, and cost. Do not claim English quality or TUI validation without testing them.

Installation merges the owned Stop handler into hooks.json and preserves unrelated hooks. Never fabricate hook trust records or disable another hook.
