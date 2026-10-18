"""Unit tests for the command-line entry point."""

import psycopg
import pytest
from pytest_mock import MockerFixture

from multi_stage_data_processing_pipeline.__main__ import main


@pytest.fixture(autouse=True)
def _no_logging_setup(mocker: MockerFixture) -> None:
    """Keep the CLI from replacing pytest's log handlers."""
    mocker.patch("multi_stage_data_processing_pipeline.__main__.configure_logging")


def test_main_runs_pipeline(
    mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """The CLI runs all stages and prints the stored result."""
    connect = mocker.patch("psycopg.connect")
    cursor = connect.return_value.__enter__.return_value.cursor.return_value
    cursor.__enter__.return_value.fetchone.return_value = (7,)

    exit_code = main(["I love it", "--dsn", "postgresql://db"])

    assert exit_code == 0
    connect.assert_called_once_with("postgresql://db")
    assert capsys.readouterr().out.strip() == "id=7 sentiment=positive score=0.3333"


def test_main_returns_error_code_on_failure(mocker: MockerFixture) -> None:
    """Connection failures produce exit code 1."""
    mocker.patch("psycopg.connect", side_effect=psycopg.OperationalError("down"))

    assert main(["text", "--dsn", "postgresql://db"]) == 1


def test_main_requires_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Running without a DSN is a usage error."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(SystemExit):
        main(["text"])
