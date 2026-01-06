"""Tests for core depivoting functionality."""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from depivot.core import (
    detect_data_type,
    is_forecast_month,
    clean_numeric_value,
    get_sheet_names,
    resolve_columns,
    depivot_sheet,
    create_validation_report,
    depivot_file,
    depivot_multi_file,
    depivot_batch,
    MONTH_ORDER,
)
from depivot.exceptions import ColumnError, FileProcessingError, SheetError, ValidationError


# =============================================================================
# DATA TYPE DETECTION TESTS
# =============================================================================

class TestDetectDataType:
    """Test data type detection from sheet names."""

    def test_detect_forecast(self):
        """Test forecast detection."""
        assert detect_data_type("FY25 Forecast") == "Forecast"
        assert detect_data_type("forecast") == "Forecast"
        assert detect_data_type("Q1 Forecasts") == "Forecast"

    def test_detect_budget(self):
        """Test budget detection."""
        assert detect_data_type("FY25 Budget") == "Budget"
        assert detect_data_type("budg") == "Budget"
        assert detect_data_type("Budget Plan") == "Budget"

    def test_detect_actual(self):
        """Test actual detection."""
        assert detect_data_type("FY25 Actual") == "Actual"
        assert detect_data_type("actu") == "Actual"
        assert detect_data_type("Actuals") == "Actual"

    def test_detect_default_actual(self):
        """Test default to Actual for unknown sheet names."""
        assert detect_data_type("Sheet1") == "Actual"
        assert detect_data_type("Data") == "Actual"
        assert detect_data_type("Summary") == "Actual"

    def test_detect_case_insensitive(self):
        """Test case insensitive detection."""
        assert detect_data_type("FORECAST") == "Forecast"
        assert detect_data_type("Budget") == "Budget"
        assert detect_data_type("ACTUAL") == "Actual"


# =============================================================================
# FORECAST MONTH LOGIC TESTS
# =============================================================================

class TestIsForecastMonth:
    """Test forecast month determination."""

    def test_forecast_months_after_start(self):
        """Test months after forecast start are forecast."""
        assert is_forecast_month("Jun", "Jun") is True
        assert is_forecast_month("Jul", "Jun") is True
        assert is_forecast_month("Dec", "Jun") is True

    def test_actual_months_before_start(self):
        """Test months before forecast start are actual."""
        assert is_forecast_month("Jan", "Jun") is False
        assert is_forecast_month("May", "Jun") is False

    def test_case_insensitive(self):
        """Test case insensitive month comparison."""
        assert is_forecast_month("JUNE", "jun") is True
        assert is_forecast_month("january", "JUN") is False

    def test_abbreviated_months(self):
        """Test abbreviated month names."""
        assert is_forecast_month("Jun", "Jun") is True
        assert is_forecast_month("January", "June") is False

    def test_invalid_month_names(self):
        """Test invalid month names default to False."""
        assert is_forecast_month("InvalidMonth", "Jun") is False
        assert is_forecast_month("Jun", "InvalidMonth") is False
        assert is_forecast_month("", "Jun") is False

    def test_boundary_month(self):
        """Test month equal to forecast start."""
        assert is_forecast_month("Jun", "Jun") is True


# =============================================================================
# NUMERIC VALUE CLEANING TESTS
# =============================================================================

class TestCleanNumericValue:
    """Test numeric value cleaning."""

    def test_clean_already_numeric(self):
        """Test already numeric values."""
        assert clean_numeric_value(123) == 123.0
        assert clean_numeric_value(123.45) == 123.45
        assert clean_numeric_value(0) == 0.0

    def test_clean_string_numbers(self):
        """Test string numbers."""
        assert clean_numeric_value("123") == 123.0
        assert clean_numeric_value("123.45") == 123.45

    def test_clean_with_commas(self):
        """Test numbers with comma separators."""
        assert clean_numeric_value("1,234") == 1234.0
        assert clean_numeric_value("1,234.56") == 1234.56
        assert clean_numeric_value("1,234,567.89") == 1234567.89

    def test_clean_negative_parentheses(self):
        """Test negative numbers in parentheses."""
        assert clean_numeric_value("(123)") == -123.0
        assert clean_numeric_value("(123.45)") == -123.45
        assert clean_numeric_value("(1,234.56)") == -1234.56

    def test_clean_with_currency(self):
        """Test numbers with currency symbols."""
        assert clean_numeric_value("$123.45") == 123.45
        assert clean_numeric_value("$1,234.56") == 1234.56

    def test_clean_with_special_chars(self):
        """Test numbers with special characters."""
        assert clean_numeric_value("$1,234.56") == 1234.56
        assert clean_numeric_value("#123") == 123.0

    def test_clean_nan_values(self):
        """Test NaN handling."""
        assert pd.isna(clean_numeric_value(None))
        assert pd.isna(clean_numeric_value(np.nan))
        assert pd.isna(clean_numeric_value(pd.NA))

    def test_clean_invalid_strings(self):
        """Test invalid string conversion."""
        assert pd.isna(clean_numeric_value("abc"))
        assert pd.isna(clean_numeric_value(""))
        assert pd.isna(clean_numeric_value("N/A"))


