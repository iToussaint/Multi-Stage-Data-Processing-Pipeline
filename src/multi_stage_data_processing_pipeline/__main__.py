"""Command-line entry point: ``python -m multi_stage_data_processing_pipeline``."""

import argparse
import logging
import os
import sys

import psycopg

from multi_stage_data_processing_pipeline.analyzer import SentimentAnalyzer
from multi_stage_data_processing_pipeline.cleaner import TextCleaner
from multi_stage_data_processing_pipeline.exceptions import PipelineError
from multi_stage_data_processing_pipeline.logging_config import configure_logging
from multi_stage_data_processing_pipeline.pipeline import Pipeline
from multi_stage_data_processing_pipeline.storer import DatabaseStorer


def main(argv: list[str] | None = None) -> int:
    """Run the pipeline on text given on the command line.

    Args:
        argv: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="raw text to process")
    parser.add_argument(
        "--dsn",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection string (defaults to $DATABASE_URL)",
    )
    parser.add_argument("--debug", action="store_true", help="enable debug logs")
    args = parser.parse_args(argv)

    if not args.dsn:
        parser.error("a database DSN is required (--dsn or DATABASE_URL)")

    configure_logging(logging.DEBUG if args.debug else logging.INFO)

    try:
        with psycopg.connect(args.dsn) as connection:
            storer = DatabaseStorer(connection)
            storer.create_schema()
            pipeline = Pipeline([TextCleaner(), SentimentAnalyzer(), storer])
            record = pipeline.run(args.text)
    except (PipelineError, psycopg.Error) as exc:
        logging.getLogger(__name__).error("pipeline aborted: %s", exc)
        return 1

    print(
        f"id={record.record_id} sentiment={record.sentiment} score={record.score}",
        file=sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
