"""Custom exceptions for depivot."""


class DepivotError(Exception):
    """Base exception for depivot."""

    pass


class ValidationError(DepivotError):
    """Validation error."""

    pass


class FileProcessingError(DepivotError):
    """Error processing file."""

    pass


class ColumnError(DepivotError):
    """Error with column specification."""

    pass


class SheetError(DepivotError):
    """Error with sheet specification or processing."""

    pass


class DatabaseError(DepivotError):
    """Error with database operations."""

    pass
