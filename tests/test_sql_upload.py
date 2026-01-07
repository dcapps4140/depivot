"""Tests for SQL Server upload functionality."""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from depivot.sql_upload import (
    convert_month_to_period,
    extract_fiscal_year,
    fetch_l2_proj_mapping,
    transform_dataframe_for_sql,
    upload_to_sql_server,
    validate_sql_connection,
    MONTH_TO_PERIOD,
)
from depivot.exceptions import ColumnError, DatabaseError


class TestConvertMonthToPeriod:
    """Test month name to period number conversion."""

    def test_convert_full_month_names(self):
        """Test conversion of full month names."""
        assert convert_month_to_period("January") == 1
        assert convert_month_to_period("February") == 2
        assert convert_month_to_period("March") == 3
        assert convert_month_to_period("April") == 4
        assert convert_month_to_period("May") == 5
        assert convert_month_to_period("June") == 6
        assert convert_month_to_period("July") == 7
        assert convert_month_to_period("August") == 8
        assert convert_month_to_period("September") == 9
        assert convert_month_to_period("October") == 10
        assert convert_month_to_period("November") == 11
        assert convert_month_to_period("December") == 12

    def test_convert_abbreviated_month_names(self):
        """Test conversion of abbreviated month names."""
        assert convert_month_to_period("Jan") == 1
        assert convert_month_to_period("Feb") == 2
        assert convert_month_to_period("Mar") == 3
        assert convert_month_to_period("Apr") == 4
        assert convert_month_to_period("Jun") == 6
        assert convert_month_to_period("Jul") == 7
        assert convert_month_to_period("Aug") == 8
        assert convert_month_to_period("Sep") == 9
        assert convert_month_to_period("Oct") == 10
        assert convert_month_to_period("Nov") == 11
        assert convert_month_to_period("Dec") == 12

    def test_convert_case_insensitive(self):
        """Test case-insensitive conversion."""
        assert convert_month_to_period("JANUARY") == 1
        assert convert_month_to_period("january") == 1
        assert convert_month_to_period("JaN") == 1
        assert convert_month_to_period("dec") == 12
        assert convert_month_to_period("DEC") == 12

    def test_convert_with_whitespace(self):
        """Test conversion with leading/trailing whitespace."""
        assert convert_month_to_period("  January  ") == 1
        assert convert_month_to_period(" Feb ") == 2
        assert convert_month_to_period("Mar\t") == 3

    def test_convert_september_variant(self):
        """Test September abbreviation variants."""
        assert convert_month_to_period("Sep") == 9
        assert convert_month_to_period("Sept") == 9
        assert convert_month_to_period("September") == 9

    def test_convert_invalid_month(self):
        """Test error on invalid month name."""
        with pytest.raises(ValueError, match="Unrecognized month name"):
            convert_month_to_period("Invalid")

        with pytest.raises(ValueError, match="Unrecognized month name"):
            convert_month_to_period("Month13")

        with pytest.raises(ValueError, match="Unrecognized month name"):
            convert_month_to_period("")

    def test_convert_nan_value(self):
        """Test error on NaN value."""
        with pytest.raises(ValueError, match="Month value is NaN"):
            convert_month_to_period(pd.NA)

        with pytest.raises(ValueError, match="Month value is NaN"):
            convert_month_to_period(float('nan'))

    def test_month_to_period_constant(self):
        """Test MONTH_TO_PERIOD constant has all expected keys."""
        assert len(MONTH_TO_PERIOD) > 0
        assert "jan" in MONTH_TO_PERIOD
        assert "january" in MONTH_TO_PERIOD
        assert "dec" in MONTH_TO_PERIOD
        assert "december" in MONTH_TO_PERIOD


