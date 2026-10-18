"""Pipeline that runs a sequence of injected stages."""

import logging
import time
from collections.abc import Sequence

from multi_stage_data_processing_pipeline.base import PipelineStage
from multi_stage_data_processing_pipeline.exceptions import PipelineError
from multi_stage_data_processing_pipeline.models import TextRecord

logger = logging.getLogger(__name__)


class Pipeline:
    """Run raw text through an ordered list of stages.

    Stages are supplied by the caller (dependency injection), so any stage can be
    replaced by another ``PipelineStage`` implementation without changing this
    class.
    """

    def __init__(self, stages: Sequence[PipelineStage]) -> None:
        """Create a pipeline.

        Args:
            stages: Stages to run, in order.

        Raises:
            ValueError: If no stages are given.
        """
        if not stages:
            raise ValueError("a pipeline needs at least one stage")
        self._stages = tuple(stages)

    @property
    def stages(self) -> tuple[PipelineStage, ...]:
        """Return the configured stages.

        Returns:
            The stages in execution order.
        """
        return self._stages

    def run(self, raw_text: str) -> TextRecord:
        """Process raw text through every stage.

        The record state is logged after each stage so data can be traced through
        the pipeline.

        Args:
            raw_text: The text to process.

        Returns:
            The record produced by the last stage.

        Raises:
            PipelineError: The stage-specific error raised by the failing stage.
        """
        record = TextRecord(raw_text=raw_text)
        logger.info("pipeline started", extra={"record": record.to_log_dict()})

        for stage in self._stages:
            start = time.perf_counter()
            try:
                record = stage.process(record)
            except PipelineError as exc:
                logger.error(
                    "stage failed",
                    extra={
                        "stage": stage.name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "record": record.to_log_dict(),
                    },
                )
                raise
            logger.info(
                "stage completed",
                extra={
                    "stage": stage.name,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 3),
                    "record": record.to_log_dict(),
                },
            )

        logger.info("pipeline finished", extra={"record": record.to_log_dict()})
        return record
