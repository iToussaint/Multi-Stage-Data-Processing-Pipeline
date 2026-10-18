"""Common interface shared by every pipeline stage."""

from abc import ABC, abstractmethod

from multi_stage_data_processing_pipeline.models import TextRecord


class PipelineStage(ABC):
    """Abstract pipeline stage.

    A stage receives a ``TextRecord`` and returns a new ``TextRecord``. Because all
    stages share this contract, they can be injected into ``Pipeline`` in any
    combination and swapped for alternative implementations.
    """

    @property
    def name(self) -> str:
        """Return the stage name used in log messages.

        Returns:
            The class name of the stage.
        """
        return type(self).__name__

    @abstractmethod
    def process(self, record: TextRecord) -> TextRecord:
        """Process a record and return the updated record.

        Args:
            record: The record produced by the previous stage.

        Returns:
            A new record containing this stage's output.
        """
