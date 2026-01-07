"""Integration tests for validation and SQL upload features."""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from depivot.core import depivot_file, depivot_batch, depivot_multi_file
from depivot.exceptions import TemplateError, DataQualityError, FileProcessingError, DatabaseError


class TestValidationIntegration:
    """Test validation features integrated with depivot_file."""

    def test_template_validation_in_depivot(self, sample_excel_file, temp_dir, template_validation_config):
        """Test template validation runs during depivot."""
        output_file = temp_dir / "output.xlsx"

        result = depivot_file(
            input_file=sample_excel_file,
            output_file=output_file,
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
            template_validation=template_validation_config,
            verbose=False
        )

        assert result["total_rows"] > 0
        assert output_file.exists()

    def test_template_validation_failure(self, excel_file_with_wrong_headers, temp_dir, template_validation_config):
        """Test template validation catches errors."""
        output_file = temp_dir / "output.xlsx"

        with pytest.raises(FileProcessingError):
            depivot_file(
                input_file=excel_file_with_wrong_headers,
                output_file=output_file,
                id_vars=["Site", "Category"],
                template_validation=template_validation_config,
                verbose=False
            )

    def test_validation_disabled(self, sample_excel_file, temp_dir):
        """Test depivot works without validation."""
        output_file = temp_dir / "output.xlsx"

        result = depivot_file(
            input_file=sample_excel_file,
            output_file=output_file,
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
            template_validation=None,
            validation_rules=None,
            verbose=False
        )

        assert result["total_rows"] > 0
        assert output_file.exists()


class TestSQLUploadIntegration:
    """Test SQL upload integration with depivot_file."""

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_file_sql_only(self, mock_fetch, mock_transform, mock_upload, sample_excel_file, temp_dir):
        """Test depivot_file with --sql-only flag."""
        output_file = temp_dir / "output.xlsx"

        # Mock SQL upload functions
        mock_fetch.return_value = {"Site A": "L2_A", "Site B": "L2_B"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A", "L2_B"],
            "Site": ["Site A", "Site B"],
            "Category": ["Cat1", "Cat2"],
            "FiscalYear": [2025, 2025],
            "Period": [1, 2],
            "Actuals": [100.0, 200.0],
            "Status": ["Actual", "Actual"],
        })
        mock_upload.return_value = {"rows_uploaded": 2, "rows_failed": 0}

        result = depivot_file(
            input_file=sample_excel_file,
            output_file=output_file,
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
            sql_only=True,
            sql_connection_string="fake_connection_string",
            sql_table="[dbo].[TestTable]",
            sql_mode="append",
            verbose=True,
        )

        # Verify SQL functions were called
        assert mock_fetch.called
        assert mock_transform.called
        assert mock_upload.called

        # Verify Excel file was NOT created (sql_only mode)
        assert not output_file.exists()

        # Verify result contains SQL upload info
        assert result["sheets_processed"] > 0

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_file_both_excel_and_sql(self, mock_fetch, mock_transform, mock_upload, sample_excel_file, temp_dir):
        """Test depivot_file with --both flag (Excel + SQL)."""
        output_file = temp_dir / "output.xlsx"

        # Mock SQL upload functions
        mock_fetch.return_value = {"Site A": "L2_A", "Site B": "L2_B"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A", "L2_B"],
            "Site": ["Site A", "Site B"],
            "Category": ["Cat1", "Cat2"],
            "FiscalYear": [2025, 2025],
            "Period": [1, 2],
            "Actuals": [100.0, 200.0],
            "Status": ["Actual", "Actual"],
        })
        mock_upload.return_value = {"rows_uploaded": 2, "rows_failed": 0}

        result = depivot_file(
            input_file=sample_excel_file,
            output_file=output_file,
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
            both=True,
            sql_connection_string="fake_connection_string",
            sql_table="[dbo].[TestTable]",
            sql_mode="append",
            verbose=True,
        )

        # Verify SQL functions were called
        assert mock_fetch.called
        assert mock_transform.called
        assert mock_upload.called

        # Verify Excel file WAS created (both mode)
        assert output_file.exists()

        # Verify result
        assert result["sheets_processed"] > 0
        assert result["total_rows"] > 0

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_file_sql_upload_with_replace_mode(self, mock_fetch, mock_transform, mock_upload, sample_excel_file, temp_dir):
        """Test SQL upload with replace mode (truncate table first)."""
        output_file = temp_dir / "output.xlsx"

        # Mock SQL upload functions
        mock_fetch.return_value = {"Site A": "L2_A"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100.0],
            "Status": ["Actual"],
        })
        mock_upload.return_value = {"rows_uploaded": 1, "rows_failed": 0}

        result = depivot_file(
            input_file=sample_excel_file,
            output_file=output_file,
            id_vars=["Site", "Category"],
            sql_only=True,
            sql_connection_string="fake_connection_string",
            sql_table="[dbo].[TestTable]",
            sql_mode="replace",  # Replace mode
            verbose=False,
        )

        # Verify upload was called with correct mode
        assert mock_upload.called
        call_args = mock_upload.call_args
        assert call_args[1]["mode"] == "replace"

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_file_sql_upload_error(self, mock_fetch, mock_transform, mock_upload, sample_excel_file, temp_dir):
        """Test SQL upload error handling."""
        output_file = temp_dir / "output.xlsx"

        # Mock SQL upload to raise an error
        mock_fetch.return_value = {"Site A": "L2_A"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100.0],
            "Status": ["Actual"],
        })
        mock_upload.side_effect = Exception("Database connection failed")

        with pytest.raises(DatabaseError, match="SQL upload failed"):
            depivot_file(
                input_file=sample_excel_file,
                output_file=output_file,
                id_vars=["Site", "Category"],
                sql_only=True,
                sql_connection_string="fake_connection_string",
                sql_table="[dbo].[TestTable]",
                verbose=False,
            )

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_file_excel_only_no_sql(self, mock_fetch, mock_transform, mock_upload, sample_excel_file, temp_dir):
        """Test that SQL upload is NOT called when excel_only mode."""
        output_file = temp_dir / "output.xlsx"

        result = depivot_file(
            input_file=sample_excel_file,
            output_file=output_file,
            id_vars=["Site", "Category"],
            excel_only=True,  # Excel only mode
            verbose=False,
        )

        # Verify SQL functions were NOT called
        assert not mock_fetch.called
        assert not mock_transform.called
        assert not mock_upload.called

        # Verify Excel file was created
        assert output_file.exists()


