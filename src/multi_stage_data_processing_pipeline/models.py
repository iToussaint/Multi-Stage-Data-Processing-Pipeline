"""Data structures that flow between pipeline stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class Sentiment(StrEnum):
    """Sentiment labels produced by the analyzer."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class TextRecord:
    """Immutable record passed from one stage to the next.

    Each stage returns a new record with the fields it is responsible for filled in.

    Attributes:
        raw_text: The original input text.
        cleaned_text: Text produced by the cleaning stage.
        sentiment: Label produced by the analysis stage.
        score: Sentiment score in the range [-1.0, 1.0].
        record_id: Database primary key assigned by the storage stage.
    """

    raw_text: str
    cleaned_text: str | None = None
    sentiment: Sentiment | None = None
    score: float | None = None
    record_id: int | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for structured logging.

        Returns:
            A dictionary with every field of the record.
        """
        return asdict(self)