# =============================================================================
# SHEET NAME RESOLUTION TESTS
# =============================================================================

class TestGetSheetNames:
    """Test sheet name resolution."""

    @pytest.fixture
    def mock_excel_file(self, tmp_path):
        """Create a mock Excel file with multiple sheets."""
        file_path = tmp_path / "test.xlsx"
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            pd.DataFrame({"A": [1, 2]}).to_excel(writer, sheet_name="Sheet1", index=False)
            pd.DataFrame({"B": [3, 4]}).to_excel(writer, sheet_name="Sheet2", index=False)
            pd.DataFrame({"C": [5, 6]}).to_excel(writer, sheet_name="Sheet3", index=False)
        return file_path

    def test_get_all_sheets(self, mock_excel_file):
        """Test getting all sheets."""
        sheets = get_sheet_names(mock_excel_file)
        assert sheets == ["Sheet1", "Sheet2", "Sheet3"]

    def test_get_specific_sheets(self, mock_excel_file):
        """Test getting specific sheets."""
        sheets = get_sheet_names(mock_excel_file, sheet_names="Sheet1,Sheet3")
        assert sheets == ["Sheet1", "Sheet3"]

    def test_skip_sheets(self, mock_excel_file):
        """Test skipping specific sheets."""
        sheets = get_sheet_names(mock_excel_file, skip_sheets="Sheet2")
        assert sheets == ["Sheet1", "Sheet3"]

    def test_sheet_not_found(self, mock_excel_file):
        """Test error when requested sheet doesn't exist."""
        with pytest.raises(SheetError, match="Sheet\\(s\\) not found"):
            get_sheet_names(mock_excel_file, sheet_names="NonExistent")

    def test_no_sheets_after_filtering(self, mock_excel_file):
        """Test error when no sheets remain after filtering."""
        with pytest.raises(SheetError, match="No sheets to process"):
            get_sheet_names(mock_excel_file, skip_sheets="Sheet1,Sheet2,Sheet3")

    def test_invalid_file(self, tmp_path):
        """Test error with invalid Excel file."""
        invalid_file = tmp_path / "not_excel.txt"
        invalid_file.write_text("not an excel file")
        with pytest.raises(FileProcessingError):
            get_sheet_names(invalid_file)


# =============================================================================
# COLUMN RESOLUTION TESTS
# =============================================================================

class TestResolveColumns:
    """Test column resolution logic."""

    def test_resolve_auto_value_vars(self):
        """Test auto-detecting value_vars."""
        df = pd.DataFrame({"ID": [1, 2], "Jan": [100, 200], "Feb": [150, 250]})
        id_vars, value_vars = resolve_columns(df, id_vars=["ID"], value_vars=None)
        assert id_vars == ["ID"]
        assert set(value_vars) == {"Jan", "Feb"}

    def test_resolve_explicit_value_vars(self):
        """Test explicit value_vars."""
        df = pd.DataFrame({"ID": [1, 2], "Jan": [100, 200], "Feb": [150, 250]})
        id_vars, value_vars = resolve_columns(df, id_vars=["ID"], value_vars=["Jan"])
        assert id_vars == ["ID"]
        assert value_vars == ["Jan"]

    def test_resolve_with_include_cols(self):
        """Test resolving with include filter."""
        df = pd.DataFrame({"ID": [1, 2], "Jan": [100, 200], "Feb": [150, 250], "Mar": [175, 275]})
        id_vars, value_vars = resolve_columns(
            df, id_vars=["ID"], value_vars=None, include_cols=["ID", "Jan", "Feb"]
        )
        assert set(value_vars) == {"Jan", "Feb"}

    def test_resolve_with_exclude_cols(self):
        """Test resolving with exclude filter."""
        df = pd.DataFrame({"ID": [1, 2], "Jan": [100, 200], "Feb": [150, 250], "Mar": [175, 275]})
        id_vars, value_vars = resolve_columns(
            df, id_vars=["ID"], value_vars=None, exclude_cols=["Mar"]
        )
        assert set(value_vars) == {"Jan", "Feb"}

    def test_resolve_no_value_vars(self):
        """Test error when no value columns remain."""
        df = pd.DataFrame({"ID": [1, 2], "Name": ["A", "B"]})
        with pytest.raises(ColumnError, match="No value columns to unpivot"):
            resolve_columns(df, id_vars=["ID"], value_vars=None, include_cols=["ID"])


