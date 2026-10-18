"""Integration tests: full pipeline against a real PostgreSQL container."""

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from multi_stage_data_processing_pipeline.analyzer import SentimentAnalyzer
from multi_stage_data_processing_pipeline.cleaner import TextCleaner
from multi_stage_data_processing_pipeline.exceptions import CleaningError
from multi_stage_data_processing_pipeline.models import Sentiment
from multi_stage_data_processing_pipeline.pipeline import Pipeline
from multi_stage_data_processing_pipeline.storer import DatabaseStorer

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def postgres() -> Iterator[PostgresContainer]:
    """Start a PostgreSQL container for the test module."""
    with PostgresContainer("postgres:16-alpine", driver=None) as container:
        yield container


@pytest.fixture
def connection(postgres: PostgresContainer) -> Iterator[psycopg.Connection[Any]]:
    """Open a connection on a freshly created, empty schema."""
    with psycopg.connect(postgres.get_connection_url()) as conn:
        conn.execute("DROP TABLE IF EXISTS processed_texts")
        conn.commit()
        yield conn


@pytest.fixture
def pipeline(connection: psycopg.Connection[Any]) -> Pipeline:
    """Assemble the production pipeline with a real storer."""
    storer = DatabaseStorer(connection)
    storer.create_schema()
    return Pipeline([TextCleaner(), SentimentAnalyzer(), storer])


def test_full_pipeline_stores_result(
    pipeline: Pipeline, connection: psycopg.Connection[Any]
) -> None:
    """Raw text is cleaned, analyzed and persisted."""
    result = pipeline.run("<p>I LOVE this product, it's AMAZING!</p>")

    row = connection.execute(
        "SELECT raw_text, cleaned_text, sentiment, score FROM processed_texts "
        "WHERE id = %s",
        (result.record_id,),
    ).fetchone()

    assert row == (
        "<p>I LOVE this product, it's AMAZING!</p>",
        "i love this product it's amazing",
        "positive",
        pytest.approx(0.3333),
    )
    assert result.sentiment is Sentiment.POSITIVE


def test_multiple_inputs_are_stored(
    pipeline: Pipeline, connection: psycopg.Connection[Any]
) -> None:
    """Each run inserts one row with the matching label."""
    inputs = {
        "This is terrible and awful.": "negative",
        "Great, great, great!": "positive",
        "The meeting is at noon.": "neutral",
    }

    ids = {pipeline.run(text).record_id: label for text, label in inputs.items()}

    rows = connection.execute("SELECT id, sentiment FROM processed_texts").fetchall()
    assert dict(rows) == ids


def test_failed_run_stores_nothing(
    pipeline: Pipeline, connection: psycopg.Connection[Any]
) -> None:
    """A run that fails before storage leaves the table empty."""
    with pytest.raises(CleaningError):
        pipeline.run("!!! ???")

    count = connection.execute("SELECT COUNT(*) FROM processed_texts").fetchone()
    assert count == (0,)