class TestSQLUploadBatchIntegration:
    """Test SQL upload integration with depivot_batch."""

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_batch_sql_only(self, mock_fetch, mock_transform, mock_upload, temp_dir):
        """Test depivot_batch with SQL upload."""
        # Create test input files
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        for i in range(2):
            file_path = input_dir / f"data_{i}.xlsx"
            df = pd.DataFrame({
                "Site": ["Site A", "Site B"],
                "Category": ["Cat1", "Cat2"],
                "Jan": [100 + i*10, 200 + i*10],
                "Feb": [150 + i*10, 250 + i*10],
            })
            df.to_excel(file_path, index=False, sheet_name="Sheet1")

        # Mock SQL upload functions
        mock_fetch.return_value = {"Site A": "L2_A", "Site B": "L2_B"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A", "L2_B"],
            "Site": ["Site A", "Site B"],
            "Category": ["Cat1", "Cat2"],
            "FiscalYear": [2025, 2025],
            "Period": [1, 2],
            "Actuals": [100.0, 200.0],
            "Status": ["Actual", "Actual"],
        })
        mock_upload.return_value = {"rows_uploaded": 2, "rows_failed": 0}

        result = depivot_batch(
            input_dir=input_dir,
            output_dir=output_dir,
            pattern="*.xlsx",
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
            sql_only=True,
            sql_connection_string="fake_connection_string",
            sql_table="[dbo].[TestTable]",
            sql_mode="append",
            verbose=True,
        )

        # Verify batch processing succeeded
        assert len(result["successful"]) == 2
        assert len(result["failed"]) == 0

        # Verify SQL functions were called (once per file)
        assert mock_fetch.call_count == 2
        assert mock_transform.call_count == 2
        assert mock_upload.call_count == 2

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_batch_both_excel_and_sql(self, mock_fetch, mock_transform, mock_upload, temp_dir):
        """Test depivot_batch with both Excel and SQL output."""
        # Create test input files
        input_dir = temp_dir / "input"
        input_dir.mkdir()
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        file_path = input_dir / "data.xlsx"
        df = pd.DataFrame({
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "Jan": [100],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")

        # Mock SQL upload functions
        mock_fetch.return_value = {"Site A": "L2_A"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100.0],
            "Status": ["Actual"],
        })
        mock_upload.return_value = {"rows_uploaded": 1, "rows_failed": 0}

        result = depivot_batch(
            input_dir=input_dir,
            output_dir=output_dir,
            id_vars=["Site", "Category"],
            both=True,  # Both Excel and SQL
            sql_connection_string="fake_connection_string",
            sql_table="[dbo].[TestTable]",
            verbose=False,
        )

        # Verify processing succeeded
        assert len(result["successful"]) == 1

        # Verify SQL upload was called
        assert mock_upload.called

        # Verify Excel files were created
        output_files = list(output_dir.glob("*.xlsx"))
        assert len(output_files) == 1