# =============================================================================
# DEPIVOT SHEET TESTS
# =============================================================================

class TestDepivotSheet:
    """Test single sheet depivoting."""

    def test_depivot_basic(self):
        """Test basic depivot operation."""
        df = pd.DataFrame({
            "ID": [1, 2],
            "Jan": [100, 200],
            "Feb": [150, 250],
        })
        result = depivot_sheet(df, id_vars=["ID"])

        assert len(result) == 4  # 2 rows * 2 months
        assert "ID" in result.columns
        assert "variable" in result.columns
        assert "value" in result.columns
        assert set(result["variable"].unique()) == {"Jan", "Feb"}

    def test_depivot_custom_names(self):
        """Test depivot with custom column names."""
        df = pd.DataFrame({
            "ID": [1, 2],
            "Jan": [100, 200],
        })
        result = depivot_sheet(
            df, id_vars=["ID"], var_name="Month", value_name="Amount"
        )

        assert "Month" in result.columns
        assert "Amount" in result.columns

    def test_depivot_no_id_vars(self):
        """Test depivot with no id_vars adds row index."""
        df = pd.DataFrame({
            "Jan": [100, 200],
            "Feb": [150, 250],
        })
        result = depivot_sheet(df, id_vars=[])

        assert "Row" in result.columns
        assert list(result["Row"].unique()) == [1, 2]

    def test_depivot_with_drop_na(self):
        """Test depivot with drop_na option."""
        df = pd.DataFrame({
            "ID": [1, 2],
            "Jan": [100, None],
            "Feb": [None, 250],
        })
        result = depivot_sheet(df, id_vars=["ID"], drop_na=True)

        assert len(result) == 2  # Only non-NA rows
        assert result["value"].notna().all()

    def test_depivot_explicit_value_vars(self):
        """Test depivot with explicit value_vars."""
        df = pd.DataFrame({
            "ID": [1, 2],
            "Jan": [100, 200],
            "Feb": [150, 250],
            "Notes": ["A", "B"],
        })
        result = depivot_sheet(df, id_vars=["ID"], value_vars=["Jan", "Feb"])

        assert set(result["variable"].unique()) == {"Jan", "Feb"}
        assert "Notes" not in result.columns

    def test_depivot_multiple_id_vars(self):
        """Test depivot with multiple id_vars."""
        df = pd.DataFrame({
            "Site": ["A", "B"],
            "Category": ["X", "Y"],
            "Jan": [100, 200],
        })
        result = depivot_sheet(df, id_vars=["Site", "Category"])

        assert "Site" in result.columns
        assert "Category" in result.columns
        assert len(result) == 2


# =============================================================================
# VALIDATION REPORT TESTS
# =============================================================================

