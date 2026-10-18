# Debugging Session

This document records the intentional bug introduced into the pipeline and how it
was found with the VS Code debugger (configurations in `.vscode/launch.json`).
Screenshots of each step go in `docs/screenshots/`.

## 1. The intentional bug

In `SentimentAnalyzer.process` (`src/multi_stage_data_processing_pipeline/analyzer.py`)
the score was changed to divide by the number of sentiment hits instead of the
number of words, and the hit counts were swapped:

```python
# buggy
score = round((negative_hits - positive_hits) / max(positive_hits + negative_hits, 1), 4)

# correct
score = round((positive_hits - negative_hits) / len(words), 4)
```

## 2. Symptom

`pytest -m "not integration"` fails:

```
FAILED tests/unit/test_analyzer.py::test_process_scores_text[this is great-...]
AssertionError: assert <Sentiment.NEGATIVE: 'negative'> is <Sentiment.POSITIVE: 'positive'>
```

The integration test `test_full_pipeline_stores_result` also fails because the row
in PostgreSQL is stored as `negative` with score `-1.0`.

## 3. Breakpoints

1. Set a breakpoint on the `score = ...` line in `analyzer.py`.
2. Set a breakpoint on `record = stage.process(record)` in `pipeline.py`.
3. Run the **Debug unit tests** launch configuration.

## 4. Watch expressions

Added in the *Watch* panel while paused in `SentimentAnalyzer.process`:

| Expression | Value | Expected |
|---|---|---|
| `words` | `['this', 'is', 'great']` | same |
| `positive_hits` | `1` | `1` |
| `negative_hits` | `0` | `0` |
| `positive_hits - negative_hits` | `1` | `1` |
| `score` | `-1.0` | `0.3333` |

The hit counts are correct, so the error is in the score formula itself: the sign is
reversed and the denominator is the number of hits rather than the number of words.

## 5. Call stack inspection

When paused in the analyzer during the integration run, the *Call Stack* panel shows:

```
SentimentAnalyzer.process   analyzer.py
Pipeline.run                pipeline.py
test_full_pipeline_stores_result   test_pipeline_postgres.py
```

Selecting the `Pipeline.run` frame shows `stage` is the `SentimentAnalyzer` instance
and `record.cleaned_text` is already correct, confirming that `TextCleaner` is not
at fault and the defect is isolated to the analysis stage.

## 6. Fix and verification

The formula was restored to `(positive_hits - negative_hits) / len(words)`. All unit
and integration tests pass again, and the structured log line for
`"stage completed"` / `"stage": "SentimentAnalyzer"` shows `"score": 0.3333`.
