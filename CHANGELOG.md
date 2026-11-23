# Changelog

## v0.1.1 — 2026-11-23

Expanded Chinese candidate detection for negation, unverified work, caution, limited scope, and non-guarantees. New cues include `不会`, `避免`, `没有`, `并未`, `尚未`, `以免`, `不要`, `不应`, `不足以`, `仅作`, and `只涉及`, with common variants such as `不作任何保证` and `有待进一步验证`.

Added source-offset and Markdown-protection regression checks, 22 Chinese judgment examples, and a reproducible release evaluation. The full live check covers 54 Chinese answers at the existing 0.8 threshold. See the [evaluation results](docs/evaluation-v0.1.1.md).

## v0.1.0 — 2026-11-23

Initial Stop hook release: Markdown-aware candidate scanning, batched Jev 1.14 decisions through OpenRouter, one strikethrough-review continuation, installer, credential configuration, and Chinese context/grouping evaluation.
