"""Input validation utilities for depivot."""

from pathlib import Path
from typing import List

import pandas as pd

from depivot.exceptions import ColumnError, ValidationError


def validate_file_path(path: Path, must_exist: bool = True) -> Path:
    """Validate file path exists and has correct extension.

    Args:
        path: Path to file
        must_exist: Whether file must exist (default: True)

    Returns:
        Validated Path object

    Raises:
        ValidationError: If file doesn't exist or has invalid extension
    """
    if must_exist and not path.exists():
        raise ValidationError(f"File not found: {path}")

    if not path.is_file() and must_exist:
        raise ValidationError(f"Path is not a file: {path}")

    valid_extensions = {".xlsx", ".xls"}
    if path.suffix.lower() not in valid_extensions:
        raise ValidationError(
            f"Invalid file extension: {path.suffix}. "
            f"Expected one of: {', '.join(valid_extensions)}"
        )

    return path


def validate_columns_exist(df: pd.DataFrame, columns: List[str], sheet_name: str = "") -> None:
    """Validate that columns exist in DataFrame.

    Args:
        df: DataFrame to check
        columns: Column names to validate
        sheet_name: Optional sheet name for error messages

    Raises:
        ColumnError: If any column is missing
    """
    missing_cols = [col for col in columns if col not in df.columns]

    if missing_cols:
        sheet_info = f" in sheet '{sheet_name}'" if sheet_name else ""
        available_cols = ", ".join(df.columns.tolist())
        raise ColumnError(
            f"Column(s) not found{sheet_info}: {', '.join(missing_cols)}. "
            f"Available columns: {available_cols}"
        )


def validate_id_value_vars(id_vars: List[str], value_vars: List[str]) -> None:
    """Validate no overlap between id_vars and value_vars.

    Args:
        id_vars: Identifier columns
        value_vars: Value columns to unpivot

    Raises:
        ColumnError: If there's overlap between id_vars and value_vars
    """
    overlap = set(id_vars) & set(value_vars)

    if overlap:
        raise ColumnError(
            f"Columns cannot be both id_vars and value_vars: {', '.join(overlap)}"
        )


def validate_output_path(output_path: Path, overwrite: bool = False) -> None:
    """Validate output path and check for overwrites.

    Args:
        output_path: Path for output file
        overwrite: Whether to allow overwriting existing files

    Raises:
        ValidationError: If file exists and overwrite is False
    """
    if output_path.exists() and not overwrite:
        raise ValidationError(
            f"Output file already exists: {output_path}. "
            "Use --overwrite to overwrite existing files."
        )