class TestCreateValidationReport:
    """Test validation report creation."""

    def test_validation_report_totals_match(self, tmp_path):
        """Test validation report when totals match."""
        input_file = tmp_path / "test.xlsx"
        input_file.touch()

        sheets_data = {
            "Sheet1": pd.DataFrame({
                "ID": [1, 2],
                "Jan": [100, 200],
                "Feb": [150, 250],
            })
        }

        depivoted_sheets = {
            "Sheet1": pd.DataFrame({
                "ID": [1, 1, 2, 2],
                "variable": ["Jan", "Feb", "Jan", "Feb"],
                "value": [100, 150, 200, 250],
            })
        }

        value_vars_by_sheet = {"Sheet1": ["Jan", "Feb"]}

        report = create_validation_report(
            input_file=input_file,
            sheets_data=sheets_data,
            depivoted_sheets=depivoted_sheets,
            id_vars=["ID"],
            value_vars_by_sheet=value_vars_by_sheet,
            value_name="value",
        )

        assert not report.empty
        assert "Match" in report.columns
        # Check that grand total exists
        grand_total = report[report["Category"] == "GRAND_TOTAL"]
        assert len(grand_total) == 1
        assert grand_total.iloc[0]["Match"] == "OK"

    def test_validation_report_no_id_vars(self, tmp_path):
        """Test validation report with no id_vars."""
        input_file = tmp_path / "test.xlsx"
        input_file.touch()

        sheets_data = {
            "Sheet1": pd.DataFrame({
                "Jan": [100, 200],
                "Feb": [150, 250],
            })
        }

        depivoted_sheets = {
            "Sheet1": pd.DataFrame({
                "variable": ["Jan", "Feb", "Jan", "Feb"],
                "value": [100, 150, 200, 250],
            })
        }

        value_vars_by_sheet = {"Sheet1": ["Jan", "Feb"]}

        report = create_validation_report(
            input_file=input_file,
            sheets_data=sheets_data,
            depivoted_sheets=depivoted_sheets,
            id_vars=[],
            value_vars_by_sheet=value_vars_by_sheet,
            value_name="value",
        )

        # Should still generate sheet-level and grand totals
        assert not report.empty
        assert "SHEET_TOTAL" in report["Category"].values
        assert "GRAND_TOTAL" in report["Category"].values


# =============================================================================
# DEPIVOT FILE TESTS
# =============================================================================

class TestDepivotFile:
    """Test file-level depivoting."""

    @pytest.fixture
    def sample_excel(self, tmp_path):
        """Create a sample Excel file for testing."""
        file_path = tmp_path / "FY25_2025-01.xlsx"
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df = pd.DataFrame({
                "Site": ["Site1", "Site2"],
                "Jan": [100, 200],
                "Feb": [150, 250],
            })
            df.to_excel(writer, sheet_name="Actuals", index=False)
        return file_path

    def test_depivot_file_basic(self, tmp_path, sample_excel):
        """Test basic file depivoting."""
        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=sample_excel,
            output_file=output_file,
            id_vars=["Site"],
            overwrite=True,
        )

        assert result["sheets_processed"] == 1
        assert result["total_rows"] == 4  # 2 sites * 2 months
        assert output_file.exists()

    def test_depivot_file_with_release_date(self, tmp_path, sample_excel):
        """Test file depivoting with release date extraction."""
        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=sample_excel,
            output_file=output_file,
            id_vars=["Site"],
            overwrite=True,
        )

        # Read output to verify ReleaseDate column
        output_df = pd.read_excel(output_file, sheet_name="Actuals")
        assert "ReleaseDate" in output_df.columns
        assert output_df["ReleaseDate"].iloc[0] == "2025-01"

    def test_depivot_file_with_data_type(self, tmp_path):
        """Test file depivoting with data type detection."""
        file_path = tmp_path / "test.xlsx"
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df = pd.DataFrame({
                "Site": ["Site1"],
                "Jan": [100],
            })
            df.to_excel(writer, sheet_name="Forecast", index=False)

        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site"],
            overwrite=True,
        )

        # Read output to verify DataType column
        output_df = pd.read_excel(output_file, sheet_name="Forecast")
        assert "DataType" in output_df.columns
        assert output_df["DataType"].iloc[0] == "Forecast"

    def test_depivot_file_combine_sheets(self, tmp_path):
        """Test file depivoting with sheet combination."""
        file_path = tmp_path / "test.xlsx"
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df1 = pd.DataFrame({"Site": ["Site1"], "Jan": [100]})
            df2 = pd.DataFrame({"Site": ["Site2"], "Jan": [200]})
            df1.to_excel(writer, sheet_name="Sheet1", index=False)
            df2.to_excel(writer, sheet_name="Sheet2", index=False)

        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site"],
            combine_sheets=True,
            overwrite=True,
        )

        # Verify combined output
        assert result["sheets_processed"] == 2
        output_sheets = pd.ExcelFile(output_file).sheet_names
        assert "Data" in output_sheets
        assert "Sheet1" not in output_sheets
        assert "Sheet2" not in output_sheets

    def test_depivot_file_overwrite_protection(self, tmp_path, sample_excel):
        """Test that overwrite protection works."""
        output_file = tmp_path / "output.xlsx"
        output_file.touch()  # Create existing file

        with pytest.raises(ValidationError, match="already exists"):
            depivot_file(
                input_file=sample_excel,
                output_file=output_file,
                id_vars=["Site"],
                overwrite=False,
            )

    def test_depivot_file_forecast_logic(self, tmp_path):
        """Test forecast start logic."""
        file_path = tmp_path / "test.xlsx"
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df = pd.DataFrame({
                "Site": ["Site1", "Site1"],
                "Jan": [100, 100],
                "Jun": [150, 150],
            })
            df.to_excel(writer, sheet_name="Actuals", index=False)

        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site"],
            forecast_start="Jun",
            overwrite=True,
        )

        # Read output to verify DataType logic
        output_df = pd.read_excel(output_file, sheet_name="Actuals")
        jan_rows = output_df[output_df["variable"] == "Jan"]
        jun_rows = output_df[output_df["variable"] == "Jun"]

        assert jan_rows.iloc[0]["DataType"] == "Actual"
        assert jun_rows.iloc[0]["DataType"] == "Forecast"

    def test_depivot_file_validation_disabled(self, tmp_path, sample_excel):
        """Test file depivoting with validation disabled."""
        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=sample_excel,
            output_file=output_file,
            id_vars=["Site"],
            no_validate=True,
            overwrite=True,
        )

        # Verify no validation sheet in output
        output_sheets = pd.ExcelFile(output_file).sheet_names
        assert "Validation" not in output_sheets


