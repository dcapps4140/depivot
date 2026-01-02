"""
Data quality validation framework for depivot tool.

Provides configurable validation rules with severity levels (error/warning/info)
for pre-processing and post-processing validation.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from rich.console import Console

console = Console()


@dataclass
class ValidationResult:
    """Result from a single validation rule execution."""
    rule_name: str
    severity: str  # "error" | "warning" | "info"
    passed: bool
    message: str
    details: Dict[str, Any]
    timestamp: datetime


@dataclass
class ValidationContext:
    """Context information passed to validation rules."""

    # Pre-processing context
    df: Optional[pd.DataFrame] = None
    sheet_name: Optional[str] = None
    input_file: Optional[Path] = None

    # Post-processing context
    df_source: Optional[pd.DataFrame] = None
    df_processed: Optional[pd.DataFrame] = None

    # Configuration
    id_vars: List[str] = field(default_factory=list)
    value_vars: List[str] = field(default_factory=list)
    var_name: str = "variable"
    value_name: str = "value"

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class ValidationRule(ABC):
    """Abstract base class for validation rules."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize validation rule from config.

        Args:
            config: Rule configuration dictionary with keys:
                - enabled: bool (default True)
                - severity: str "error"|"warning"|"info" (default "warning")
                - params: dict of rule-specific parameters
                - message: str message template with {placeholders}
        """
        self.enabled = config.get("enabled", True)
        self.severity = config.get("severity", "warning")
        self.params = config.get("params", {})
        self.message_template = config.get("message", "Validation failed")

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Execute the validation rule.

        Args:
            context: ValidationContext with DataFrame and configuration

        Returns:
            ValidationResult with pass/fail status and details
        """
        pass

    def is_enabled(self) -> bool:
        """Check if rule is enabled."""
        return self.enabled

    def format_message(self, **kwargs) -> str:
        """
        Format message template with provided variables.

        Args:
            **kwargs: Variables to substitute in message template

        Returns:
            Formatted message string
        """
        try:
            return self.message_template.format(**kwargs)
        except KeyError as e:
            return f"{self.message_template} (missing variable: {e})"


