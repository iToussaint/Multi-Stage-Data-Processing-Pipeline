"""Unit tests for structured logging."""

import json
import logging

from multi_stage_data_processing_pipeline.logging_config import (
    JsonFormatter,
    configure_logging,
)


def _record(**extra: object) -> logging.LogRecord:
    """Build a log record with extra attributes."""
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", None, None)
    record.__dict__.update(extra)
    return record


def test_format_outputs_json_with_extras() -> None:
    """Standard fields and extras appear in the JSON output."""
    output = json.loads(JsonFormatter().format(_record(stage="TextCleaner")))

    assert output["message"] == "hello"
    assert output["level"] == "INFO"
    assert output["logger"] == "test"
    assert output["stage"] == "TextCleaner"
    assert "timestamp" in output
    assert "pathname" not in output


def test_format_includes_exception() -> None:
    """Exception tracebacks are included."""
    try:
        raise RuntimeError("bad")
    except RuntimeError:
        import sys

        record = logging.LogRecord(
            "test", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )

    output = json.loads(JsonFormatter().format(record))

    assert "RuntimeError: bad" in output["exception"]


def test_configure_logging_installs_json_handler() -> None:
    """The root logger gets a single JSON handler at the given level."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        configure_logging(logging.DEBUG)

        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, JsonFormatter)
    finally:
        root.handlers, root.level = saved_handlers, saved_level
