# Changelog

## v0.2.2 — 2026-11-26

The review prompt places closing strikethrough delimiters before trailing punctuation to address the reported App rendering issue. The rule covers all Chinese and English punctuation, including consecutive marks, quotation marks, and brackets, while preserving the original text and punctuation order.

Added a hook-prompt regression check and formatting examples in both READMEs.

## v0.2.1 — 2026-11-25

Added standalone 不是 as a candidate cue, including contrast clauses separated by punctuation.

The review now requires strikethrough only, preserving all original characters and formatting. Keyword candidates are advisory references for reviewing the entire answer; the final annotations may be more or fewer than the suggestions. The prompt explicitly asks for generous coverage of defensive and defensive-leaning wording, including mild or borderline cases outside the reference list.

Added regression checks for independent negation, the strikethrough-only contract, and whole-answer review beyond candidate limits. Offline coverage includes 58 Chinese examples.

## v0.2.0 — 2026-11-23

Replaced external model scoring with local lexical screening followed directly by one Codex review. All selected candidates reach the review prompt in source order. The prompt asks for strikethrough on redundant defensive prose and small affirmative rewrites when useful information should be retained.

Removed the decision-service client, API-key setup, transcript reads, scoring thresholds, and HTTP dependency. Existing model-related configuration fields are accepted and ignored during upgrades. Historical decision experiments remain available at the v0.1.x tags.

Added package version and pipeline details to metadata logs and doctor output, plus a --version command. Offline verification covers the two reported architecture/pgvector sentences, legacy configuration, zero network/credential access, source offsets, and one-continuation behavior.

## v0.1.1 — 2026-11-23

Expanded Chinese candidate detection for negation, unverified work, caution, limited scope, and non-guarantees. New cues include `不会`, `避免`, `没有`, `并未`, `尚未`, `以免`, `不要`, `不应`, `不足以`, `仅作`, and `只涉及`, with common variants such as `不作任何保证` and `有待进一步验证`.

Added source-offset and Markdown-protection regression checks, 22 Chinese judgment examples, and a reproducible release evaluation. The full live check covers 54 Chinese answers at the existing 0.8 threshold. See the [evaluation results](docs/evaluation-v0.1.1.md).

## v0.1.0 — 2026-11-23

Initial Stop hook release: Markdown-aware candidate scanning, batched Jev 1.14 decisions through OpenRouter, one strikethrough-review continuation, installer, credential configuration, and Chinese context/grouping evaluation.