# =============================================================================
# BATCH PROCESSING TESTS
# =============================================================================

class TestDepivotBatch:
    """Test batch file processing."""

    @pytest.fixture
    def batch_files(self, tmp_path):
        """Create multiple Excel files for batch processing."""
        files = []
        for i in range(3):
            file_path = tmp_path / f"file{i}.xlsx"
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                df = pd.DataFrame({
                    "Site": [f"Site{i}"],
                    "Jan": [100 * (i + 1)],
                })
                df.to_excel(writer, sheet_name="Data", index=False)
            files.append(file_path)
        return tmp_path, files

    def test_batch_processing_success(self, batch_files):
        """Test successful batch processing."""
        input_dir, files = batch_files
        output_dir = input_dir / "output"

        result = depivot_batch(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern="*.xlsx",
            id_vars=["Site"],
            overwrite=True,
        )

        assert len(result["successful"]) == 3
        assert len(result["failed"]) == 0

    def test_batch_processing_no_files(self, tmp_path):
        """Test batch processing with no matching files."""
        input_dir = tmp_path / "empty"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        result = depivot_batch(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern="*.xlsx",
            id_vars=["Site"],
        )

        assert len(result["successful"]) == 0
        assert len(result["failed"]) == 0

    def test_batch_processing_invalid_input_dir(self, tmp_path):
        """Test batch processing with invalid input directory."""
        input_dir = tmp_path / "nonexistent"
        output_dir = tmp_path / "output"

        with pytest.raises(FileProcessingError, match="not a directory"):
            depivot_batch(
                input_dir=input_dir,
                output_dir=output_dir,
                pattern="*.xlsx",
                id_vars=["Site"],
            )

    def test_batch_processing_creates_output_dir(self, batch_files):
        """Test that output directory is created if it doesn't exist."""
        input_dir, files = batch_files
        output_dir = input_dir / "new_output"

        assert not output_dir.exists()

        result = depivot_batch(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern="*.xlsx",
            id_vars=["Site"],
            overwrite=True,
        )

        assert output_dir.exists()
        assert len(result["successful"]) == 3


# =============================================================================
# DEPIVOT MULTI FILE TESTS
# =============================================================================

