"""Tests for data quality validation."""
import pytest
import pandas as pd
from pathlib import Path
from depivot.data_quality import ValidationEngine, ValidationContext
from depivot.exceptions import DataQualityError


class TestValidationEngine:
    def test_engine_initialization(self, data_quality_config):
        engine = ValidationEngine(data_quality_config)
        assert engine.enabled is True
        assert len(engine.pre_processing_rules) >= 1
        assert len(engine.post_processing_rules) >= 1


class TestNullValuesCheck:
    def test_null_values_pass(self, sample_dataframe):
        config = {
            "enabled": True,
            "pre_processing": [{
                "rule": "check_null_values",
                "enabled": True,
                "severity": "warning",
                "params": {"columns": ["Site"], "threshold": 0.5},
                "message": "Too many NULLs"
            }],
            "post_processing": [],
            "validation_settings": {}
        }
        engine = ValidationEngine(config)
        context = ValidationContext(
            df=sample_dataframe,
            sheet_name="Test",
            input_file=Path("test.xlsx"),
            id_vars=["Site"],
            value_vars=["Jan"],
            var_name="Month",
            value_name="Amount"
        )
        results = engine.run_pre_processing(context)
        assert len(results) > 0


class TestDuplicatesCheck:
    def test_duplicates_fail(self, dataframe_with_duplicates):
        config = {
            "enabled": True,
            "pre_processing": [{
                "rule": "check_duplicates",
                "enabled": True,
                "severity": "error",
                "params": {"key_columns": ["Site", "Category"]},
                "message": "Duplicates found"
            }],
            "post_processing": [],
            "validation_settings": {}
        }
        engine = ValidationEngine(config)
        context = ValidationContext(
            df=dataframe_with_duplicates,
            sheet_name="Test",
            input_file=Path("test.xlsx"),
            id_vars=["Site"],
            value_vars=["Jan"],
            var_name="Month",
            value_name="Amount"
        )
        results = engine.run_pre_processing(context)
        assert any(r.severity == "error" and not r.passed for r in results)
        with pytest.raises(DataQualityError):
            engine.check_for_errors(results)
