"""Unit tests for DatabaseStorer using a mocked psycopg connection."""

from unittest.mock import MagicMock

import psycopg
import pytest
from pytest_mock import MockerFixture

from multi_stage_data_processing_pipeline.exceptions import StorageError
from multi_stage_data_processing_pipeline.models import Sentiment, TextRecord
from multi_stage_data_processing_pipeline.storer import (
    CREATE_TABLE_SQL,
    INSERT_SQL,
    DatabaseStorer,
)

ANALYZED = TextRecord(
    raw_text="Great!",
    cleaned_text="great",
    sentiment=Sentiment.POSITIVE,
    score=1.0,
)


@pytest.fixture
def cursor(mocker: MockerFixture) -> MagicMock:
    """Return a mock cursor."""
    mock: MagicMock = mocker.MagicMock()
    return mock


@pytest.fixture
def connection(mocker: MockerFixture, cursor: MagicMock) -> MagicMock:
    """Return a mock connection whose cursor() context yields ``cursor``."""
    conn: MagicMock = mocker.MagicMock(spec=psycopg.Connection)
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn


def test_process_inserts_record_and_sets_id(
    connection: MagicMock, cursor: MagicMock
) -> None:
    """The record is inserted and its new id returned."""
    cursor.fetchone.return_value = (42,)

    result = DatabaseStorer(connection).process(ANALYZED)

    cursor.execute.assert_called_once_with(
        INSERT_SQL, ("Great!", "great", "positive", 1.0)
    )
    connection.commit.assert_called_once()
    assert result.record_id == 42
    assert result.sentiment is Sentiment.POSITIVE


def test_process_wraps_database_errors(
    connection: MagicMock, cursor: MagicMock
) -> None:
    """Psycopg errors are rolled back and re-raised as StorageError."""
    cursor.execute.side_effect = psycopg.OperationalError("connection lost")

    with pytest.raises(StorageError, match="connection lost") as exc_info:
        DatabaseStorer(connection).process(ANALYZED)

    connection.rollback.assert_called_once()
    connection.commit.assert_not_called()
    assert isinstance(exc_info.value.__cause__, psycopg.OperationalError)


def test_process_raises_when_no_id_returned(
    connection: MagicMock, cursor: MagicMock
) -> None:
    """A missing RETURNING row raises StorageError."""
    cursor.fetchone.return_value = None

    with pytest.raises(StorageError, match="did not return an id"):
        DatabaseStorer(connection).process(ANALYZED)


@pytest.mark.parametrize(
    "record",
    [
        TextRecord(raw_text="x"),
        TextRecord(raw_text="x", cleaned_text="x"),
        TextRecord(raw_text="x", cleaned_text="x", sentiment=Sentiment.NEUTRAL),
    ],
)
def test_process_rejects_incomplete_records(
    connection: MagicMock, record: TextRecord
) -> None:
    """Records that were not cleaned and analyzed are rejected."""
    with pytest.raises(StorageError):
        DatabaseStorer(connection).process(record)

    connection.cursor.assert_not_called()


def test_create_schema_executes_ddl(connection: MagicMock, cursor: MagicMock) -> None:
    """The table is created and the transaction committed."""
    DatabaseStorer(connection).create_schema()

    cursor.execute.assert_called_once_with(CREATE_TABLE_SQL)
    connection.commit.assert_called_once()


def test_create_schema_wraps_database_errors(
    connection: MagicMock, cursor: MagicMock
) -> None:
    """Schema errors are rolled back and re-raised as StorageError."""
    cursor.execute.side_effect = psycopg.ProgrammingError("denied")

    with pytest.raises(StorageError, match="denied"):
        DatabaseStorer(connection).create_schema()

    connection.rollback.assert_called_once()
