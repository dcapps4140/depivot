"""Tests for validation utilities."""
import pytest
import pandas as pd
from pathlib import Path
from depivot.validators import (
    validate_file_path,
    validate_columns_exist,
    validate_id_value_vars,
    validate_output_path,
)
from depivot.exceptions import ColumnError, ValidationError


# =============================================================================
# VALIDATE FILE PATH TESTS
# =============================================================================

class TestValidateFilePath:
    """Test file path validation."""

    def test_validate_existing_xlsx(self, tmp_path):
        """Test validating existing .xlsx file."""
        test_file = tmp_path / "test.xlsx"
        test_file.touch()

        result = validate_file_path(test_file, must_exist=True)
        assert result == test_file

    def test_validate_existing_xls(self, tmp_path):
        """Test validating existing .xls file."""
        test_file = tmp_path / "test.xls"
        test_file.touch()

        result = validate_file_path(test_file, must_exist=True)
        assert result == test_file

    def test_validate_nonexistent_file_with_must_exist(self, tmp_path):
        """Test that validation fails for non-existent file when must_exist=True."""
        test_file = tmp_path / "nonexistent.xlsx"

        with pytest.raises(ValidationError, match="File not found"):
            validate_file_path(test_file, must_exist=True)

    def test_validate_nonexistent_file_without_must_exist(self, tmp_path):
        """Test that validation passes for non-existent file when must_exist=False."""
        test_file = tmp_path / "nonexistent.xlsx"

        result = validate_file_path(test_file, must_exist=False)
        assert result == test_file

    def test_validate_directory_path_fails(self, tmp_path):
        """Test that validation fails for directory path."""
        # Try to validate a directory as a file
        with pytest.raises(ValidationError, match="Path is not a file"):
            validate_file_path(tmp_path, must_exist=True)

    def test_validate_invalid_extension(self, tmp_path):
        """Test that validation fails for invalid file extension."""
        test_file = tmp_path / "test.csv"
        test_file.touch()

        with pytest.raises(ValidationError, match="Invalid file extension"):
            validate_file_path(test_file, must_exist=True)

    def test_validate_case_insensitive_extension(self, tmp_path):
        """Test that extension validation is case-insensitive."""
        test_file = tmp_path / "test.XLSX"
        test_file.touch()

        result = validate_file_path(test_file, must_exist=True)
        assert result == test_file


# =============================================================================
# VALIDATE COLUMNS EXIST TESTS
# =============================================================================

class TestValidateColumnsExist:
    """Test column existence validation."""

    def test_validate_columns_exist_success(self):
        """Test validation passes when all columns exist."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        # Should not raise
        validate_columns_exist(df, ["A", "B"])

    def test_validate_single_missing_column(self):
        """Test validation fails for single missing column."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        with pytest.raises(ColumnError, match="Column\\(s\\) not found"):
            validate_columns_exist(df, ["A", "C"])

    def test_validate_multiple_missing_columns(self):
        """Test validation fails for multiple missing columns."""
        df = pd.DataFrame({"A": [1, 2]})

        with pytest.raises(ColumnError, match="Column\\(s\\) not found.*B.*C"):
            validate_columns_exist(df, ["B", "C"])

    def test_validate_with_sheet_name(self):
        """Test error message includes sheet name when provided."""
        df = pd.DataFrame({"A": [1, 2]})

        with pytest.raises(ColumnError, match="in sheet 'Sheet1'"):
            validate_columns_exist(df, ["B"], sheet_name="Sheet1")

    def test_validate_without_sheet_name(self):
        """Test error message without sheet name."""
        df = pd.DataFrame({"A": [1, 2]})

        with pytest.raises(ColumnError) as exc_info:
            validate_columns_exist(df, ["B"])

        # Should not contain "in sheet"
        assert "in sheet" not in str(exc_info.value)

    def test_validate_shows_available_columns(self):
        """Test error message shows available columns."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})

        with pytest.raises(ColumnError, match="Available columns:.*A.*B.*C"):
            validate_columns_exist(df, ["D"])

    def test_validate_empty_column_list(self):
        """Test validation with empty column list passes."""
        df = pd.DataFrame({"A": [1, 2]})

        # Should not raise
        validate_columns_exist(df, [])


# =============================================================================
# VALIDATE ID VALUE VARS TESTS
# =============================================================================

class TestValidateIdValueVars:
    """Test id_vars and value_vars validation."""

    def test_validate_no_overlap_success(self):
        """Test validation passes when there's no overlap."""
        id_vars = ["A", "B"]
        value_vars = ["C", "D"]

        # Should not raise
        validate_id_value_vars(id_vars, value_vars)

    def test_validate_single_overlap(self):
        """Test validation fails for single overlapping column."""
        id_vars = ["A", "B"]
        value_vars = ["B", "C"]

        with pytest.raises(ColumnError, match="cannot be both id_vars and value_vars"):
            validate_id_value_vars(id_vars, value_vars)

    def test_validate_multiple_overlap(self):
        """Test validation fails for multiple overlapping columns."""
        id_vars = ["A", "B", "C"]
        value_vars = ["B", "C", "D"]

        with pytest.raises(ColumnError, match="B.*C|C.*B"):
            validate_id_value_vars(id_vars, value_vars)

    def test_validate_empty_lists(self):
        """Test validation with empty lists passes."""
        # Should not raise
        validate_id_value_vars([], [])

    def test_validate_one_empty_list(self):
        """Test validation with one empty list passes."""
        # Should not raise
        validate_id_value_vars(["A", "B"], [])
        validate_id_value_vars([], ["A", "B"])


# =============================================================================
# VALIDATE OUTPUT PATH TESTS
# =============================================================================

class TestValidateOutputPath:
    """Test output path validation."""

    def test_validate_nonexistent_output_path(self, tmp_path):
        """Test validation passes for non-existent output path."""
        output_file = tmp_path / "output.xlsx"

        # Should not raise
        validate_output_path(output_file, overwrite=False)

    def test_validate_existing_output_without_overwrite(self, tmp_path):
        """Test validation fails for existing file without overwrite."""
        output_file = tmp_path / "output.xlsx"
        output_file.touch()

        with pytest.raises(ValidationError, match="Output file already exists"):
            validate_output_path(output_file, overwrite=False)

    def test_validate_existing_output_with_overwrite(self, tmp_path):
        """Test validation passes for existing file with overwrite=True."""
        output_file = tmp_path / "output.xlsx"
        output_file.touch()

        # Should not raise
        validate_output_path(output_file, overwrite=True)

    def test_validate_error_message_suggests_overwrite(self, tmp_path):
        """Test error message suggests using --overwrite flag."""
        output_file = tmp_path / "output.xlsx"
        output_file.touch()

        with pytest.raises(ValidationError, match="Use --overwrite"):
            validate_output_path(output_file, overwrite=False)