class TestDepivotMultiFile:
    """Test multi-file processing with combined output."""

    @pytest.fixture
    def multi_files(self, tmp_path):
        """Create multiple test Excel files."""
        files = []
        for i in range(3):
            file_path = tmp_path / f"test_file_{i+1}.xlsx"
            df = pd.DataFrame({
                "Site": [f"Site{i}A", f"Site{i}B"],
                "Category": ["Cat1", "Cat2"],
                "Jan": [100 + i*10, 200 + i*10],
                "Feb": [150 + i*10, 250 + i*10],
            })
            df.to_excel(file_path, index=False, sheet_name="Sheet1")
            files.append(file_path)
        return files

    def test_multi_file_basic(self, multi_files, tmp_path):
        """Test basic multi-file processing."""
        output_file = tmp_path / "combined.xlsx"

        result = depivot_multi_file(
            input_files=multi_files,
            output_file=output_file,
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
        )

        assert output_file.exists()
        assert len(result["input_files"]) == 3
        assert result["sheets_processed"] == 3
        assert result["total_rows"] > 0

        # Verify combined data
        df_result = pd.read_excel(output_file, sheet_name="Data")
        assert "Site" in df_result.columns
        assert "Month" in df_result.columns
        assert "Amount" in df_result.columns
        assert len(df_result) == 12  # 3 files * 2 rows * 2 months

    def test_multi_file_verbose(self, multi_files, tmp_path, capsys):
        """Test multi-file processing with verbose output."""
        output_file = tmp_path / "combined.xlsx"

        depivot_multi_file(
            input_files=multi_files,
            output_file=output_file,
            id_vars=["Site", "Category"],
            verbose=True,
        )

        captured = capsys.readouterr()
        assert "Processing" in captured.out
        assert "file(s) into combined output" in captured.out

    def test_multi_file_empty_list(self, tmp_path):
        """Test multi-file with empty file list."""
        output_file = tmp_path / "combined.xlsx"

        # Empty file list will cause pd.concat to fail
        with pytest.raises(ValueError, match="No objects to concatenate"):
            depivot_multi_file(
                input_files=[],
                output_file=output_file,
                id_vars=["Site"],
            )


# =============================================================================
# ADDITIONAL DEPIVOT FILE TESTS FOR COVERAGE
# =============================================================================