class TestExtractFiscalYear:
    """Test fiscal year extraction from release date."""

    def test_extract_year_yyyy_mm_format(self):
        """Test extraction from YYYY-MM format."""
        assert extract_fiscal_year("2025-02") == 2025
        assert extract_fiscal_year("2024-12") == 2024
        assert extract_fiscal_year("2023-01") == 2023

    def test_extract_year_yyyy_underscore_mm_format(self):
        """Test extraction from YYYY_MM format."""
        assert extract_fiscal_year("2025_02") == 2025
        assert extract_fiscal_year("2024_12") == 2024

    def test_extract_year_with_whitespace(self):
        """Test extraction with whitespace."""
        assert extract_fiscal_year("  2025-02  ") == 2025
        assert extract_fiscal_year(" 2024-12 ") == 2024

    def test_extract_year_invalid_format(self):
        """Test error on invalid format."""
        with pytest.raises(ValueError, match="Invalid ReleaseDate format"):
            extract_fiscal_year("invalid")

        with pytest.raises(ValueError, match="Invalid ReleaseDate format"):
            extract_fiscal_year("not-a-year")

        with pytest.raises(ValueError, match="Invalid ReleaseDate format"):
            extract_fiscal_year("abc-12")

    def test_extract_year_nan_value(self):
        """Test error on NaN value."""
        with pytest.raises(ValueError, match="ReleaseDate is NaN"):
            extract_fiscal_year(pd.NA)

        with pytest.raises(ValueError, match="ReleaseDate is NaN"):
            extract_fiscal_year(float('nan'))


class TestFetchL2ProjMapping:
    """Test L2_Proj mapping fetch from database."""

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_fetch_mapping_success(self, mock_connect):
        """Test successful mapping fetch."""
        # Mock database connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Site A", "L2_A"),
            ("Site B", "L2_B"),
            ("Site C", "L2_C"),
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = fetch_l2_proj_mapping("fake_connection_string")

        assert result == {
            "Site A": "L2_A",
            "Site B": "L2_B",
            "Site C": "L2_C",
        }
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_fetch_mapping_custom_table(self, mock_connect):
        """Test mapping fetch with custom lookup table."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        fetch_l2_proj_mapping("fake_connection_string", "[custom].[table]")

        # Verify custom table name is used in query
        call_args = mock_cursor.execute.call_args[0][0]
        assert "[custom].[table]" in call_args

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_fetch_mapping_empty_result(self, mock_connect):
        """Test mapping fetch with no results."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        result = fetch_l2_proj_mapping("fake_connection_string")

        assert result == {}

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_fetch_mapping_database_error(self, mock_connect):
        """Test error handling for database failures."""
        import pyodbc
        mock_connect.side_effect = pyodbc.Error("Connection failed")

        with pytest.raises(DatabaseError, match="Failed to fetch L2_Proj mapping"):
            fetch_l2_proj_mapping("fake_connection_string")


