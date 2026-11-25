# Design

## Scope and lifecycle

The handler accepts a Stop payload with stop_hook_active set to false and a non-empty last_assistant_message. It performs local lexical screening and sends up to 36 candidates directly to the original Codex conversation in a single block response.

Each candidate includes exact text, a zero-based Unicode [start, end) offset, and matched cues. There are no probability scores or threshold gates. The review prompt presents candidates as advisory references that can over-match or miss defensive phrasing. Codex reviews the entire previous answer and generously strikes every defensive or defensive-leaning prose span, including mild or borderline cases and text outside the candidate list.

The full answer is returned in its original language with only strikethrough delimiters inserted. All original characters, punctuation, whitespace, and formatting are preserved. The final annotation count can be greater or smaller than the candidate count. Useful information does not exempt defensive framing from annotation, since the original text remains visible. Ordinary direct factual answers and quoted examples are judged in context. The prompt requests no rewriting, tools, or file edits; an answer without defensive phrasing is returned unchanged.

The stop_hook_active field skips the continuation. A SQLite unique key on session/turn ensures repeated or concurrent deliveries produce at most one block. Metadata logs distinguish review_requested, reported, no_candidates, message_too_long, and error outcomes; they do not represent Codex's later review verdict.

## Scanner

The shared Chinese/English scanner uses markdown-it-py for block protection and offset-preserving masks for inline code, links, formatting delimiters, and existing strikethrough. Punctuation splits candidate clauses while preserving numeric punctuation and common abbreviations.

Candidates remain in source order. Messages above max_message_chars are skipped; clauses above max_clause_chars are omitted; max_candidates bounds the reference list, not Codex's whole-answer review. An eligible candidate is required to trigger review. The omitted count includes both clause-length and count exclusions. Context excerpts remain available for local inspect output.

## Local execution

The package has no HTTP client or external decision API integration. It reads the hook payload, local configuration, and continuation state; it does not load API keys or read the transcript. Codex already has the conversation needed for contextual review.

The CLI emits one JSON object on stdout for hook runs. Malformed inputs and runtime failures allow the original turn to finish. Error logs contain exception classes rather than arbitrary error bodies.

## Installation and migration

The installer uses atomic replacement, backs up hooks.json, and merges one identifiable handler while preserving unrelated hooks. Trust is managed through Codex App. The hook uses the uv tool environment's absolute Python path.

Pre-0.2 model-related settings are accepted and ignored. Active settings continue to apply, and unknown fields still produce a configuration error. The old max_annotations setting no longer limits candidate review. API-key files are left untouched and unused.

Doctor exposes the executing version, interpreter, module location, effective settings, ignored legacy fields, and registered commands. Every new metadata log record includes version and pipeline. This makes running-package differences visible without inspecting message text.

## Verification

Tests exercise the user-reported negations, standalone 不是, contrast clauses split by punctuation, candidate forwarding, strikethrough-only instructions, whole-answer review beyond the reference limit, network and private-file access traps, legacy configuration, concurrent duplicate suppression, and invalid input handling. The offline fixture check covers 58 Chinese answers and validates exact review offsets.

The model-based v0.1.x experiments remain historical data. Their reproduction scripts and dependency sets are available at their release tags. Codex App rendering was confirmed separately; offline checks validate candidate delivery and the review contract. Which spans Codex marks is assessed in actual conversation.

[Codex hook contract](https://learn.chatgpt.com/docs/hooks#stop).