class ValidationEngine:
    """
    Orchestrates validation rule execution.

    Loads rules from configuration, executes them in sequence,
    collects results, and reports to console.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize validation engine from config.

        Args:
            config: Validation configuration dictionary with structure:
                {
                    "enabled": bool,
                    "pre_processing": [rule_configs],
                    "post_processing": [rule_configs],
                    "validation_settings": {
                        "stop_on_error": bool,
                        "max_warnings_display": int,
                        "verbose_rules": bool
                    }
                }
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.settings = config.get("validation_settings", {})
        self.stop_on_error = self.settings.get("stop_on_error", True)

        # Load rules from configuration
        self.pre_processing_rules = self._load_rules(
            config.get("pre_processing", []),
            phase="pre"
        )
        self.post_processing_rules = self._load_rules(
            config.get("post_processing", []),
            phase="post"
        )

    def _load_rules(
        self,
        rule_configs: List[Dict],
        phase: str
    ) -> List[ValidationRule]:
        """
        Load and instantiate validation rules from configuration.

        Args:
            rule_configs: List of rule configuration dictionaries
            phase: "pre" or "post" processing phase

        Returns:
            List of ValidationRule instances
        """
        from depivot.quality_rules import RULE_REGISTRY

        rules = []
        for rule_config in rule_configs:
            rule_name = rule_config.get("rule")
            if not rule_name:
                console.print("[yellow]Warning: Rule config missing 'rule' name, skipping[/yellow]")
                continue

            if rule_name not in RULE_REGISTRY:
                console.print(f"[yellow]Warning: Unknown rule '{rule_name}', skipping[/yellow]")
                continue

            rule_class = RULE_REGISTRY[rule_name]
            try:
                rule = rule_class(rule_config)
                if rule.is_enabled():
                    rules.append(rule)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to load rule '{rule_name}': {e}[/yellow]")
                continue

        return rules

    def run_pre_processing(
        self,
        context: ValidationContext
    ) -> List[ValidationResult]:
        """
        Execute pre-processing validation rules.

        Args:
            context: ValidationContext with pre-processing data

        Returns:
            List of ValidationResult objects
        """
        if not self.enabled:
            return []

        return self._run_rules(self.pre_processing_rules, context)

    def run_post_processing(
        self,
        context: ValidationContext
    ) -> List[ValidationResult]:
        """
        Execute post-processing validation rules.

        Args:
            context: ValidationContext with post-processing data

        Returns:
            List of ValidationResult objects
        """
        if not self.enabled:
            return []

        return self._run_rules(self.post_processing_rules, context)

    def _run_rules(
        self,
        rules: List[ValidationRule],
        context: ValidationContext
    ) -> List[ValidationResult]:
        """
        Execute a list of validation rules.

        Args:
            rules: List of ValidationRule instances
            context: ValidationContext to pass to rules

        Returns:
            List of ValidationResult objects
        """
        results = []

        for rule in rules:
            try:
                result = rule.validate(context)
                results.append(result)

                # Stop on error if configured
                if (result.severity == "error" and
                    not result.passed and
                    self.stop_on_error):
                    break

            except Exception as e:
                # Rule execution failure - treat as error
                results.append(ValidationResult(
                    rule_name=rule.__class__.__name__,
                    severity="error",
                    passed=False,
                    message=f"Rule execution failed: {e}",
                    details={"exception": str(e)},
                    timestamp=datetime.now()
                ))

                if self.stop_on_error:
                    break

        return results

    def report_results(
        self,
        results: List[ValidationResult],
        phase: str,
        verbose: bool = False
    ) -> None:
        """
        Report validation results to console.

        Args:
            results: List of ValidationResult objects
            phase: Description of validation phase (e.g., "Pre-Sheet1")
            verbose: If True, show detailed information
        """
        if not results:
            return

        # Categorize results
        errors = [r for r in results if r.severity == "error" and not r.passed]
        warnings = [r for r in results if r.severity == "warning" and not r.passed]
        info = [r for r in results if r.severity == "info" and not r.passed]
        passed = [r for r in results if r.passed]

        # Display summary
        console.print(f"\n[cyan]Data Quality - {phase.upper()} Results:[/cyan]")
        console.print(f"  [green]Passed:[/green] {len(passed)}")
        console.print(f"  [yellow]Warnings:[/yellow] {len(warnings)}")
        console.print(f"  [red]Errors:[/red] {len(errors)}")
        if verbose:
            console.print(f"  [blue]Info:[/blue] {len(info)}")

        # Display errors
        if errors:
            console.print("\n[red]ERRORS:[/red]")
            for result in errors:
                console.print(f"  - {result.rule_name}: {result.message}")
                if verbose and result.details:
                    console.print(f"    Details: {result.details}")

        # Display warnings (limited)
        if warnings:
            max_display = self.settings.get("max_warnings_display", 20)
            console.print(f"\n[yellow]WARNINGS:[/yellow]")
            for i, result in enumerate(warnings[:max_display]):
                console.print(f"  - {result.rule_name}: {result.message}")
                if verbose and result.details:
                    console.print(f"    Details: {result.details}")

            if len(warnings) > max_display:
                console.print(f"  ... and {len(warnings) - max_display} more warnings")

        # Display info (if verbose)
        if verbose and info:
            console.print(f"\n[blue]INFO:[/blue]")
            for result in info:
                console.print(f"  - {result.rule_name}: {result.message}")
                if result.details:
                    console.print(f"    Details: {result.details}")

    def check_for_errors(self, results: List[ValidationResult]) -> None:
        """
        Check for error-level validation failures and raise exception.

        Args:
            results: List of ValidationResult objects

        Raises:
            DataQualityError: If any error-level validations failed
        """
        from depivot.exceptions import DataQualityError

        errors = [r for r in results if r.severity == "error" and not r.passed]
        if errors:
            error_msgs = [f"{r.rule_name}: {r.message}" for r in errors]
            raise DataQualityError(
                f"Data quality validation failed with {len(errors)} error(s):\n" +
                "\n".join(f"  - {msg}" for msg in error_msgs)
            )
