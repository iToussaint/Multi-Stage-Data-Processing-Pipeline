"""Text cleaning stage."""

import logging
import re
from dataclasses import replace

from multi_stage_data_processing_pipeline.base import PipelineStage
from multi_stage_data_processing_pipeline.exceptions import CleaningError
from multi_stage_data_processing_pipeline.models import TextRecord

logger = logging.getLogger(__name__)

_HTML_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_NON_TEXT = re.compile(r"[^a-z0-9'\s]")
_WHITESPACE = re.compile(r"\s+")


class TextCleaner(PipelineStage):
    """Normalize raw text so it can be analyzed.

    Cleaning lowercases the text and removes HTML tags, URLs, punctuation and
    redundant whitespace.
    """

    def process(self, record: TextRecord) -> TextRecord:
        """Clean the record's raw text.

        Args:
            record: Record whose ``raw_text`` should be cleaned.

        Returns:
            A copy of the record with ``cleaned_text`` set.

        Raises:
            CleaningError: If the raw text is not a string or nothing is left
                after cleaning.
        """
        if not isinstance(record.raw_text, str):
            raise CleaningError(
                f"raw_text must be a string, got {type(record.raw_text).__name__}"
            )

        text = record.raw_text.lower()
        text = _HTML_TAG.sub(" ", text)
        text = _URL.sub(" ", text)
        text = _NON_TEXT.sub(" ", text)
        text = _WHITESPACE.sub(" ", text).strip()

        if not text:
            raise CleaningError("text is empty after cleaning")

        logger.debug(
            "text cleaned",
            extra={"stage": self.name, "chars_in": len(record.raw_text)},
        )
        return replace(record, cleaned_text=text)
