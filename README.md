# Multi-Stage Data Processing Pipeline

A Python pipeline that takes raw text, cleans it, analyzes its sentiment (simulated)
and stores the structured result in PostgreSQL. Each stage is a separate,
independently testable component.

## Architecture

```mermaid
flowchart LR
    IN[Raw text] --> P

    subgraph P[Pipeline]
        direction LR
        C[TextCleaner] --> A[SentimentAnalyzer] --> S[DatabaseStorer]
    end

    S --> DB[(PostgreSQL<br/>processed_texts)]

    I{{PipelineStage ABC}} -. implemented by .-> C
    I -.-> A
    I -.-> S
```

| Component | Responsibility | Error |
|---|---|---|
| `TextCleaner` | Lowercase, strip HTML, URLs, punctuation and extra whitespace | `CleaningError` |
| `SentimentAnalyzer` | Score words against a lexicon, label positive / negative / neutral | `AnalysisError` |
| `DatabaseStorer` | Insert the record into `processed_texts` and return its id | `StorageError` |
| `Pipeline` | Run injected stages in order and log state after each stage | re-raises stage errors |

Design notes:

- **Single responsibility** — each stage does one job; logging setup, data model and
  exceptions live in their own modules.
- **Common interface** — every stage extends the `PipelineStage` ABC
  (`process(record) -> record`), so stages are interchangeable.
- **Dependency injection** — `Pipeline` receives its stages, `DatabaseStorer` receives
  its database connection and `SentimentAnalyzer` receives its word lists. Any stage
  can be swapped without changing the pipeline.
- **Immutable data** — stages pass a frozen `TextRecord` and return a new copy.
- **Structured logging** — JSON log lines record the full `TextRecord` after every
  stage, plus stage name, duration and error details on failure.
- **Custom exceptions** — `CleaningError`, `AnalysisError` and `StorageError` all
  inherit from `PipelineError`.

### Project layout

```
src/multi_stage_data_processing_pipeline/
    base.py            PipelineStage ABC
    models.py          TextRecord, Sentiment
    exceptions.py      PipelineError and stage errors
    cleaner.py         TextCleaner
    analyzer.py        SentimentAnalyzer
    storer.py          DatabaseStorer
    pipeline.py        Pipeline
    logging_config.py  JSON logging
    __main__.py        CLI
tests/
    unit/              isolated stage tests (pytest-mock)
    integration/       full pipeline against PostgreSQL (testcontainers)
docs/debugging.md      debugging session write-up
```

## Setup

Requires Python 3.11+ and Docker (for integration tests).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pre-commit install
```

## Running the pipeline

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
python -m multi_stage_data_processing_pipeline "I love this product, it's amazing!"
# id=1 sentiment=positive score=0.3333
```

Add `--debug` for debug-level logs. Logs are written to stderr as JSON, e.g.:

```json
{"timestamp": "...", "level": "INFO", "logger": "multi_stage_data_processing_pipeline.pipeline", "message": "stage completed", "stage": "TextCleaner", "duration_ms": 0.041, "record": {"raw_text": "I love this product, it's amazing!", "cleaned_text": "i love this product it's amazing", "sentiment": null, "score": null, "record_id": null}}
```

## Testing

```bash
# Unit tests only (no Docker needed)
pytest -m "not integration"

# Integration tests (starts a PostgreSQL container)
pytest -m integration

# All tests with coverage report
coverage run -m pytest
coverage report
coverage html                    # htmlcov/index.html
```

## Code quality

Enforced by pre-commit on every commit:

```bash
black .
ruff check .
mypy src
pre-commit run --all-files
```

## Git workflow

Git Flow: `main` holds released code, `develop` integrates features, and each pipeline
stage is built on its own `feature/*` branch and merged through a pull request.

## Debugging

See [docs/debugging.md](docs/debugging.md) for the intentional bug and how it was
traced with breakpoints, watch expressions and call stack inspection.
