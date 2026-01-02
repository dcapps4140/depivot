"""Tests for Excel template validation."""
import pytest
import pandas as pd
from pathlib import Path

from depivot.template_validators import TemplateValidator
from depivot.exceptions import TemplateError


class TestTemplateValidator:
    """Tests for TemplateValidator class."""

    def test_validator_initialization(self, template_validation_config):
        """Test TemplateValidator initializes correctly."""
        validator = TemplateValidator(template_validation_config)
        
        assert validator.enabled is True
        assert validator.stop_on_error is True
        assert len(validator.file_structure_checks) == 1
        assert len(validator.sheet_template_checks) == 1
        assert len(validator.dataframe_template_checks) == 1

    def test_validator_disabled(self):
        """Test validator can be disabled."""
        config = {"enabled": False}
        validator = TemplateValidator(config)
        
        assert validator.enabled is False


class TestFileStructureValidation:
    """Tests for file structure validation (Phase 1)."""

    def test_expected_sheets_pass(self, sample_excel_file, template_validation_config):
        """Test expected sheets validation passes with correct sheet."""
        validator = TemplateValidator(template_validation_config)
        
        # Should not raise exception
        validator.validate_file_structure(sample_excel_file)

    def test_expected_sheets_fail(self, sample_excel_file):
        """Test expected sheets validation fails with missing sheet."""
        config = {
            "enabled": True,
            "file_structure": [
                {
                    "check": "expected_sheets",
                    "enabled": True,
                    "severity": "error",
                    "params": {
                        "required_sheets": ["Nonexistent Sheet"],
                        "allow_extra_sheets": True,
                    },
                    "message": "Required sheet not found"
                }
            ],
            "sheet_template": [],
            "dataframe_template": [],
            "settings": {}
        }
        validator = TemplateValidator(config)
        
        with pytest.raises(TemplateError, match="Required sheet not found"):
            validator.validate_file_structure(sample_excel_file)


class TestSheetTemplateValidation:
    """Tests for sheet template validation (Phase 2)."""

    def test_header_row_validation_pass(self, sample_excel_file, template_validation_config):
        """Test header row validation passes with correct headers."""
        validator = TemplateValidator(template_validation_config)
        
        # Should not raise exception
        validator.validate_sheet_template(sample_excel_file, "Test Sheet")

    def test_merged_cells_detection(self, excel_file_with_merged_cells):
        """Test merged cells are detected."""
        config = {
            "enabled": True,
            "file_structure": [],
            "sheet_template": [
                {
                    "check": "merged_cells",
                    "enabled": True,
                    "severity": "error",
                    "params": {
                        "allowed": False,
                    },
                    "message": "Merged cells detected"
                }
            ],
            "dataframe_template": [],
            "settings": {}
        }
        validator = TemplateValidator(config)
        
        with pytest.raises(TemplateError, match="Merged cells detected"):
            validator.validate_sheet_template(excel_file_with_merged_cells, "Test Sheet")


class TestDataFrameValidation:
    """Tests for DataFrame validation (Phase 3)."""

    def test_required_columns_pass(self, sample_dataframe, template_validation_config):
        """Test required columns validation passes."""
        validator = TemplateValidator(template_validation_config)
        
        # Should not raise exception
        validator.validate_dataframe_template(sample_dataframe, "Test Sheet")

    def test_required_columns_fail(self, sample_dataframe):
        """Test required columns validation fails with missing columns."""
        config = {
            "enabled": True,
            "file_structure": [],
            "sheet_template": [],
            "dataframe_template": [
                {
                    "check": "required_columns",
                    "enabled": True,
                    "severity": "error",
                    "params": {
                        "columns": ["Site", "Category", "Nonexistent"],
                    },
                    "message": "Required columns missing"
                }
            ],
            "settings": {}
        }
        validator = TemplateValidator(config)
        
        with pytest.raises(TemplateError, match="Required columns missing"):
            validator.validate_dataframe_template(sample_dataframe, "Test Sheet")
