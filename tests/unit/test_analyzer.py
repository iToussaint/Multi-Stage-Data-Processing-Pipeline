"""Unit tests for SentimentAnalyzer."""

import pytest

from multi_stage_data_processing_pipeline.analyzer import SentimentAnalyzer
from multi_stage_data_processing_pipeline.exceptions import AnalysisError
from multi_stage_data_processing_pipeline.models import Sentiment, TextRecord


def _cleaned(text: str) -> TextRecord:
    """Build a record that has already been cleaned."""
    return TextRecord(raw_text=text, cleaned_text=text)


@pytest.fixture
def analyzer() -> SentimentAnalyzer:
    """Return an analyzer with the default lexicon."""
    return SentimentAnalyzer()


@pytest.mark.parametrize(
    ("text", "sentiment", "score"),
    [
        ("this is great", Sentiment.POSITIVE, 0.3333),
        ("awful and terrible", Sentiment.NEGATIVE, -0.6667),
        ("the sky is blue", Sentiment.NEUTRAL, 0.0),
        ("good but bad", Sentiment.NEUTRAL, 0.0),
        ("love", Sentiment.POSITIVE, 1.0),
    ],
)
def test_process_scores_text(
    analyzer: SentimentAnalyzer, text: str, sentiment: Sentiment, score: float
) -> None:
    """Sentiment label and score follow the lexicon counts."""
    result = analyzer.process(_cleaned(text))

    assert result.sentiment is sentiment
    assert result.score == score


def test_process_preserves_other_fields(analyzer: SentimentAnalyzer) -> None:
    """Fields set by earlier stages are kept."""
    record = TextRecord(raw_text="Great!", cleaned_text="great")

    result = analyzer.process(record)

    assert result.raw_text == "Great!"
    assert result.cleaned_text == "great"


@pytest.mark.parametrize("cleaned", [None, ""])
def test_process_requires_cleaned_text(
    analyzer: SentimentAnalyzer, cleaned: str | None
) -> None:
    """A record without cleaned text raises AnalysisError."""
    with pytest.raises(AnalysisError):
        analyzer.process(TextRecord(raw_text="x", cleaned_text=cleaned))


def test_custom_lexicon_is_used() -> None:
    """Injected word lists replace the defaults."""
    analyzer = SentimentAnalyzer(positive_words={"python"}, negative_words={"bug"})

    assert analyzer.process(_cleaned("python")).sentiment is Sentiment.POSITIVE
    assert analyzer.process(_cleaned("bug")).sentiment is Sentiment.NEGATIVE
    assert analyzer.process(_cleaned("great")).sentiment is Sentiment.NEUTRAL


def test_threshold_makes_weak_scores_neutral() -> None:
    """Scores within the threshold are labelled neutral."""
    analyzer = SentimentAnalyzer(threshold=0.5)

    result = analyzer.process(_cleaned("a good day overall"))

    assert result.score == 0.25
    assert result.sentiment is Sentiment.NEUTRAL


@pytest.mark.parametrize("threshold", [-0.1, 1.0, 2.0])
def test_invalid_threshold_raises(threshold: float) -> None:
    """Thresholds outside [0, 1) are rejected."""
    with pytest.raises(ValueError, match="threshold"):
        SentimentAnalyzer(threshold=threshold)