class TestSQLUploadMultiFileIntegration:
    """Test SQL upload integration with depivot_multi_file."""

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_multi_file_sql_only(self, mock_fetch, mock_transform, mock_upload, temp_dir):
        """Test depivot_multi_file with SQL upload (wildcard processing)."""
        # Create multiple test input files
        input_files = []
        for i in range(2):
            file_path = temp_dir / f"data_{i}.xlsx"
            df = pd.DataFrame({
                "Site": ["Site A", "Site B"],
                "Category": ["Cat1", "Cat2"],
                "Jan": [100 + i*10, 200 + i*10],
                "Feb": [150 + i*10, 250 + i*10],
            })
            df.to_excel(file_path, index=False, sheet_name="Sheet1")
            input_files.append(file_path)

        output_file = temp_dir / "output.xlsx"

        # Mock SQL upload functions
        mock_fetch.return_value = {"Site A": "L2_A", "Site B": "L2_B"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A", "L2_B"],
            "Site": ["Site A", "Site B"],
            "Category": ["Cat1", "Cat2"],
            "FiscalYear": [2025, 2025],
            "Period": [1, 2],
            "Actuals": [100.0, 200.0],
            "Status": ["Actual", "Actual"],
        })
        mock_upload.return_value = {"rows_uploaded": 2, "rows_failed": 0}

        result = depivot_multi_file(
            input_files=input_files,
            output_file=output_file,
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
            sql_only=True,
            sql_connection_string="fake_connection_string",
            sql_table="[dbo].[TestTable]",
            sql_mode="append",
            verbose=True,
        )

        # Verify SQL functions were called
        assert mock_fetch.called
        assert mock_transform.called
        assert mock_upload.called

        # Verify Excel file was NOT created (sql_only mode)
        assert not output_file.exists()

        # Verify result contains processing info
        assert result["sheets_processed"] > 0
        assert result["total_rows"] > 0
        assert len(result["input_files"]) == 2

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_multi_file_both_excel_and_sql(self, mock_fetch, mock_transform, mock_upload, temp_dir):
        """Test depivot_multi_file with both Excel and SQL output."""
        # Create multiple test input files
        input_files = []
        for i in range(2):
            file_path = temp_dir / f"data_{i}.xlsx"
            df = pd.DataFrame({
                "Site": ["Site A"],
                "Category": ["Cat1"],
                "Jan": [100 + i*10],
            })
            df.to_excel(file_path, index=False, sheet_name="Sheet1")
            input_files.append(file_path)

        output_file = temp_dir / "output.xlsx"

        # Mock SQL upload functions
        mock_fetch.return_value = {"Site A": "L2_A"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100.0],
            "Status": ["Actual"],
        })
        mock_upload.return_value = {"rows_uploaded": 1, "rows_failed": 0}

        result = depivot_multi_file(
            input_files=input_files,
            output_file=output_file,
            id_vars=["Site", "Category"],
            var_name="Month",
            value_name="Amount",
            both=True,
            sql_connection_string="fake_connection_string",
            sql_table="[dbo].[TestTable]",
            sql_mode="replace",
            verbose=False,
        )

        # Verify SQL functions were called
        assert mock_fetch.called
        assert mock_transform.called
        assert mock_upload.called

        # Verify Excel file WAS created (both mode)
        assert output_file.exists()

        # Verify result
        assert result["sheets_processed"] > 0
        assert result["total_rows"] > 0

    @patch('depivot.sql_upload.upload_to_sql_server')
    @patch('depivot.sql_upload.transform_dataframe_for_sql')
    @patch('depivot.sql_upload.fetch_l2_proj_mapping')
    def test_depivot_multi_file_sql_error(self, mock_fetch, mock_transform, mock_upload, temp_dir):
        """Test depivot_multi_file SQL upload error handling."""
        # Create test input file
        file_path = temp_dir / "data.xlsx"
        df = pd.DataFrame({
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "Jan": [100],
        })
        df.to_excel(file_path, index=False, sheet_name="Sheet1")

        output_file = temp_dir / "output.xlsx"

        # Mock SQL upload to raise an error
        mock_fetch.return_value = {"Site A": "L2_A"}
        mock_transform.return_value = pd.DataFrame({
            "L2_Proj": ["L2_A"],
            "Site": ["Site A"],
            "Category": ["Cat1"],
            "FiscalYear": [2025],
            "Period": [1],
            "Actuals": [100.0],
            "Status": ["Actual"],
        })
        mock_upload.side_effect = Exception("Database connection failed")

        with pytest.raises(DatabaseError, match="SQL upload failed"):
            depivot_multi_file(
                input_files=[file_path],
                output_file=output_file,
                id_vars=["Site", "Category"],
                sql_only=True,
                sql_connection_string="fake_connection_string",
                sql_table="[dbo].[TestTable]",
                verbose=False,
            )