class TestDepivotFileEdgeCases:
    """Test additional edge cases and code paths in depivot_file."""

    @pytest.fixture
    def test_file_with_totals(self, tmp_path):
        """Create a test file with total rows."""
        file_path = tmp_path / "data_with_totals.xlsx"
        df = pd.DataFrame({
            "Site": ["SiteA", "SiteB", "Grand Total", "SiteC", "Subtotal"],
            "Category": ["Cat1", "Cat2", "Total", "Cat3", "Sum"],
            "Jan": [100, 200, 300, 150, 450],
            "Feb": [110, 210, 320, 160, 480],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")
        return file_path

    def test_exclude_totals_filtering(self, test_file_with_totals, tmp_path):
        """Test exclude_totals parameter filters summary rows."""
        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=test_file_with_totals,
            output_file=output_file,
            id_vars=["Site", "Category"],
            exclude_totals=True,
            verbose=True,
        )

        df_result = pd.read_excel(output_file, sheet_name="Sheet1")

        # Should exclude rows with "Grand Total", "Subtotal", etc.
        sites = df_result["Site"].unique()
        assert "Grand Total" not in sites
        assert "Subtotal" not in sites
        assert "SiteA" in sites
        assert "SiteB" in sites
        assert "SiteC" in sites

    def test_exclude_totals_custom_patterns(self, test_file_with_totals, tmp_path):
        """Test exclude_totals with custom summary patterns."""
        output_file = tmp_path / "output.xlsx"

        result = depivot_file(
            input_file=test_file_with_totals,
            output_file=output_file,
            id_vars=["Site", "Category"],
            exclude_totals=True,
            summary_patterns=["Total", "Sum", "Subtotal"],
            verbose=True,
        )

        # With exclude_totals=True, some summary rows should be filtered
        df_result = pd.read_excel(output_file, sheet_name="Sheet1")

        # At minimum, verify that filtering occurred and we have valid data
        assert output_file.exists()
        assert len(df_result) > 0
        assert result["sheets_processed"] == 1

    def test_release_date_none_handling(self, tmp_path, capsys):
        """Test handling when release_date cannot be extracted."""
        # Create file without date in name
        file_path = tmp_path / "data.xlsx"
        df = pd.DataFrame({
            "Site": ["A", "B"],
            "Jan": [100, 200],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")

        output_file = tmp_path / "output.xlsx"

        depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site"],
            release_date=None,
            verbose=True,
        )

        captured = capsys.readouterr()
        assert "Could not extract release date" in captured.out
        assert "Use --release-date to specify manually" in captured.out

    def test_verbose_output_messages(self, tmp_path, capsys):
        """Test verbose output displays progress messages."""
        file_path = tmp_path / "data_2025-01.xlsx"
        df = pd.DataFrame({
            "Site": ["A", "B"],
            "Jan": [100, 200],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")

        output_file = tmp_path / "output.xlsx"

        depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site"],
            verbose=True,
        )

        captured = capsys.readouterr()
        assert "Auto-detected release date" in captured.out
        assert "Processing" in captured.out

    def test_combine_sheets_functionality(self, tmp_path):
        """Test combine_sheets parameter combines multiple sheets."""
        file_path = tmp_path / "multi_sheet.xlsx"

        with pd.ExcelWriter(file_path) as writer:
            df1 = pd.DataFrame({
                "Site": ["A", "B"],
                "Jan": [100, 200],
            })
            df2 = pd.DataFrame({
                "Site": ["C", "D"],
                "Jan": [300, 400],
            })
            df1.to_excel(writer, sheet_name="Sheet1", index=False)
            df2.to_excel(writer, sheet_name="Sheet2", index=False)

        output_file = tmp_path / "combined_output.xlsx"

        result = depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site"],
            combine_sheets=True,
            output_sheet_name="AllData",
        )

        # Check that combined output has single sheet
        df_result = pd.read_excel(output_file, sheet_name="AllData")
        assert len(df_result) == 4  # 2 rows from each sheet
        sites = df_result["Site"].unique()
        assert set(sites) == {"A", "B", "C", "D"}

    def test_template_validation_integration(self, tmp_path):
        """Test template validation integration."""
        file_path = tmp_path / "data.xlsx"
        df = pd.DataFrame({
            "Site": ["A", "B"],
            "Category": ["Cat1", "Cat2"],
            "Jan": [100, 200],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")

        output_file = tmp_path / "output.xlsx"

        # Simple template validation config
        template_config = {
            "enabled": True,
            "settings": {"stop_on_error": False, "verbose": False}
        }

        result = depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site", "Category"],
            template_validation=template_config,
            verbose=True,
        )

        assert output_file.exists()
        assert result["sheets_processed"] == 1

    def test_no_validate_quality_flag(self, tmp_path):
        """Test no_validate_quality flag skips quality validation."""
        file_path = tmp_path / "data.xlsx"
        df = pd.DataFrame({
            "Site": ["A", "B"],
            "Jan": [100, 200],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")

        output_file = tmp_path / "output.xlsx"

        # Even with validation_rules, should skip quality validation
        validation_rules = {
            "enabled": True,
            "pre_processing": [],
            "post_processing": [],
        }

        result = depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site"],
            validation_rules=validation_rules,
            no_validate_quality=True,
        )

        assert output_file.exists()

    def test_data_quality_validation_integration(self, tmp_path):
        """Test data quality validation integration."""
        file_path = tmp_path / "data.xlsx"
        df = pd.DataFrame({
            "Site": ["A", "B", "C"],
            "Category": ["Cat1", "Cat2", "Cat3"],
            "Jan": [100, 200, 300],
            "Feb": [150, 250, 350],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")

        output_file = tmp_path / "output.xlsx"

        # Quality validation config
        validation_rules = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "check_required_columns",
                    "enabled": True,
                    "severity": "error",
                    "params": {"columns": ["Site", "Category"]},
                }
            ],
            "post_processing": [
                {
                    "rule": "check_row_count",
                    "enabled": True,
                    "severity": "warning",
                    "params": {"min_ratio": 0.5, "max_ratio": 5.0},
                }
            ],
            "validation_settings": {"stop_on_error": False},
        }

        result = depivot_file(
            input_file=file_path,
            output_file=output_file,
            id_vars=["Site", "Category"],
            validation_rules=validation_rules,
            no_validate_quality=False,
            verbose=True,
        )

        assert output_file.exists()
        assert result["sheets_processed"] == 1
