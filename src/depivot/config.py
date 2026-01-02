"""Configuration file handling for depivot."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def load_config(config_file: Path) -> Dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        config_file: Path to YAML configuration file

    Returns:
        Dictionary of configuration parameters

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    return config or {}


def save_config(config_file: Path, config: Dict[str, Any]) -> None:
    """Save configuration to YAML file.

    Args:
        config_file: Path to save configuration
        config: Dictionary of configuration parameters

    Raises:
        IOError: If unable to write config file
    """
    # Create parent directory if it doesn't exist
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_config_params(options: Dict[str, Any]) -> Dict[str, Any]:
    """Extract saveable parameters from options dictionary.

    Args:
        options: Full options dictionary from CLI

    Returns:
        Dictionary of parameters that should be saved to config

    Note:
        Excludes runtime-specific parameters like verbose, overwrite, dry_run
        Only saves non-default values to keep config files clean
    """
    # Parameters that make sense to save in config
    saveable_params = [
        "id_vars",
        "value_vars",
        "var_name",
        "value_name",
        "include_cols",
        "exclude_cols",
        "sheet_names",
        "skip_sheets",
        "header_row",
        "drop_na",
        "index_col_name",
        "data_type_col",
        "data_type_override",
        "forecast_start",
        "combine_sheets",
        "output_sheet_name",
        "exclude_totals",
        "summary_patterns",
        "sql_connection_string",
        "sql_table",
        "sql_mode",
        "sql_l2_lookup_table",
        "validation_rules",
        "template_validation",
    ]

    # Default values - don't save if value matches default
    defaults = {
        "var_name": "variable",
        "value_name": "value",
        "index_col_name": "Row",
        "data_type_col": "DataType",
        "output_sheet_name": "Data",
        "header_row": 0,
        "drop_na": False,
        "combine_sheets": False,
        "exclude_totals": False,
        "sql_mode": "append",
        "sql_l2_lookup_table": "[dbo].[Intel_Site_Names]",
        "validation_rules": None,
        "template_validation": None,
    }

    config = {}
    for param in saveable_params:
        if param in options and options[param] is not None:
            # Skip if value matches default
            if param in defaults and options[param] == defaults[param]:
                continue

            # Skip empty lists
            if isinstance(options[param], list) and len(options[param]) == 0:
                continue

            # Convert lists to comma-separated strings for readability
            if isinstance(options[param], list):
                config[param] = ",".join(str(v) for v in options[param])
            else:
                config[param] = options[param]

    return config


def apply_config(config: Dict[str, Any], cli_options: Dict[str, Any]) -> Dict[str, Any]:
    """Apply configuration to CLI options, with CLI taking precedence.

    Args:
        config: Configuration loaded from file
        cli_options: Options from CLI arguments

    Returns:
        Merged options dictionary (CLI options override config)
    """
    # Start with config values
    merged = config.copy()

    # Override with CLI options (only if they were explicitly set)
    # Note: This is simplified - in practice, you'd need to detect which
    # options were explicitly provided vs defaults
    for key, value in cli_options.items():
        if value is not None:
            merged[key] = value

    return merged