class TestTransformDataFrameForSQL:
    """Test DataFrame transformation for SQL upload."""

    def test_transform_basic(self):
        """Test basic transformation."""
        df = pd.DataFrame({
            "Site": ["Site A", "Site B"],
            "Category": ["Cat1", "Cat2"],
            "Month": ["Jan", "Feb"],
            "Amount": [100, 200],
            "ReleaseDate": ["2025-02", "2025-02"],
            "DataType": ["Actual", "Budget"],
        })
        l2_mapping = {"Site A": "L2_A", "Site B": "L2_B"}

        result = transform_dataframe_for_sql(df, l2_mapping, "Month", "Amount")

        assert list(result.columns) == ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status", "ReleaseDate", "ReportPeriod"]
        assert result["Period"].tolist() == [1, 2]
        assert result["FiscalYear"].tolist() == [2025, 2025]
        assert result["Actuals"].tolist() == [100, 200]
        assert result["Status"].tolist() == ["Actual", "Budget"]
        assert result["L2_Proj"].tolist() == ["L2_A", "L2_B"]
        assert result["ReleaseDate"].tolist() == ["2025-02", "2025-02"]
        assert result["ReportPeriod"].tolist() == [2, 2]

    def test_transform_missing_required_columns(self):
        """Test error when required columns are missing."""
        df = pd.DataFrame({
            "Site": ["Site A"],
            "Month": ["Jan"],
        })
        l2_mapping = {}

        with pytest.raises(ColumnError, match="Required columns missing"):
            transform_dataframe_for_sql(df, l2_mapping)

    def test_transform_invalid_month(self):
        """Test error on invalid month values."""
        df = pd.DataFrame({
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "Month": ["InvalidMonth"],
            "Amount": [100],
        })
        l2_mapping = {}

        with pytest.raises(ColumnError, match="Invalid month values"):
            transform_dataframe_for_sql(df, l2_mapping)

    def test_transform_without_release_date(self):
        """Test transformation without ReleaseDate column."""
        df = pd.DataFrame({
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "Month": ["Jan"],
            "Amount": [100],
        })
        l2_mapping = {"Site A": "L2_A"}

        result = transform_dataframe_for_sql(df, l2_mapping, verbose=True)

        assert result["FiscalYear"].isna().all()

    def test_transform_without_data_type(self):
        """Test transformation without DataType column."""
        df = pd.DataFrame({
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "Month": ["Jan"],
            "Amount": [100],
        })
        l2_mapping = {"Site A": "L2_A"}

        result = transform_dataframe_for_sql(df, l2_mapping, verbose=True)

        assert result["Status"].isna().all()

    def test_transform_missing_l2_mapping(self, capsys):
        """Test warning for missing L2_Proj mapping."""
        df = pd.DataFrame({
            "Site": ["Site A", "Site B", "Site C"],
            "Category": ["Cat1", "Cat2", "Cat3"],
            "Month": ["Jan", "Feb", "Mar"],
            "Amount": [100, 200, 300],
        })
        l2_mapping = {"Site A": "L2_A"}  # Missing Site B and C

        result = transform_dataframe_for_sql(df, l2_mapping)

        # Sites B and C should have NaN for L2_Proj
        assert result.loc[result["Site"] == "Site A", "L2_Proj"].iloc[0] == "L2_A"
        assert pd.isna(result.loc[result["Site"] == "Site B", "L2_Proj"].iloc[0])
        assert pd.isna(result.loc[result["Site"] == "Site C", "L2_Proj"].iloc[0])

    def test_transform_custom_column_names(self):
        """Test transformation with custom column names."""
        df = pd.DataFrame({
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "Period": ["Jun"],
            "Value": [150],
        })
        l2_mapping = {"Site A": "L2_A"}

        result = transform_dataframe_for_sql(df, l2_mapping, var_name="Period", value_name="Value")

        assert result["Period"].iloc[0] == 6
        assert result["Actuals"].iloc[0] == 150

    def test_transform_all_months(self):
        """Test transformation with all 12 months."""
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        df = pd.DataFrame({
            "Site": ["Site A"] * 12,
            "Category": ["Cat1"] * 12,
            "Month": months,
            "Amount": range(100, 112),
        })
        l2_mapping = {"Site A": "L2_A"}

        result = transform_dataframe_for_sql(df, l2_mapping)

        assert result["Period"].tolist() == list(range(1, 13))


