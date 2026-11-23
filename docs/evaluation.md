# Chinese evaluation

The release uses **paragraph context, batched questions, and a 0.8 threshold**. The target remains the short clause; its paragraph and the latest user question help Jev decide whether the qualification serves the user's request.

## Recorded run

Run on 2026-11-23 through OpenRouter's Decisions API, using `typesafe/jev-1.14`, resolved to `typesafe/jev-1.14-20261014`. Prompt hash: `3b4bbefc50028f2a`.

The [dataset](../evals/cases.zh.jsonl) contains 32 hand-labeled, synthetic Chinese answers: 24 calibration cases and 8 validation cases. There are 42 keyword candidates, including 27 labeled unnecessary qualifications and 15 useful or quoted clauses. Four answers have no candidates. All labeled positive spans were found by the scanner in this dataset.

Each context variant receives the same user question. For the grouping comparison, separate requests keep the identical shared state used by the batch and ask one question at a time. The test changes request grouping without changing which candidate texts the model can see.

## Context and request grouping

Thresholds were selected on calibration data using F0.5, which emphasizes precision, with higher precision and then higher thresholds breaking ties. The table shows validation results at each configuration's calibration-selected threshold.

| Context | Requests | Threshold | Calibration: caught / 19 | Calibration false positives | Validation: caught / 8 | Validation false positives | Median time per answer |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Clause | Batched | 0.70 | 17 | 0 | 8 | 0 | 0.651 s |
| Clause | Separate | 0.75 | 17 | 0 | 8 | 0 | 0.720 s |
| Sentence | Batched | 0.70 | 17 | 0 | 7 | 0 | 0.664 s |
| Sentence | Separate | 0.70 | 17 | 0 | 8 | 0 | 0.721 s |
| Paragraph | Batched | **0.80** | **17** | **0** | **8** | **0** | **0.675 s** |
| Paragraph | Separate | 0.60 | 18 | 0 | 8 | 0 | 0.776 s |

The calibration set has 12 negative candidates; validation has 3. Times exclude answers that make no request and include client/network overhead. Separate requests within one answer run sequentially; the evaluation runs up to four answers concurrently.

The batched context variants tied on calibration F0.5. Paragraph context supplies the useful answer before a trailing caveat and achieved the same calibration precision/recall at a higher threshold. We selected it for that contextual coverage. This small sample does not establish a general accuracy advantage over sentence or clause context.

At the chosen 0.8 threshold, paragraph batch and separate requests agreed on all **42/42** candidate labels. Their mean absolute probability difference was **0.0102**, with a maximum of **0.07**. Batched processing used **28 requests / $0.0009051** across the 32 answers, versus **42 requests / $0.001192086** separately. These results support batching as the default.

## Borderline results and ordering

Eight multi-candidate calibration answers were also run with reversed target/question order. A second run repeated their original order to measure ordinary request variation.

| Comparison with the first run | Candidates | Label agreement at 0.8 | Mean absolute probability difference | Maximum difference |
| --- | ---: | ---: | ---: | ---: |
| Same order, repeated | 18 | 18/18 | 0.020 | 0.10 |
| Reversed order | 18 | 16/18 | 0.030 | 0.13 |

The reversed run moved 「这只是文学表达」 from 0.80 to 0.78 and 「这种语气不一定适合所有人」 from 0.85 to 0.75. Probabilities varied even without changing order, so a single reversal comparison cannot isolate the cause. The implementation keeps source order, shares no previous judgments between requests, and passes provisional findings to Codex for a final contextual review.

The two missed calibration clauses were 「不过我没有直接读取磁盘文件」 (0.59) and 「因此无法确认它与最新文件完全一致」 (0.56), following the question 「你能看到注入的个人指令吗？」. They resemble useful capability explanations. The default keeps these borderline clauses; the matched case explicitly asking about disk access is also retained.

These are candidate-level decisions on short synthetic examples. They measure the detector before Codex's final review. The eight validation cases are a small check; English quality and TUI behavior were left outside this evaluation.

## Reproduce

```sh
uv sync --locked --dev
uv run python evals/run.py
uv run python evals/run.py --live --output evals/local/results.zh.json
uv run python evals/stability.py --live \
  --baseline evals/local/results.zh.json \
  --output evals/local/stability.zh.json
```

The first command after installation validates local fixtures only. Live runs use `OPENROUTER_API_KEY` or the configured private key file. The main runner checkpoints completed jobs and retries transport failures up to twice; rerun the same command to resume.

Published evidence: [full probabilities and threshold sweeps](../evals/results.zh.json), [same-order repeat](../evals/stability.zh.json), [rubric and request code](../src/codex_prose_lint/judge.py). The recorded runs contain **226 successful requests**, costing **$0.006764352** in reported API usage. Preliminary smoke calls and an interrupted initial run are outside that recorded total. The raw run records the initial 0.85 configuration; threshold sweeps selected the release default of 0.8 afterward.
