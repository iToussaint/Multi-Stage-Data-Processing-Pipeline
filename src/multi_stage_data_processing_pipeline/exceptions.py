"""Custom exceptions raised by the pipeline stages."""


class PipelineError(Exception):
    """Base class for every error raised by the pipeline."""


class CleaningError(PipelineError):
    """Raised when the text cleaning stage cannot process its input."""


class AnalysisError(PipelineError):
    """Raised when the sentiment analysis stage cannot process its input."""


class StorageError(PipelineError):
    """Raised when the storage stage cannot persist a record."""
