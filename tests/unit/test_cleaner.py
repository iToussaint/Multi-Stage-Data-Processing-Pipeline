"""Unit tests for TextCleaner."""

from typing import Any, cast

import pytest

from multi_stage_data_processing_pipeline.cleaner import TextCleaner
from multi_stage_data_processing_pipeline.exceptions import CleaningError
from multi_stage_data_processing_pipeline.models import TextRecord


@pytest.fixture
def cleaner() -> TextCleaner:
    """Return a fresh cleaner."""
    return TextCleaner()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hello World", "hello world"),
        ("  lots   of\n\tspace  ", "lots of space"),
        ("<p>Great <b>product</b></p>", "great product"),
        ("see https://example.com and www.test.org now", "see and now"),
        ("Wow!!! It's 100% good.", "wow it's 100 good"),
    ],
)
def test_process_cleans_text(cleaner: TextCleaner, raw: str, expected: str) -> None:
    """Text is lowercased and stripped of markup, URLs and punctuation."""
    result = cleaner.process(TextRecord(raw_text=raw))

    assert result.cleaned_text == expected


def test_process_keeps_raw_text(cleaner: TextCleaner) -> None:
    """The original raw text is preserved on the returned record."""
    result = cleaner.process(TextRecord(raw_text="Hi!"))

    assert result.raw_text == "Hi!"


def test_process_returns_new_record(cleaner: TextCleaner) -> None:
    """The input record is not mutated."""
    record = TextRecord(raw_text="Hi")

    result = cleaner.process(record)

    assert result is not record
    assert record.cleaned_text is None


@pytest.mark.parametrize("raw", ["", "   ", "!!!", "<br/>", "https://only.url"])
def test_process_raises_when_nothing_left(cleaner: TextCleaner, raw: str) -> None:
    """Input that is empty after cleaning raises CleaningError."""
    with pytest.raises(CleaningError, match="empty"):
        cleaner.process(TextRecord(raw_text=raw))


def test_process_raises_for_non_string(cleaner: TextCleaner) -> None:
    """Non-string input raises CleaningError."""
    record = TextRecord(raw_text=cast(Any, 123))

    with pytest.raises(CleaningError, match="must be a string"):
        cleaner.process(record)


def test_name(cleaner: TextCleaner) -> None:
    """The stage name is the class name."""
    assert cleaner.name == "TextCleaner"
