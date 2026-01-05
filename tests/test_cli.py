"""Tests for CLI interface."""
import pytest
import yaml
from pathlib import Path
from click.testing import CliRunner
from depivot.cli import main


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self, cli_runner):
        """Test --help flag."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Depivot Excel files" in result.output
        assert "--id-vars" in result.output
        assert "--config" in result.output

    def test_cli_version(self, cli_runner):
        """Test --version flag."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_missing_input_path(self, cli_runner):
        """Test error when input path is missing."""
        result = cli_runner.invoke(main, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Error" in result.output

    def test_cli_nonexistent_input_file(self, cli_runner):
        """Test error when input file doesn't exist."""
        result = cli_runner.invoke(main, ["nonexistent.xlsx"])

        assert result.exit_code == 1
        assert "does not exist" in result.output or "Error" in result.output


class TestCLIDryRun:
    """Test dry run mode."""

    def test_dry_run_single_file(self, cli_runner, sample_excel_file):
        """Test dry run with single file."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--id-vars", "Site,Category",
                "--var-name", "Month",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Would process file" in result.output
        assert "ID variables: Site, Category" in result.output

    def test_dry_run_no_id_vars(self, cli_runner, sample_excel_file):
        """Test dry run without ID variables."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--var-name", "Month",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "will add row index" in result.output


class TestCLIConfigSave:
    """Test configuration saving."""

    def test_save_config_only(self, cli_runner, temp_dir):
        """Test saving config without processing."""
        config_file = temp_dir / "test_config.yaml"

        result = cli_runner.invoke(
            main,
            [
                "dummy.xlsx",  # Input not validated when only saving config
                "--id-vars", "Site,Category",
                "--var-name", "Period",
                "--value-name", "Amount",
                "--header-row", "3",
                "--save-config", str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert config_file.exists()
        assert "Configuration saved" in result.output

        # Verify saved config
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        assert config["id_vars"] == "Site,Category"
        assert config["var_name"] == "Period"
        assert config["value_name"] == "Amount"
        assert config["header_row"] == 3

    def test_save_config_excludes_defaults(self, cli_runner, temp_dir):
        """Test that default values are not saved."""
        config_file = temp_dir / "test_config.yaml"

        result = cli_runner.invoke(
            main,
            [
                "dummy.xlsx",
                "--id-vars", "ID",
                "--var-name", "variable",  # Default value
                "--value-name", "value",    # Default value
                "--save-config", str(config_file),
            ],
        )

        assert result.exit_code == 0

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        assert "var_name" not in config  # Default excluded
        assert "value_name" not in config  # Default excluded
        assert config["id_vars"] == "ID"  # Non-default included


class TestCLIConfigLoad:
    """Test configuration loading."""

    def test_load_config(self, cli_runner, temp_dir, sample_excel_file):
        """Test loading config from file."""
        config_file = temp_dir / "test_config.yaml"
        config_data = {
            "id_vars": "Site,Category",
            "var_name": "Period",
            "header_row": 2,
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--config", str(config_file),
                "--dry-run",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert "Loaded configuration from" in result.output

    def test_load_config_nonexistent(self, cli_runner, sample_excel_file):
        """Test error when config file doesn't exist."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--config", "nonexistent.yaml",
            ],
        )

        assert result.exit_code == 1
        assert "Error loading config file" in result.output

    def test_cli_overrides_config(self, cli_runner, temp_dir, sample_excel_file):
        """Test that CLI arguments override config values."""
        config_file = temp_dir / "test_config.yaml"
        config_data = {
            "id_vars": "ID",
            "var_name": "Month",
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--config", str(config_file),
                "--var-name", "Period",  # Override config value
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # The CLI should use "Period" instead of "Month"


class TestCLISQLOptions:
    """Test SQL-related options."""

    def test_sql_flags_mutually_exclusive(self, cli_runner, sample_excel_file):
        """Test that SQL flags are mutually exclusive."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--sql-only",
                "--excel-only",
                "--id-vars", "ID",
            ],
        )

        assert result.exit_code == 1
        assert "Only one of" in result.output

    def test_sql_requires_connection_string(self, cli_runner, sample_excel_file):
        """Test that SQL mode requires connection string."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--sql-only",
                "--sql-table", "[dbo].[TestTable]",
                "--id-vars", "ID",
            ],
        )

        assert result.exit_code == 1
        assert "sql-connection-string is required" in result.output

    def test_sql_requires_table_name(self, cli_runner, sample_excel_file):
        """Test that SQL mode requires table name."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--sql-only",
                "--sql-connection-string", "Driver={ODBC};Server=localhost",
                "--id-vars", "ID",
            ],
        )

        assert result.exit_code == 1
        assert "sql-table is required" in result.output


