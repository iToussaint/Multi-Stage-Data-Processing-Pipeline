"""PostgreSQL storage stage."""

import logging
from dataclasses import replace
from typing import Any

import psycopg

from multi_stage_data_processing_pipeline.base import PipelineStage
from multi_stage_data_processing_pipeline.exceptions import StorageError
from multi_stage_data_processing_pipeline.models import TextRecord

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS processed_texts (
    id SERIAL PRIMARY KEY,
    raw_text TEXT NOT NULL,
    cleaned_text TEXT NOT NULL,
    sentiment VARCHAR(16) NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

INSERT_SQL = """
INSERT INTO processed_texts (raw_text, cleaned_text, sentiment, score)
VALUES (%s, %s, %s, %s)
RETURNING id
"""


class DatabaseStorer(PipelineStage):
    """Persist analyzed records to the ``processed_texts`` table.

    The database connection is injected so the stage can be tested with a mock
    and pointed at any PostgreSQL instance.
    """

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        """Create a storer.

        Args:
            connection: An open psycopg connection.
        """
        self._connection = connection

    def create_schema(self) -> None:
        """Create the ``processed_texts`` table if it does not exist.

        Raises:
            StorageError: If the table cannot be created.
        """
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(CREATE_TABLE_SQL)
            self._connection.commit()
        except psycopg.Error as exc:
            self._connection.rollback()
            raise StorageError(f"failed to create schema: {exc}") from exc

    def process(self, record: TextRecord) -> TextRecord:
        """Insert the record and return it with its database id.

        Args:
            record: Fully analyzed record.

        Returns:
            A copy of the record with ``record_id`` set.

        Raises:
            StorageError: If the record is incomplete or the insert fails.
        """
        if record.cleaned_text is None or record.sentiment is None:
            raise StorageError("record must be cleaned and analyzed before storage")
        if record.score is None:
            raise StorageError("record has no sentiment score")

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(
                    INSERT_SQL,
                    (
                        record.raw_text,
                        record.cleaned_text,
                        record.sentiment.value,
                        record.score,
                    ),
                )
                row = cursor.fetchone()
            self._connection.commit()
        except psycopg.Error as exc:
            self._connection.rollback()
            raise StorageError(f"failed to store record: {exc}") from exc

        if row is None:
            raise StorageError("insert did not return an id")

        logger.debug("record stored", extra={"stage": self.name, "record_id": row[0]})
        return replace(record, record_id=int(row[0]))