class TestUploadToSQLServer:
    """Test SQL Server upload functionality."""

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_upload_append_mode(self, mock_connect):
        """Test upload in append mode."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        df = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100],
            "Status": ["Actual"],
            "ReleaseDate": ["2025-03"],
            "ReportPeriod": [3],
        })

        result = upload_to_sql_server(df, "fake_connection", "[dbo].[TestTable]", mode="append")

        assert result["rows_uploaded"] == 1
        assert result["rows_failed"] == 0
        assert result["table"] == "[dbo].[TestTable]"
        assert result["mode"] == "append"

        # Verify executemany was called
        mock_cursor.executemany.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_upload_replace_mode(self, mock_connect):
        """Test upload in replace mode (truncate first)."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        df = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100],
            "Status": ["Actual"],
            "ReleaseDate": ["2025-03"],
            "ReportPeriod": [3],
        })

        result = upload_to_sql_server(df, "fake_connection", "[dbo].[TestTable]", mode="replace", verbose=True)

        assert result["rows_uploaded"] == 1
        assert result["mode"] == "replace"

        # Verify TRUNCATE was called
        truncate_call = mock_cursor.execute.call_args_list[0][0][0]
        assert "TRUNCATE TABLE" in truncate_call

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_upload_multiple_rows(self, mock_connect):
        """Test upload with multiple rows."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        df = pd.DataFrame({
            "L2_Proj": ["L2_A", "L2_B", "L2_C"],
            "Site": ["Site A", "Site B", "Site C"],
            "Category": ["Cat1", "Cat2", "Cat3"],
            "FiscalYear": [2025, 2025, 2025],
            "Period": [1, 2, 3],
            "Actuals": [100, 200, 300],
            "Status": ["Actual", "Budget", "Forecast"],
            "ReleaseDate": ["2025-03", "2025-03", "2025-03"],
            "ReportPeriod": [3, 3, 3],
        })

        result = upload_to_sql_server(df, "fake_connection", "[dbo].[TestTable]")

        assert result["rows_uploaded"] == 3

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_upload_with_null_values(self, mock_connect):
        """Test upload with NULL values."""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        df = pd.DataFrame({
            "L2_Proj": [None],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [None],
            "Period": [1],
            "Actuals": [100],
            "Status": [None],
            "ReleaseDate": [None],
            "ReportPeriod": [None],
        })

        result = upload_to_sql_server(df, "fake_connection", "[dbo].[TestTable]")

        assert result["rows_uploaded"] == 1

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_upload_database_error(self, mock_connect):
        """Test error handling for upload failures."""
        import pyodbc
        mock_cursor = MagicMock()
        mock_cursor.executemany.side_effect = pyodbc.Error("Insert failed")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        df = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100],
            "Status": ["Actual"],
            "ReleaseDate": ["2025-03"],
            "ReportPeriod": [3],
        })

        with pytest.raises(DatabaseError, match="SQL Server upload failed"):
            upload_to_sql_server(df, "fake_connection", "[dbo].[TestTable]")

        # Verify rollback was called
        mock_conn.rollback.assert_called_once()


class TestValidateSQLConnection:
    """Test SQL connection validation."""

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_validate_connection_success(self, mock_connect):
        """Test successful connection validation."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        result = validate_sql_connection("fake_connection_string")

        assert result is True
        mock_conn.close.assert_called_once()

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_validate_connection_failure(self, mock_connect):
        """Test connection validation failure."""
        import pyodbc
        mock_connect.side_effect = pyodbc.Error("Connection failed")

        with pytest.raises(DatabaseError, match="Cannot connect to SQL Server"):
            validate_sql_connection("fake_connection_string")


class TestIntegration:
    """Integration tests for SQL upload workflow."""

    @patch('depivot.sql_upload.pyodbc.connect')
    def test_full_workflow(self, mock_connect):
        """Test complete workflow: transform and upload."""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("Site A", "L2_A"), ("Site B", "L2_B")]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Step 1: Fetch L2 mapping
        l2_mapping = fetch_l2_proj_mapping("fake_connection")
        assert len(l2_mapping) == 2

        # Step 2: Transform DataFrame
        df = pd.DataFrame({
            "Site": ["Site A", "Site B"],
            "Category": ["Cat1", "Cat2"],
            "Month": ["Jan", "Feb"],
            "Amount": [100, 200],
            "ReleaseDate": ["2025-02", "2025-03"],
            "DataType": ["Actual", "Budget"],
        })

        sql_df = transform_dataframe_for_sql(df, l2_mapping)
        assert len(sql_df) == 2
        assert list(sql_df.columns) == ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status", "ReleaseDate", "ReportPeriod"]

        # Step 3: Upload to SQL Server
        result = upload_to_sql_server(sql_df, "fake_connection", "[dbo].[TestTable]")
        assert result["rows_uploaded"] == 2
        assert result["rows_failed"] == 0
