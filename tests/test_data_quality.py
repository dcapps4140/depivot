"""Tests for data quality validation."""
import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from depivot.data_quality import (
    ValidationEngine,
    ValidationContext,
    ValidationResult,
    ValidationRule,
)
from depivot.exceptions import DataQualityError


# =============================================================================
# VALIDATION RESULT TESTS
# =============================================================================

class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test ValidationResult can be created."""
        result = ValidationResult(
            rule_name="TestRule",
            severity="error",
            passed=False,
            message="Test failed",
            details={"count": 5},
            timestamp=datetime.now()
        )

        assert result.rule_name == "TestRule"
        assert result.severity == "error"
        assert result.passed is False
        assert result.message == "Test failed"
        assert result.details == {"count": 5}
        assert isinstance(result.timestamp, datetime)


# =============================================================================
# VALIDATION CONTEXT TESTS
# =============================================================================

class TestValidationContext:
    """Test ValidationContext dataclass."""

    def test_context_defaults(self):
        """Test ValidationContext default values."""
        context = ValidationContext()

        assert context.df is None
        assert context.sheet_name is None
        assert context.input_file is None
        assert context.df_source is None
        assert context.df_processed is None
        assert context.id_vars == []
        assert context.value_vars == []
        assert context.var_name == "variable"
        assert context.value_name == "value"
        assert context.metadata == {}

    def test_context_with_data(self, sample_dataframe):
        """Test ValidationContext with provided data."""
        context = ValidationContext(
            df=sample_dataframe,
            sheet_name="TestSheet",
            input_file=Path("test.xlsx"),
            id_vars=["Site"],
            value_vars=["Jan", "Feb"],
            var_name="Month",
            value_name="Amount",
            metadata={"key": "value"}
        )

        assert context.df is not None
        assert context.sheet_name == "TestSheet"
        assert context.input_file == Path("test.xlsx")
        assert context.id_vars == ["Site"]
        assert context.value_vars == ["Jan", "Feb"]
        assert context.var_name == "Month"
        assert context.value_name == "Amount"
        assert context.metadata == {"key": "value"}


# =============================================================================
# VALIDATION RULE BASE CLASS TESTS
# =============================================================================

class MockValidationRule(ValidationRule):
    """Mock validation rule for testing."""

    def validate(self, context: ValidationContext) -> ValidationResult:
        return ValidationResult(
            rule_name="MockRule",
            severity=self.severity,
            passed=True,
            message="Mock passed",
            details={},
            timestamp=datetime.now()
        )


class TestValidationRule:
    """Test ValidationRule base class."""

    def test_rule_initialization_defaults(self):
        """Test rule initialization with defaults."""
        config = {}
        rule = MockValidationRule(config)

        assert rule.enabled is True
        assert rule.severity == "warning"
        assert rule.params == {}
        assert rule.message_template == "Validation failed"

    def test_rule_initialization_custom(self):
        """Test rule initialization with custom config."""
        config = {
            "enabled": False,
            "severity": "error",
            "params": {"threshold": 0.5},
            "message": "Custom message"
        }
        rule = MockValidationRule(config)

        assert rule.enabled is False
        assert rule.severity == "error"
        assert rule.params == {"threshold": 0.5}
        assert rule.message_template == "Custom message"

    def test_is_enabled(self):
        """Test is_enabled method."""
        enabled_rule = MockValidationRule({"enabled": True})
        disabled_rule = MockValidationRule({"enabled": False})

        assert enabled_rule.is_enabled() is True
        assert disabled_rule.is_enabled() is False

    def test_format_message_basic(self):
        """Test message formatting with variables."""
        rule = MockValidationRule({"message": "Found {count} issues"})
        message = rule.format_message(count=5)

        assert message == "Found 5 issues"

    def test_format_message_multiple_vars(self):
        """Test message formatting with multiple variables."""
        rule = MockValidationRule({
            "message": "{column} has {count} nulls ({percent}%)"
        })
        message = rule.format_message(column="Site", count=10, percent=25.5)

        assert message == "Site has 10 nulls (25.5%)"

    def test_format_message_missing_variable(self):
        """Test message formatting with missing variable."""
        rule = MockValidationRule({"message": "Found {count} issues"})
        message = rule.format_message(other="value")

        assert "missing variable" in message.lower()
        assert "count" in message


# =============================================================================
# VALIDATION ENGINE TESTS
# =============================================================================

class TestValidationEngine:
    """Test ValidationEngine orchestration."""

    def test_engine_initialization(self, data_quality_config):
        """Test engine initialization from config."""
        engine = ValidationEngine(data_quality_config)

        assert engine.enabled is True
        assert len(engine.pre_processing_rules) >= 1
        assert len(engine.post_processing_rules) >= 1

    def test_engine_initialization_disabled(self):
        """Test engine initialization when disabled."""
        config = {"enabled": False}
        engine = ValidationEngine(config)

        assert engine.enabled is False

    def test_engine_initialization_empty_config(self):
        """Test engine initialization with empty config."""
        config = {}
        engine = ValidationEngine(config)

        assert engine.enabled is True
        assert engine.pre_processing_rules == []
        assert engine.post_processing_rules == []

    def test_engine_settings(self):
        """Test engine settings extraction."""
        config = {
            "enabled": True,
            "validation_settings": {
                "stop_on_error": False,
                "max_warnings_display": 10,
                "verbose_rules": True
            }
        }
        engine = ValidationEngine(config)

        assert engine.stop_on_error is False
        assert engine.settings["max_warnings_display"] == 10

    def test_load_rules_valid(self):
        """Test loading valid rules."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "check_null_values",
                    "enabled": True,
                    "severity": "warning",
                    "params": {"threshold": 0.1}
                }
            ]
        }
        engine = ValidationEngine(config)

        assert len(engine.pre_processing_rules) == 1

    def test_load_rules_disabled_rule(self):
        """Test loading rules with disabled rule."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "check_null_values",
                    "enabled": False,
                    "severity": "warning"
                }
            ]
        }
        engine = ValidationEngine(config)

        assert len(engine.pre_processing_rules) == 0

    def test_load_rules_missing_name(self, capsys):
        """Test loading rules with missing rule name."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "enabled": True,
                    "severity": "warning"
                }
            ]
        }
        engine = ValidationEngine(config)

        assert len(engine.pre_processing_rules) == 0

    def test_load_rules_unknown_rule(self, capsys):
        """Test loading rules with unknown rule name."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "nonexistent_rule",
                    "enabled": True
                }
            ]
        }
        engine = ValidationEngine(config)

        assert len(engine.pre_processing_rules) == 0

    def test_run_pre_processing_disabled_engine(self, sample_dataframe):
        """Test pre-processing returns empty when engine disabled."""
        config = {"enabled": False}
        engine = ValidationEngine(config)
        context = ValidationContext(df=sample_dataframe)

        results = engine.run_pre_processing(context)

        assert results == []

    def test_run_post_processing_disabled_engine(self, sample_dataframe):
        """Test post-processing returns empty when engine disabled."""
        config = {"enabled": False}
        engine = ValidationEngine(config)
        context = ValidationContext(df=sample_dataframe, df_processed=sample_dataframe)

        results = engine.run_post_processing(context)

        assert results == []

    def test_run_rules_success(self, sample_dataframe):
        """Test successful rule execution."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "check_null_values",
                    "enabled": True,
                    "severity": "warning",
                    "params": {"threshold": 0.5}
                }
            ]
        }
        engine = ValidationEngine(config)
        context = ValidationContext(df=sample_dataframe)

        results = engine.run_pre_processing(context)

        assert len(results) > 0
        assert all(isinstance(r, ValidationResult) for r in results)

    def test_run_rules_stop_on_error(self, dataframe_with_duplicates):
        """Test stop_on_error functionality."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "check_duplicates",
                    "enabled": True,
                    "severity": "error",
                    "params": {"key_columns": ["Site", "Category"]}
                },
                {
                    "rule": "check_null_values",
                    "enabled": True,
                    "severity": "warning",
                    "params": {"threshold": 0.1}
                }
            ],
            "validation_settings": {"stop_on_error": True}
        }
        engine = ValidationEngine(config)
        context = ValidationContext(df=dataframe_with_duplicates)

        results = engine.run_pre_processing(context)

        # Should stop after first error
        assert len(results) == 1
        assert results[0].severity == "error"
        assert not results[0].passed

    def test_run_rules_no_stop_on_error(self, dataframe_with_duplicates):
        """Test continuing after error when stop_on_error=False."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "check_duplicates",
                    "enabled": True,
                    "severity": "error",
                    "params": {"key_columns": ["Site", "Category"]}
                },
                {
                    "rule": "check_null_values",
                    "enabled": True,
                    "severity": "warning",
                    "params": {"threshold": 0.1}
                }
            ],
            "validation_settings": {"stop_on_error": False}
        }
        engine = ValidationEngine(config)
        context = ValidationContext(df=dataframe_with_duplicates)

        results = engine.run_pre_processing(context)

        # Should run all rules
        assert len(results) >= 2

    def test_run_rules_exception_handling(self, sample_dataframe):
        """Test exception handling during rule execution."""
        config = {
            "enabled": True,
            "pre_processing": [
                {
                    "rule": "check_null_values",
                    "enabled": True,
                    "severity": "warning",
                    "params": {"threshold": 0.1}
                }
            ],
            "validation_settings": {"stop_on_error": True}
        }
        engine = ValidationEngine(config)

        # Mock a rule to raise exception
        def mock_validate(context):
            raise ValueError("Test exception")

        engine.pre_processing_rules[0].validate = mock_validate
        context = ValidationContext(df=sample_dataframe)

        results = engine.run_pre_processing(context)

        assert len(results) == 1
        assert results[0].severity == "error"
        assert not results[0].passed
        assert "Rule execution failed" in results[0].message

    def test_report_results_empty(self, capsys):
        """Test reporting with no results."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        engine.report_results([], "test")

        # Should not produce output for empty results
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_report_results_passed_only(self, capsys):
        """Test reporting with only passed results."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name="Rule1",
                severity="warning",
                passed=True,
                message="Passed",
                details={},
                timestamp=datetime.now()
            )
        ]

        engine.report_results(results, "test")

        captured = capsys.readouterr()
        assert "Passed: 1" in captured.out

    def test_report_results_with_errors(self, capsys):
        """Test reporting with error results."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name="ErrorRule",
                severity="error",
                passed=False,
                message="Error occurred",
                details={"count": 5},
                timestamp=datetime.now()
            )
        ]

        engine.report_results(results, "test")

        captured = capsys.readouterr()
        assert "ERRORS:" in captured.out
        assert "ErrorRule" in captured.out

    def test_report_results_with_warnings(self, capsys):
        """Test reporting with warning results."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name="WarningRule",
                severity="warning",
                passed=False,
                message="Warning occurred",
                details={},
                timestamp=datetime.now()
            )
        ]

        engine.report_results(results, "test")

        captured = capsys.readouterr()
        assert "WARNINGS:" in captured.out
        assert "WarningRule" in captured.out

    def test_report_results_verbose(self, capsys):
        """Test reporting in verbose mode."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name="InfoRule",
                severity="info",
                passed=False,
                message="Info message",
                details={"key": "value"},
                timestamp=datetime.now()
            )
        ]

        engine.report_results(results, "test", verbose=True)

        captured = capsys.readouterr()
        assert "INFO:" in captured.out
        assert "Details:" in captured.out

    def test_report_results_many_warnings(self, capsys):
        """Test reporting with many warnings (truncation)."""
        config = {
            "enabled": True,
            "validation_settings": {"max_warnings_display": 2}
        }
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name=f"Warning{i}",
                severity="warning",
                passed=False,
                message=f"Warning {i}",
                details={},
                timestamp=datetime.now()
            )
            for i in range(5)
        ]

        engine.report_results(results, "test")

        captured = capsys.readouterr()
        assert "and 3 more warnings" in captured.out

    def test_check_for_errors_no_errors(self):
        """Test check_for_errors with no errors."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name="Rule1",
                severity="warning",
                passed=False,
                message="Warning",
                details={},
                timestamp=datetime.now()
            )
        ]

        # Should not raise
        engine.check_for_errors(results)

    def test_check_for_errors_with_errors(self):
        """Test check_for_errors raises exception."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name="ErrorRule",
                severity="error",
                passed=False,
                message="Error occurred",
                details={},
                timestamp=datetime.now()
            )
        ]

        with pytest.raises(DataQualityError, match="Data quality validation failed"):
            engine.check_for_errors(results)

    def test_check_for_errors_multiple_errors(self):
        """Test check_for_errors with multiple errors."""
        config = {"enabled": True}
        engine = ValidationEngine(config)

        results = [
            ValidationResult(
                rule_name="Error1",
                severity="error",
                passed=False,
                message="First error",
                details={},
                timestamp=datetime.now()
            ),
            ValidationResult(
                rule_name="Error2",
                severity="error",
                passed=False,
                message="Second error",
                details={},
                timestamp=datetime.now()
            )
        ]

        with pytest.raises(DataQualityError) as exc_info:
            engine.check_for_errors(results)

        assert "2 error(s)" in str(exc_info.value)
        assert "Error1" in str(exc_info.value)
        assert "Error2" in str(exc_info.value)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestNullValuesCheck:
    """Test null values validation integration."""

    def test_null_values_pass(self, sample_dataframe):
        """Test null values check passes with clean data."""
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
        assert results[0].passed is True


class TestDuplicatesCheck:
    """Test duplicates validation integration."""

    def test_duplicates_fail(self, dataframe_with_duplicates):
        """Test duplicates check fails with duplicate data."""
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
