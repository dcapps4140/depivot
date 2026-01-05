"""Tests for configuration file handling."""
import pytest
import yaml
from pathlib import Path
from depivot.config import load_config, save_config, get_config_params, apply_config


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_success(self, temp_dir):
        """Test loading a valid config file."""
        config_file = temp_dir / "config.yaml"
        config_data = {
            "id_vars": "ID,Name",
            "var_name": "Month",
            "value_name": "Amount",
            "header_row": 2,
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        result = load_config(config_file)

        assert result == config_data
        assert result["id_vars"] == "ID,Name"
        assert result["header_row"] == 2

    def test_load_config_file_not_found(self, temp_dir):
        """Test loading a non-existent config file."""
        config_file = temp_dir / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(config_file)

    def test_load_config_invalid_yaml(self, temp_dir):
        """Test loading an invalid YAML file."""
        config_file = temp_dir / "invalid.yaml"

        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            load_config(config_file)

    def test_load_config_empty_file(self, temp_dir):
        """Test loading an empty config file."""
        config_file = temp_dir / "empty.yaml"
        config_file.touch()

        result = load_config(config_file)

        assert result == {}


class TestSaveConfig:
    """Test configuration saving."""

    def test_save_config_success(self, temp_dir):
        """Test saving a config file."""
        config_file = temp_dir / "config.yaml"
        config_data = {
            "id_vars": "ID,Name",
            "var_name": "Month",
            "value_name": "Amount",
        }

        save_config(config_file, config_data)

        assert config_file.exists()

        with open(config_file, "r") as f:
            loaded = yaml.safe_load(f)

        assert loaded == config_data

    def test_save_config_creates_parent_dirs(self, temp_dir):
        """Test that save_config creates parent directories."""
        config_file = temp_dir / "subdir" / "config.yaml"
        config_data = {"id_vars": "ID"}

        save_config(config_file, config_data)

        assert config_file.exists()
        assert config_file.parent.exists()

    def test_save_config_overwrites_existing(self, temp_dir):
        """Test that save_config overwrites existing files."""
        config_file = temp_dir / "config.yaml"

        # Write initial config
        save_config(config_file, {"id_vars": "ID"})

        # Overwrite with new config
        new_config = {"id_vars": "ID,Name", "var_name": "Period"}
        save_config(config_file, new_config)

        with open(config_file, "r") as f:
            loaded = yaml.safe_load(f)

        assert loaded == new_config


class TestGetConfigParams:
    """Test extracting saveable parameters."""

    def test_get_config_params_basic(self):
        """Test extracting basic parameters."""
        options = {
            "id_vars": ["ID", "Name"],
            "var_name": "Month",
            "value_name": "Sales",
            "verbose": True,  # Should be excluded
            "overwrite": False,  # Should be excluded
        }

        result = get_config_params(options)

        assert result["id_vars"] == "ID,Name"  # Converted to comma-separated string
        assert result["var_name"] == "Month"
        assert result["value_name"] == "Sales"
        assert "verbose" not in result
        assert "overwrite" not in result

    def test_get_config_params_excludes_defaults(self):
        """Test that default values are excluded."""
        options = {
            "id_vars": ["ID"],
            "var_name": "variable",  # Default value
            "value_name": "value",    # Default value
            "header_row": 0,          # Default value
            "drop_na": False,         # Default value
        }

        result = get_config_params(options)

        assert "var_name" not in result
        assert "value_name" not in result
        assert "header_row" not in result
        assert "drop_na" not in result
        assert "id_vars" in result  # Non-default value

    def test_get_config_params_excludes_none(self):
        """Test that None values are excluded."""
        options = {
            "id_vars": ["ID"],
            "value_vars": None,
            "include_cols": None,
        }

        result = get_config_params(options)

        assert "value_vars" not in result
        assert "include_cols" not in result
        assert "id_vars" in result

    def test_get_config_params_excludes_empty_lists(self):
        """Test that empty lists are excluded."""
        options = {
            "id_vars": [],
            "value_vars": ["Jan", "Feb"],
        }

        result = get_config_params(options)

        assert "id_vars" not in result
        assert "value_vars" in result

    def test_get_config_params_converts_lists(self):
        """Test that lists are converted to comma-separated strings."""
        options = {
            "id_vars": ["ID", "Name", "Date"],
            "value_vars": ["Q1", "Q2", "Q3", "Q4"],
            "exclude_cols": ["Notes", "Comments"],
        }

        result = get_config_params(options)

        assert result["id_vars"] == "ID,Name,Date"
        assert result["value_vars"] == "Q1,Q2,Q3,Q4"
        assert result["exclude_cols"] == "Notes,Comments"

    def test_get_config_params_non_default_values(self):
        """Test saving non-default values."""
        options = {
            "id_vars": ["Site", "Category"],
            "var_name": "Period",  # Non-default
            "header_row": 3,       # Non-default
            "combine_sheets": True,  # Non-default
            "sql_mode": "replace",   # Non-default
        }

        result = get_config_params(options)

        assert result["var_name"] == "Period"
        assert result["header_row"] == 3
        assert result["combine_sheets"] is True
        assert result["sql_mode"] == "replace"

    def test_get_config_params_validation_config(self):
        """Test that validation configs are saved."""
        validation_rules = {
            "enabled": True,
            "pre_processing": [{"rule": "check_null_values"}],
        }
        template_validation = {
            "enabled": True,
            "file_structure": [{"check": "expected_sheets"}],
        }

        options = {
            "id_vars": ["ID"],
            "validation_rules": validation_rules,
            "template_validation": template_validation,
        }

        result = get_config_params(options)

        assert result["validation_rules"] == validation_rules
        assert result["template_validation"] == template_validation


class TestApplyConfig:
    """Test applying config to CLI options."""

    def test_apply_config_basic(self):
        """Test basic config application."""
        config = {
            "id_vars": "ID,Name",
            "var_name": "Month",
            "header_row": 2,
        }
        cli_options = {
            "id_vars": None,
            "var_name": None,
            "verbose": True,
        }

        result = apply_config(config, cli_options)

        assert result["id_vars"] == "ID,Name"  # From config
        assert result["var_name"] == "Month"    # From config
        assert result["header_row"] == 2        # From config
        assert result["verbose"] is True        # From CLI

    def test_apply_config_cli_overrides(self):
        """Test that CLI options override config."""
        config = {
            "id_vars": "ID",
            "var_name": "Month",
            "header_row": 2,
        }
        cli_options = {
            "id_vars": "Site,Category",  # Override
            "var_name": "Period",        # Override
            "header_row": 5,             # Override
        }

        result = apply_config(config, cli_options)

        assert result["id_vars"] == "Site,Category"
        assert result["var_name"] == "Period"
        assert result["header_row"] == 5

    def test_apply_config_cli_none_doesnt_override(self):
        """Test that None CLI values don't override config."""
        config = {
            "id_vars": "ID,Name",
            "var_name": "Month",
        }
        cli_options = {
            "id_vars": None,     # Should not override
            "var_name": None,    # Should not override
            "verbose": True,
        }

        result = apply_config(config, cli_options)

        assert result["id_vars"] == "ID,Name"
        assert result["var_name"] == "Month"
        assert result["verbose"] is True

    def test_apply_config_empty_config(self):
        """Test applying empty config."""
        config = {}
        cli_options = {
            "id_vars": "ID",
            "verbose": True,
        }

        result = apply_config(config, cli_options)

        assert result["id_vars"] == "ID"
        assert result["verbose"] is True

    def test_apply_config_empty_cli(self):
        """Test applying with empty CLI options."""
        config = {
            "id_vars": "ID,Name",
            "var_name": "Month",
        }
        cli_options = {}

        result = apply_config(config, cli_options)

        assert result["id_vars"] == "ID,Name"
        assert result["var_name"] == "Month"
