"""Simulated sentiment analysis stage."""

import logging
from collections.abc import Iterable
from dataclasses import replace

from multi_stage_data_processing_pipeline.base import PipelineStage
from multi_stage_data_processing_pipeline.exceptions import AnalysisError
from multi_stage_data_processing_pipeline.models import Sentiment, TextRecord

logger = logging.getLogger(__name__)

DEFAULT_POSITIVE_WORDS = frozenset(
    {"good", "great", "excellent", "happy", "love", "awesome", "nice", "amazing"}
)
DEFAULT_NEGATIVE_WORDS = frozenset(
    {"bad", "terrible", "awful", "sad", "hate", "poor", "horrible", "worst"}
)


class SentimentAnalyzer(PipelineStage):
    """Score cleaned text with a simple word lexicon.

    The score is ``(positive_hits - negative_hits) / total_words`` and therefore
    lies in ``[-1.0, 1.0]``. Scores above ``threshold`` are positive, scores below
    ``-threshold`` are negative and everything else is neutral.
    """

    def __init__(
        self,
        positive_words: Iterable[str] = DEFAULT_POSITIVE_WORDS,
        negative_words: Iterable[str] = DEFAULT_NEGATIVE_WORDS,
        threshold: float = 0.0,
    ) -> None:
        """Create an analyzer.

        Args:
            positive_words: Words that count towards a positive score.
            negative_words: Words that count towards a negative score.
            threshold: Minimum absolute score for a non-neutral label.

        Raises:
            ValueError: If ``threshold`` is outside ``[0.0, 1.0)``.
        """
        if not 0.0 <= threshold < 1.0:
            raise ValueError("threshold must be in the range [0.0, 1.0)")
        self._positive = frozenset(positive_words)
        self._negative = frozenset(negative_words)
        self._threshold = threshold

    def process(self, record: TextRecord) -> TextRecord:
        """Analyze the sentiment of the record's cleaned text.

        Args:
            record: Record whose ``cleaned_text`` should be analyzed.

        Returns:
            A copy of the record with ``sentiment`` and ``score`` set.

        Raises:
            AnalysisError: If the record has no cleaned text.
        """
        if not record.cleaned_text:
            raise AnalysisError("record has no cleaned_text to analyze")

        words = record.cleaned_text.split()
        positive_hits = sum(word in self._positive for word in words)
        negative_hits = sum(word in self._negative for word in words)
        score = round((positive_hits - negative_hits) / len(words), 4)

        logger.debug(
            "sentiment scored",
            extra={
                "stage": self.name,
                "positive_hits": positive_hits,
                "negative_hits": negative_hits,
            },
        )
        return replace(record, sentiment=self._label(score), score=score)

    def _label(self, score: float) -> Sentiment:
        """Map a numeric score to a sentiment label.

        Args:
            score: Sentiment score in ``[-1.0, 1.0]``.

        Returns:
            The matching sentiment label.
        """
        if score > self._threshold:
            return Sentiment.POSITIVE
        if score < -self._threshold:
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL
