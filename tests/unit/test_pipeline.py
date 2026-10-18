"""Unit tests for Pipeline with mocked stages."""

import logging

import pytest
from pytest_mock import MockerFixture

from multi_stage_data_processing_pipeline.base import PipelineStage
from multi_stage_data_processing_pipeline.exceptions import AnalysisError
from multi_stage_data_processing_pipeline.models import TextRecord
from multi_stage_data_processing_pipeline.pipeline import Pipeline


class UpperCaseStage(PipelineStage):
    """Test stage that upper-cases the raw text into cleaned_text."""

    def process(self, record: TextRecord) -> TextRecord:
        """Upper-case the raw text."""
        return TextRecord(
            raw_text=record.raw_text, cleaned_text=record.raw_text.upper()
        )


def test_run_passes_record_through_stages_in_order(mocker: MockerFixture) -> None:
    """Each stage receives the previous stage's output."""
    first = mocker.create_autospec(PipelineStage, instance=True)
    second = mocker.create_autospec(PipelineStage, instance=True)
    after_first = TextRecord(raw_text="hi", cleaned_text="hi")
    after_second = TextRecord(raw_text="hi", cleaned_text="hi", record_id=1)
    first.process.return_value = after_first
    second.process.return_value = after_second

    result = Pipeline([first, second]).run("hi")

    first.process.assert_called_once_with(TextRecord(raw_text="hi"))
    second.process.assert_called_once_with(after_first)
    assert result is after_second


def test_run_stops_and_reraises_on_stage_error(mocker: MockerFixture) -> None:
    """A failing stage aborts the run and later stages are skipped."""
    failing = mocker.create_autospec(PipelineStage, instance=True)
    failing.process.side_effect = AnalysisError("boom")
    later = mocker.create_autospec(PipelineStage, instance=True)

    with pytest.raises(AnalysisError, match="boom"):
        Pipeline([failing, later]).run("hi")

    later.process.assert_not_called()


def test_stages_can_be_swapped() -> None:
    """Any PipelineStage implementation can be injected."""
    result = Pipeline([UpperCaseStage()]).run("hi")

    assert result.cleaned_text == "HI"


def test_stages_property_returns_injected_stages() -> None:
    """The configured stages are exposed in order."""
    stage = UpperCaseStage()

    assert Pipeline([stage]).stages == (stage,)


def test_empty_pipeline_is_rejected() -> None:
    """A pipeline without stages cannot be built."""
    with pytest.raises(ValueError, match="at least one stage"):
        Pipeline([])


def test_run_logs_state_after_each_stage(caplog: pytest.LogCaptureFixture) -> None:
    """State is logged after every stage."""
    with caplog.at_level(logging.INFO):
        Pipeline([UpperCaseStage()]).run("hi")

    completed = [r for r in caplog.records if r.getMessage() == "stage completed"]
    assert len(completed) == 1
    assert completed[0].__dict__["stage"] == "UpperCaseStage"
    assert completed[0].__dict__["record"]["cleaned_text"] == "HI"


def test_run_logs_failures(
    mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    """Stage failures are logged with the error type."""
    failing = mocker.create_autospec(PipelineStage, instance=True)
    failing.name = "Failing"
    failing.process.side_effect = AnalysisError("boom")

    with caplog.at_level(logging.ERROR), pytest.raises(AnalysisError):
        Pipeline([failing]).run("hi")

    (failure,) = [r for r in caplog.records if r.getMessage() == "stage failed"]
    assert failure.__dict__["stage"] == "Failing"
    assert failure.__dict__["error_type"] == "AnalysisError"