class TestCLIBatchProcessing:
    """Test batch processing mode."""

    def test_batch_requires_output_dir(self, cli_runner, temp_dir):
        """Test that batch processing requires output directory."""
        input_dir = temp_dir / "input"
        input_dir.mkdir()

        result = cli_runner.invoke(
            main,
            [
                str(input_dir),
                "--id-vars", "ID",
            ],
        )

        assert result.exit_code == 1
        assert "output-dir must be specified" in result.output

    def test_batch_dry_run(self, cli_runner, temp_dir):
        """Test batch processing in dry run mode."""
        input_dir = temp_dir / "input"
        input_dir.mkdir()

        result = cli_runner.invoke(
            main,
            [
                str(input_dir),
                "--id-vars", "ID",
                "--output-dir", str(temp_dir / "output"),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Would process directory" in result.output
        assert "DRY RUN" in result.output


class TestCLIColumnParsing:
    """Test column list parsing."""

    def test_parse_id_vars(self, cli_runner, sample_excel_file):
        """Test parsing comma-separated ID variables."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--id-vars", "Site,Category,Date",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Site, Category, Date" in result.output

    def test_parse_sheet_names(self, cli_runner, sample_excel_file):
        """Test parsing sheet names."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--id-vars", "ID",
                "--sheet-names", "Sales,Revenue",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Sheet names: Sales,Revenue" in result.output


class TestCLIErrorHandling:
    """Test error handling."""

    def test_handles_depivot_error(self, cli_runner):
        """Test that DepivotError is handled gracefully."""
        result = cli_runner.invoke(
            main,
            ["nonexistent.xlsx", "--id-vars", "ID"],
        )

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_invalid_config_yaml(self, cli_runner, temp_dir, sample_excel_file):
        """Test error handling for invalid config YAML."""
        config_file = temp_dir / "invalid.yaml"

        with open(config_file, "w") as f:
            f.write("invalid: yaml: [[[")

        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--config", str(config_file),
            ],
        )

        assert result.exit_code == 1
        assert "Error loading config file" in result.output


class TestCLIOutputPath:
    """Test output path handling."""

    def test_default_output_path(self, cli_runner, sample_excel_file):
        """Test that default output path is generated."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--id-vars", "Site,Category",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Would process file" in result.output

    def test_custom_output_path(self, cli_runner, sample_excel_file, temp_dir):
        """Test custom output path."""
        output_file = temp_dir / "custom_output.xlsx"

        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                str(output_file),
                "--id-vars", "Site,Category",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0


class TestCLIFlags:
    """Test various flag combinations."""

    def test_verbose_flag(self, cli_runner, sample_excel_file, temp_dir):
        """Test verbose output flag."""
        config_file = temp_dir / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({"id_vars": "Site"}, f)

        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--config", str(config_file),
                "--verbose",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "Loaded configuration from" in result.output

    def test_exclude_totals_flag(self, cli_runner, sample_excel_file):
        """Test exclude totals flag."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--id-vars", "Site",
                "--exclude-totals",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

    def test_combine_sheets_flag(self, cli_runner, sample_excel_file):
        """Test combine sheets flag."""
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--id-vars", "Site",
                "--combine-sheets",
                "--output-sheet-name", "Combined",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0


class TestCLIIntegration:
    """Integration tests for CLI."""

    def test_full_config_workflow(self, cli_runner, temp_dir, sample_excel_file):
        """Test complete workflow: save config, load config, process."""
        config_file = temp_dir / "workflow_config.yaml"

        # Step 1: Save config
        result = cli_runner.invoke(
            main,
            [
                "dummy.xlsx",
                "--id-vars", "Site,Category",
                "--var-name", "Month",
                "--value-name", "Amount",
                "--header-row", "2",
                "--exclude-totals",
                "--save-config", str(config_file),
            ],
        )

        assert result.exit_code == 0
        assert config_file.exists()

        # Step 2: Load config and do dry run
        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--config", str(config_file),
                "--dry-run",
                "--verbose",
            ],
        )

        assert result.exit_code == 0
        assert "Loaded configuration from" in result.output

    def test_config_with_validation(self, cli_runner, temp_dir, sample_excel_file):
        """Test config with validation settings."""
        config_file = temp_dir / "validation_config.yaml"
        config_data = {
            "id_vars": "Site,Category",
            "validation_rules": {
                "enabled": True,
                "pre_processing": [
                    {
                        "rule": "check_null_values",
                        "enabled": True,
                        "severity": "warning",
                    }
                ],
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = cli_runner.invoke(
            main,
            [
                str(sample_excel_file),
                "--config", str(config_file),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
