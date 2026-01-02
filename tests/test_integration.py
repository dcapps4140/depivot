"""Integration tests for validation features."""
import pytest
import pandas as pd
from pathlib import Path
from depivot.core import depivot_file
from depivot.exceptions import TemplateError, DataQualityError, FileProcessingError


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
