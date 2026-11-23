# Design

## Scope and lifecycle

The handler accepts a `Stop` payload with `stop_hook_active: false` and a non-empty `last_assistant_message`. It does not register for tool or subagent events. It evaluates a maximum of 36 candidate clauses and suggests at most 8 spans by default.

The result is either `{}` or `{"decision":"block","reason":"..."}`. Codex treats the latter as a continuation prompt in the original conversation. The reason carries exact original spans, character offsets, and probabilities. It asks Codex to make an independent relevance check, preserve the complete answer, and add `~~` only to accepted spans.

`stop_hook_active` prevents checking that continuation again. A local SQLite unique key on session/turn makes repeated or concurrent deliveries produce at most one block response. No transcript or generated document is rewritten by the handler.

## Segmentation

`markdown-it-py` supplies block ranges for code, blockquotes, HTML, and tables. An offset-preserving mask adds inline code, links, URL text, reference definitions, formatting delimiters, and existing strikethrough. The scanner never rewrites the input while detecting spans.

One scanner recognizes `，,；;：:。！？!?` and newlines, with a contextual rule for periods. Numeric punctuation is preserved, including `1.14`, `1,000`, and `12:30`. A small abbreviation set avoids common period boundaries. A separate set of sentence and paragraph boundaries supplies surrounding context. Each candidate retains an exact `[start, end)` range in Python Unicode character offsets.

This is a lightweight prose scanner, not a linguistic parser. Long clauses above 800 characters are excluded from hook suggestions; messages above the configured length limit are skipped. Protected regions remain present in surrounding context where needed to understand a prose clause, but never become annotation targets.

## Judgment contract

The only endpoint is `https://openrouter.ai/api/alpha/decisions`. The model is `typesafe/jev-1.14`, resolved by OpenRouter to a dated build. The request has a shared state with the user question and target-specific clauses/contexts, and one named `noul` question per candidate.

Criteria describe both unnecessary defensive prose and necessary information. They explicitly preserve concrete failures, requested constraints, material uncertainty, quotations, examples, and fictional dialogue. Candidate text is treated as data. The output validator requires a numeric, finite probability in `[0,1]` for every requested ID.

The default sends up to 12 questions together. Larger messages are chunked. The hook does not retry failed requests: it returns `{}` and records only failure metadata. `inspect --live` exposes errors for troubleshooting; the evaluation runner retries transient transport failures and preserves checkpoints.

## Context and grouping experiment

The evaluation keeps the target clause fixed while changing the accompanying context to the clause itself, its complete sentence, or its paragraph. All modes also receive the same user question. It compares one batched request with separate questions that carry **identical shared state**, so the grouping comparison isolates question grouping rather than silently removing context.

Reversing the question/target order is a separate check. These decisions have no conversational history, and no previous model verdict is fed into another question. They share input text, so measured differences still matter; there is no claim of perfect statistical independence.

## Credentials, installation, and trust

Credentials come from a non-empty `OPENROUTER_API_KEY` or a private local env file. The parser reads a literal assignment without running a shell or evaluating substitutions. API error bodies and credentials are never written to hook stdout or metadata logs.

The installer uses atomic file replacement, backs up the old hooks file, and merges one identifiable handler. It does not edit Codex hook-trust records. Users review the new handler in Codex App. The absolute Python command continues to work when the app is launched outside a shell.

## Validation boundaries

Unit tests cover offsets, Markdown protection, response validation, threshold application, continuation guards, failure behavior, and non-destructive installation. Live Chinese tests cover the decision service and grouping/context choices.

A live protocol smoke check ran the installer's generated command with a synthetic Stop payload and an empty API-key environment variable. The private key-file fallback succeeded; Jev returned 0.96 for the birthday-wish disclaimer, and the hook returned a block prompt. Duplicate delivery and `stop_hook_active: true` both returned `{}` without another API call. This checks the installed command and hook protocol; App rendering was confirmed separately in a conversation. TUI rendering and English classification quality were left outside this release's validation.

Sources: [Codex hooks](https://learn.chatgpt.com/docs/hooks), [OpenRouter Decisions schema](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request), [Jev typed-question tutorial](https://openrouter.ai/blog/tutorials/how-to-use-jev/).
