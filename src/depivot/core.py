"""Core depivoting logic for depivot."""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from depivot.exceptions import ColumnError, FileProcessingError, SheetError
from depivot.utils import (
    extract_release_date,
    find_excel_files,
    generate_output_filename,
    is_summary_row,
    parse_column_list,
)
from depivot.validators import (
    validate_columns_exist,
    validate_file_path,
    validate_id_value_vars,
    validate_output_path,
)

console = Console()

# Month ordering for forecast logic
MONTH_ORDER = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def detect_data_type(sheet_name: str) -> str:
    """Detect data type from sheet name.

    Args:
        sheet_name: Name of the Excel sheet

    Returns:
        Data type: "Actual", "Budget", or "Forecast"
    """
    sheet_lower = sheet_name.lower()

    # Check for keywords in order of specificity
    if "forecast" in sheet_lower:
        return "Forecast"
    elif "budg" in sheet_lower or "budget" in sheet_lower:
        return "Budget"
    elif "actu" in sheet_lower or "actual" in sheet_lower:
        return "Actual"
    else:
        # Default to Actual if no keywords found
        return "Actual"


def is_forecast_month(month: str, forecast_start: str) -> bool:
    """Determine if a month is forecast based on forecast start month.

    Args:
        month: Month name (e.g., "Jan", "Feb")
        forecast_start: Month name when forecast starts (e.g., "Jun")

    Returns:
        True if month is forecast, False if actual
    """
    month_lower = month.lower()[:3]  # Get first 3 chars, lowercase
    forecast_lower = forecast_start.lower()[:3]

    month_num = MONTH_ORDER.get(month_lower, 0)
    forecast_num = MONTH_ORDER.get(forecast_lower, 0)

    if month_num == 0 or forecast_num == 0:
        # Invalid month name, default to actual
        return False

    return month_num >= forecast_num


def clean_numeric_value(value) -> float:
    """Clean and convert text values to numeric.

    Handles:
    - Special characters
    - Commas (1,234.56)
    - Negative numbers in parentheses (123.45) → -123.45
    - Currency symbols

    Args:
        value: Value to clean (can be str, int, float)

    Returns:
        Float value, or NaN if conversion fails
    """
    import re

    if pd.isna(value):
        return float('nan')

    # If already numeric, return as float
    if isinstance(value, (int, float)):
        return float(value)

    # Convert to string and clean
    value_str = str(value)

    # Remove special characters (keep digits, decimal point, comma, parentheses, minus)
    value_str = re.sub(r'[^\d.,()\-]', '', value_str)

    # Handle negative numbers in parentheses
    is_negative = False
    if '(' in value_str and ')' in value_str:
        is_negative = True
        value_str = value_str.replace('(', '').replace(')', '')

    # Remove commas
    value_str = value_str.replace(',', '')

    # Try to convert to float
    try:
        result = float(value_str)
        return -result if is_negative else result
    except (ValueError, AttributeError):
        return float('nan')


def get_sheet_names(
    input_file: Path, sheet_names: Optional[str] = None, skip_sheets: Optional[str] = None
) -> List[str]:
    """Get list of sheet names to process from Excel file.

    Args:
        input_file: Path to Excel file
        sheet_names: Comma-separated list of specific sheets to process
        skip_sheets: Comma-separated list of sheets to skip

    Returns:
        List of sheet names to process

    Raises:
        SheetError: If specified sheets don't exist
    """
    # Read all sheet names from the Excel file
    try:
        xl_file = pd.ExcelFile(input_file)
        all_sheets = xl_file.sheet_names
    except Exception as e:
        raise FileProcessingError(f"Error reading Excel file {input_file}: {e}")

    # Filter sheets based on options
    if sheet_names:
        requested_sheets = parse_column_list(sheet_names)
        missing_sheets = [s for s in requested_sheets if s not in all_sheets]
        if missing_sheets:
            raise SheetError(
                f"Sheet(s) not found: {', '.join(missing_sheets)}. "
                f"Available sheets: {', '.join(all_sheets)}"
            )
        sheets_to_process = requested_sheets
    elif skip_sheets:
        skip_list = parse_column_list(skip_sheets)
        sheets_to_process = [s for s in all_sheets if s not in skip_list]
    else:
        sheets_to_process = all_sheets

    if not sheets_to_process:
        raise SheetError("No sheets to process after filtering")

    return sheets_to_process


def resolve_columns(
    df: pd.DataFrame,
    id_vars: List[str],
    value_vars: Optional[List[str]] = None,
    include_cols: Optional[List[str]] = None,
    exclude_cols: Optional[List[str]] = None,
) -> tuple:
    """Resolve which columns are id_vars and value_vars.

    Args:
        df: DataFrame to process
        id_vars: Identifier columns
        value_vars: Columns to unpivot (if None, all non-id columns)
        include_cols: Only include these columns
        exclude_cols: Exclude these columns

    Returns:
        Tuple of (id_vars, value_vars) lists

    Raises:
        ColumnError: If column resolution fails
    """
    all_cols = df.columns.tolist()

    # Start with all columns
    available_cols = set(all_cols)

    # Apply include filter
    if include_cols:
        available_cols = available_cols & set(include_cols)

    # Apply exclude filter
    if exclude_cols:
        available_cols = available_cols - set(exclude_cols)

    # Determine value_vars
    if value_vars is None:
        # Auto-detect: all columns except id_vars
        final_value_vars = [col for col in available_cols if col not in id_vars]
    else:
        final_value_vars = [col for col in value_vars if col in available_cols]

    if not final_value_vars:
        raise ColumnError(
            "No value columns to unpivot. Check your column specifications."
        )

    # Validate no overlap
    validate_id_value_vars(id_vars, final_value_vars)

    return id_vars, final_value_vars


def depivot_sheet(
    df: pd.DataFrame,
    id_vars: List[str],
    value_vars: Optional[List[str]] = None,
    var_name: str = "variable",
    value_name: str = "value",
    include_cols: Optional[List[str]] = None,
    exclude_cols: Optional[List[str]] = None,
    drop_na: bool = False,
    index_col_name: str = "Row",
) -> pd.DataFrame:
    """Depivot a single DataFrame using pandas melt.

    Args:
        df: DataFrame to depivot
        id_vars: Identifier columns (if empty, row index will be added)
        value_vars: Columns to unpivot (if None, all non-id columns)
        var_name: Name for the variable column
        value_name: Name for the value column
        include_cols: Only include these columns
        exclude_cols: Exclude these columns
        drop_na: Drop rows with NA values after unpivoting
        index_col_name: Name for auto-generated index column

    Returns:
        Depivoted DataFrame

    Raises:
        ColumnError: If column validation fails
    """
    # If no id_vars, add row index as identifier
    if not id_vars:
        df = df.copy()
        df.insert(0, index_col_name, range(1, len(df) + 1))
        id_vars = [index_col_name]

    # Resolve columns
    final_id_vars, final_value_vars = resolve_columns(
        df, id_vars, value_vars, include_cols, exclude_cols
    )

    # Perform melt operation
    df_long = pd.melt(
        df,
        id_vars=final_id_vars,
        value_vars=final_value_vars,
        var_name=var_name,
        value_name=value_name,
    )

    # Drop NA values if requested
    if drop_na:
        df_long = df_long.dropna()

    return df_long


def create_validation_report(
    input_file: Path,
    sheets_data: Dict[str, pd.DataFrame],
    depivoted_sheets: Dict[str, pd.DataFrame],
    id_vars: List[str],
    value_vars_by_sheet: Dict[str, List[str]],
    value_name: str,
    header_row: int = 0,
) -> pd.DataFrame:
    """Create validation report comparing source and processed data.

    Args:
        input_file: Path to input Excel file
        sheets_data: Dictionary of original DataFrames by sheet name
        depivoted_sheets: Dictionary of depivoted DataFrames by sheet name
        id_vars: Identifier columns used
        value_vars_by_sheet: Value columns used for each sheet
        value_name: Name of value column in output
        header_row: Header row used when reading

    Returns:
        DataFrame with validation results
    """
    validation_rows = []

    for sheet_name in sheets_data.keys():
        df_source = sheets_data[sheet_name]
        df_processed = depivoted_sheets[sheet_name]
        value_vars = value_vars_by_sheet[sheet_name]

        # Calculate source totals by grouping columns
        if id_vars:
            # Group by id_vars and sum value_vars
            for _, row in df_source.iterrows():
                id_values = {col: row[col] for col in id_vars if col in df_source.columns}
                source_total = sum(
                    clean_numeric_value(row[col]) for col in value_vars if col in df_source.columns
                )

                # Find matching processed rows
                mask = pd.Series([True] * len(df_processed))
                for col, val in id_values.items():
                    mask &= df_processed[col] == val

                processed_total = df_processed.loc[mask, value_name].sum()

                validation_rows.append({
                    "SourceFile": input_file.name,
                    "Sheet": sheet_name,
                    **id_values,
                    "Source_Total": source_total,
                    "Processed_Total": processed_total,
                    "Difference": processed_total - source_total,
                    "Match": "OK" if abs(processed_total - source_total) < 0.01 else "MISMATCH",
                })

        # Sheet-level totals
        sheet_source_total = sum(
            clean_numeric_value(df_source[col].sum()) for col in value_vars if col in df_source.columns
        )
        sheet_processed_total = df_processed[value_name].sum()

        validation_rows.append({
            "SourceFile": input_file.name,
            "Sheet": sheet_name,
            "Category": "SHEET_TOTAL",
            "Source_Total": sheet_source_total,
            "Processed_Total": sheet_processed_total,
            "Difference": sheet_processed_total - sheet_source_total,
            "Match": "OK" if abs(sheet_processed_total - sheet_source_total) < 0.01 else "MISMATCH",
        })

    # Grand total across all sheets
    grand_source = sum(row["Source_Total"] for row in validation_rows if row.get("Category") == "SHEET_TOTAL")
    grand_processed = sum(row["Processed_Total"] for row in validation_rows if row.get("Category") == "SHEET_TOTAL")

    validation_rows.append({
        "SourceFile": input_file.name,
        "Sheet": "ALL_SHEETS",
        "Category": "GRAND_TOTAL",
        "Source_Total": grand_source,
        "Processed_Total": grand_processed,
        "Difference": grand_processed - grand_source,
        "Match": "OK" if abs(grand_processed - grand_source) < 0.01 else "MISMATCH",
    })

    return pd.DataFrame(validation_rows)


def depivot_file(
    input_file: Path,
    output_file: Path,
    id_vars: List[str],
    value_vars: Optional[List[str]] = None,
    var_name: str = "variable",
    value_name: str = "value",
    sheet_names: Optional[str] = None,
    skip_sheets: Optional[str] = None,
    include_cols: Optional[List[str]] = None,
    exclude_cols: Optional[List[str]] = None,
    header_row: int = 0,
    drop_na: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
    index_col_name: str = "Row",
    data_type_col: str = "DataType",
    data_type_override: Optional[str] = None,
    forecast_start: Optional[str] = None,
    release_date: Optional[str] = None,
    no_validate: bool = False,
    combine_sheets: bool = False,
    output_sheet_name: str = "Data",
    exclude_totals: bool = False,
    summary_patterns: Optional[List[str]] = None,
    sql_only: bool = False,
    excel_only: bool = False,
    both: bool = False,
    sql_connection_string: Optional[str] = None,
    sql_table: Optional[str] = None,
    sql_mode: str = "append",
    sql_l2_lookup_table: str = "[dbo].[Intel_Site_Names]",
    validation_rules: Optional[Dict] = None,
    no_validate_quality: bool = False,
    template_validation: Optional[Dict] = None,
) -> Dict[str, int]:
    """Depivot a single Excel file with multi-sheet support.

    Args:
        input_file: Path to input Excel file
        output_file: Path to output file
        id_vars: Identifier columns (if empty, row index will be added)
        value_vars: Columns to unpivot (if None, auto-detect)
        var_name: Name for the variable column
        value_name: Name for the value column
        sheet_names: Specific sheets to process (comma-separated)
        skip_sheets: Sheets to skip (comma-separated)
        include_cols: Only include these columns
        exclude_cols: Exclude these columns
        header_row: Row number containing column headers (0-indexed)
        drop_na: Drop rows with NA values
        overwrite: Allow overwriting existing files
        verbose: Verbose output
        index_col_name: Name for auto-generated index column
        data_type_col: Name for data type column (default: "DataType")
        data_type_override: Override auto-detected data type
        forecast_start: Month when forecast starts (e.g., "Jun"). Months before are Actual, after are Forecast.
        release_date: Release date (YYYY-MM format). Auto-extracted from filename if not specified.
        no_validate: Skip validation report generation

    Returns:
        Dictionary with processing statistics

    Raises:
        Various exceptions from validators and processors
    """
    # Validate input file
    validate_file_path(input_file, must_exist=True)

    # Validate output path
    validate_output_path(output_file, overwrite=overwrite)

    # PHASE 1: Template structure validation (fast, openpyxl, no data load)
    template_validator = None
    if template_validation:
        from depivot.template_validators import TemplateValidator
        template_validator = TemplateValidator(template_validation)

        if verbose:
            console.print("[cyan]Validating template structure...[/cyan]")

        template_validator.validate_file_structure(input_file)

    # Extract or validate release date
    if release_date is None:
        release_date = extract_release_date(input_file.name)
        if release_date and verbose:
            console.print(f"[cyan]Auto-detected release date: {release_date}[/cyan]")

    if release_date is None:
        console.print("[yellow]Warning: Could not extract release date from filename. No ReleaseDate column will be added.[/yellow]")
        console.print("[yellow]Use --release-date to specify manually (e.g., --release-date '2025-02')[/yellow]")

    # Get sheets to process
    sheets_to_process = get_sheet_names(input_file, sheet_names, skip_sheets)

    if verbose:
        console.print(f"[cyan]Processing {len(sheets_to_process)} sheet(s)[/cyan]")

    # Process each sheet
    sheets_data = {}  # Store original DataFrames for validation
    depivoted_sheets = {}
    value_vars_by_sheet = {}  # Track value_vars used for each sheet
    total_rows = 0

    # Initialize data quality validation engine
    validation_engine = None
    all_quality_results = {"pre": [], "post": []}

    if not no_validate_quality and validation_rules:
        from depivot.data_quality import ValidationEngine
        validation_engine = ValidationEngine(validation_rules)

    for sheet_name in sheets_to_process:
        try:
            if verbose:
                console.print(f"  [yellow]Processing sheet:[/yellow] {sheet_name}")

            # PHASE 2: Template sheet validation (openpyxl, per sheet, before data load)
            if template_validator:
                if verbose:
                    console.print(f"    [cyan]Validating template for {sheet_name}...[/cyan]")

                template_validator.validate_sheet_template(input_file, sheet_name)

            # Read sheet
            df = pd.read_excel(input_file, sheet_name=sheet_name, header=header_row)

            # Filter out summary/total rows if requested
            if exclude_totals and id_vars:
                initial_row_count = len(df)
                # Filter rows
                mask = df.apply(
                    lambda row: not is_summary_row(row.to_dict(), id_vars, summary_patterns),
                    axis=1
                )
                df = df[mask].copy()
                filtered_count = initial_row_count - len(df)

                if filtered_count > 0 and verbose:
                    console.print(
                        f"    [yellow]Filtered {filtered_count} summary row(s) from {sheet_name}[/yellow]"
                    )

            # Store filtered data for validation
            sheets_data[sheet_name] = df.copy()

            # PHASE 3: Template dataframe validation (pandas, after data load)
            if template_validator:
                template_validator.validate_dataframe_template(df, sheet_name)

            # PRE-PROCESSING DATA QUALITY VALIDATION
            if validation_engine:
                from depivot.data_quality import ValidationContext

                pre_context = ValidationContext(
                    df=df,
                    sheet_name=sheet_name,
                    input_file=input_file,
                    id_vars=id_vars if id_vars else [],
                    value_vars=value_vars if value_vars else [],
                    var_name=var_name,
                    value_name=value_name
                )

                pre_results = validation_engine.run_pre_processing(pre_context)
                all_quality_results["pre"].extend(pre_results)

                # Report results if verbose
                if verbose:
                    validation_engine.report_results(pre_results, f"Pre-{sheet_name}", verbose)

                # Check for errors (raises DataQualityError if any)
                validation_engine.check_for_errors(pre_results)

            # Validate columns exist in this sheet (skip if no id_vars)
            if id_vars:
                validate_columns_exist(df, id_vars, sheet_name=sheet_name)

            # Resolve columns to track what value_vars were used
            final_id_vars, final_value_vars = resolve_columns(
                df, id_vars, value_vars, include_cols, exclude_cols
            )
            value_vars_by_sheet[sheet_name] = final_value_vars

            # Depivot the sheet
            df_long = depivot_sheet(
                df,
                id_vars=id_vars,
                value_vars=value_vars,
                var_name=var_name,
                value_name=value_name,
                include_cols=include_cols,
                exclude_cols=exclude_cols,
                drop_na=drop_na,
                index_col_name=index_col_name,
            )

            # Clean numeric values in value column
            if value_name in df_long.columns:
                df_long[value_name] = df_long[value_name].apply(clean_numeric_value)

            # Add DataType column
            base_data_type = data_type_override if data_type_override else detect_data_type(sheet_name)

            # Apply forecast logic if specified and sheet is Actual
            if forecast_start and base_data_type == "Actual" and var_name in df_long.columns:
                # Determine data type based on month
                df_long[data_type_col] = df_long[var_name].apply(
                    lambda month: "Forecast" if is_forecast_month(str(month), forecast_start) else "Actual"
                )
            else:
                # Use base data type for all rows
                df_long[data_type_col] = base_data_type

            # Add ReleaseDate column if available
            if release_date:
                df_long["ReleaseDate"] = release_date

            depivoted_sheets[sheet_name] = df_long
            total_rows += len(df_long)

            # POST-PROCESSING DATA QUALITY VALIDATION
            if validation_engine:
                post_context = ValidationContext(
                    df_source=df,
                    df_processed=df_long,
                    sheet_name=sheet_name,
                    input_file=input_file,
                    id_vars=final_id_vars,
                    value_vars=final_value_vars,
                    var_name=var_name,
                    value_name=value_name
                )

                post_results = validation_engine.run_post_processing(post_context)
                all_quality_results["post"].extend(post_results)

                # Report results if verbose
                if verbose:
                    validation_engine.report_results(post_results, f"Post-{sheet_name}", verbose)

                # Check for errors (raises DataQualityError if any)
                validation_engine.check_for_errors(post_results)

            if verbose:
                console.print(
                    f"    [green]OK[/green] {len(df)} rows -> {len(df_long)} rows"
                )

        except Exception as e:
            console.print(f"  [red]ERROR processing sheet '{sheet_name}': {e}[/red]")
            raise FileProcessingError(
                f"Error processing sheet '{sheet_name}' in {input_file}: {e}"
            )

    # Generate validation report if enabled
    validation_df = None
    if not no_validate and sheets_data:
        if verbose:
            console.print("[cyan]Generating validation report...[/cyan]")
        validation_df = create_validation_report(
            input_file=input_file,
            sheets_data=sheets_data,
            depivoted_sheets=depivoted_sheets,
            id_vars=id_vars,
            value_vars_by_sheet=value_vars_by_sheet,
            value_name=value_name,
            header_row=header_row,
        )

        # Check for mismatches
        mismatches = validation_df[validation_df["Match"] == "MISMATCH"]
        if not mismatches.empty:
            console.print("[yellow]WARNING: Validation found mismatches![/yellow]")
            console.print(mismatches.to_string())
        elif verbose:
            console.print("[green]Validation: All totals match![/green]")

    # Report final data quality results summary
    if validation_engine and all_quality_results:
        all_results = all_quality_results["pre"] + all_quality_results["post"]
        if all_results:
            validation_engine.report_results(all_results, "Overall Summary", verbose)

    # Determine output modes
    excel_output = not sql_only
    sql_output = sql_only or both

    # For SQL upload, always combine sheets into one DataFrame
    if sql_output or combine_sheets:
        combined_dfs = []
        for sheet_name, df_long in depivoted_sheets.items():
            combined_dfs.append(df_long)
        combined_df = pd.concat(combined_dfs, ignore_index=True)
    else:
        combined_df = None

    # SQL Server upload
    if sql_output:
        from depivot.sql_upload import (
            upload_to_sql_server,
            transform_dataframe_for_sql,
            fetch_l2_proj_mapping,
        )
        from depivot.exceptions import DatabaseError

        try:
            # Fetch L2_Proj mapping
            if verbose:
                console.print("[cyan]Fetching L2_Proj mapping from SQL Server...[/cyan]")

            l2_proj_mapping = fetch_l2_proj_mapping(
                connection_string=sql_connection_string,
                lookup_table=sql_l2_lookup_table,
            )

            if verbose:
                console.print(f"[cyan]Fetched {len(l2_proj_mapping)} L2_Proj mappings[/cyan]")

            # Transform data to SQL schema
            if verbose:
                console.print("[cyan]Transforming data for SQL Server...[/cyan]")

            sql_df = transform_dataframe_for_sql(
                df=combined_df,
                l2_proj_mapping=l2_proj_mapping,
                var_name=var_name,
                value_name=value_name,
                verbose=verbose,
            )

            # Upload to SQL Server
            sql_stats = upload_to_sql_server(
                df=sql_df,
                connection_string=sql_connection_string,
                table_name=sql_table,
                mode=sql_mode,
                verbose=verbose,
            )

            console.print(
                f"[green]SQL: Uploaded {sql_stats['rows_uploaded']} rows to {sql_table} (mode: {sql_mode})[/green]"
            )

        except Exception as e:
            console.print(f"[red]SQL Upload Error: {e}[/red]")
            raise DatabaseError(f"SQL upload failed: {e}")

    # Excel output (if requested)
    if excel_output:
        try:
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                # Write depivoted sheets
                if combine_sheets:
                    combined_df.to_excel(writer, sheet_name=output_sheet_name, index=False)

                    if verbose:
                        console.print(
                            f"[green]Combined {len(depivoted_sheets)} sheet(s) into '{output_sheet_name}'[/green]"
                        )
                else:
                    # Write each sheet separately
                    for sheet_name, df_long in depivoted_sheets.items():
                        df_long.to_excel(writer, sheet_name=sheet_name, index=False)

                # Write validation sheet if generated
                if validation_df is not None:
                    validation_df.to_excel(writer, sheet_name="Validation", index=False)

            if verbose:
                if combine_sheets:
                    sheet_count = 1  # Just the combined sheet
                else:
                    sheet_count = len(depivoted_sheets)
                if validation_df is not None:
                    sheet_count += 1
                console.print(
                    f"[green]OK Wrote {sheet_count} sheet(s) to {output_file}[/green]"
                )

        except Exception as e:
            raise FileProcessingError(f"Error writing output file {output_file}: {e}")

    return {
        "input_file": str(input_file),
        "output_file": str(output_file),
        "sheets_processed": len(depivoted_sheets),
        "total_rows": total_rows,
    }


def depivot_multi_file(
    input_files: List[Path],
    output_file: Path,
    **options,
) -> Dict[str, int]:
    """Process multiple Excel files and combine into single output.

    Args:
        input_files: List of input Excel files to process
        output_file: Path to combined output file
        **options: Additional options passed to depivot_file processing

    Returns:
        Dictionary with processing statistics

    Raises:
        Various exceptions from validators and processors
    """
    verbose = options.get("verbose", False)
    no_validate = options.get("no_validate", False)
    output_sheet_name = options.get("output_sheet_name", "Data")

    if verbose:
        console.print(f"[cyan]Processing {len(input_files)} file(s) into combined output[/cyan]")

    # Collect all depivoted data
    all_combined_data = []
    all_validation_data = []
    total_sheets = 0
    total_rows = 0

    for input_file in input_files:
        if verbose:
            console.print(f"  [yellow]Processing file:[/yellow] {input_file.name}")

        # Process this file with combine_sheets=False to get individual sheets
        # We'll combine across files manually
        temp_options = options.copy()
        temp_options["combine_sheets"] = False
        temp_options["no_validate"] = True  # We'll do validation at the end

        # Get sheets to process
        sheets_to_process = get_sheet_names(
            input_file,
            temp_options.get("sheet_names"),
            temp_options.get("skip_sheets"),
        )

        # Process each sheet
        sheets_data = {}
        depivoted_sheets = {}
        value_vars_by_sheet = {}

        for sheet_name in sheets_to_process:
            try:
                # Read sheet
                df = pd.read_excel(
                    input_file,
                    sheet_name=sheet_name,
                    header=temp_options.get("header_row", 0),
                )

                # Store original for validation
                sheets_data[sheet_name] = df.copy()

                # Resolve columns
                id_vars = temp_options.get("id_vars", [])
                value_vars = temp_options.get("value_vars")
                include_cols = temp_options.get("include_cols")
                exclude_cols = temp_options.get("exclude_cols")

                final_id_vars, final_value_vars = resolve_columns(
                    df, id_vars, value_vars, include_cols, exclude_cols
                )
                value_vars_by_sheet[sheet_name] = final_value_vars

                # Depivot the sheet
                df_long = depivot_sheet(
                    df,
                    id_vars=id_vars,
                    value_vars=value_vars,
                    var_name=temp_options.get("var_name", "variable"),
                    value_name=temp_options.get("value_name", "value"),
                    include_cols=include_cols,
                    exclude_cols=exclude_cols,
                    drop_na=temp_options.get("drop_na", False),
                    index_col_name=temp_options.get("index_col_name", "Row"),
                )

                # Clean numeric values
                value_name = temp_options.get("value_name", "value")
                if value_name in df_long.columns:
                    df_long[value_name] = df_long[value_name].apply(clean_numeric_value)

                # Add DataType column
                data_type_col = temp_options.get("data_type_col", "DataType")
                data_type_override = temp_options.get("data_type_override")
                forecast_start = temp_options.get("forecast_start")
                var_name = temp_options.get("var_name", "variable")

                base_data_type = data_type_override if data_type_override else detect_data_type(sheet_name)

                if forecast_start and base_data_type == "Actual" and var_name in df_long.columns:
                    df_long[data_type_col] = df_long[var_name].apply(
                        lambda month: "Forecast" if is_forecast_month(str(month), forecast_start) else "Actual"
                    )
                else:
                    df_long[data_type_col] = base_data_type

                # Add ReleaseDate column
                release_date = temp_options.get("release_date")
                if release_date is None:
                    release_date = extract_release_date(input_file.name)

                if release_date:
                    df_long["ReleaseDate"] = release_date

                depivoted_sheets[sheet_name] = df_long
                all_combined_data.append(df_long)
                total_sheets += 1
                total_rows += len(df_long)

                if verbose:
                    console.print(
                        f"    [green]OK[/green] {input_file.name} / {sheet_name}: {len(df)} rows -> {len(df_long)} rows"
                    )

            except Exception as e:
                console.print(f"  [red]ERROR processing {input_file.name} / {sheet_name}: {e}[/red]")
                raise FileProcessingError(
                    f"Error processing sheet '{sheet_name}' in {input_file}: {e}"
                )

        # Generate validation for this file
        if not no_validate:
            validation_df = create_validation_report(
                input_file=input_file,
                sheets_data=sheets_data,
                depivoted_sheets=depivoted_sheets,
                id_vars=temp_options.get("id_vars", []),
                value_vars_by_sheet=value_vars_by_sheet,
                value_name=temp_options.get("value_name", "value"),
                header_row=temp_options.get("header_row", 0),
            )
            all_validation_data.append(validation_df)

    # Combine all data
    if verbose:
        console.print(f"[cyan]Combining {len(all_combined_data)} sheet(s) from {len(input_files)} file(s)[/cyan]")

    combined_df = pd.concat(all_combined_data, ignore_index=True)

    # Combine validation data
    validation_combined = None
    if all_validation_data:
        validation_combined = pd.concat(all_validation_data, ignore_index=True)

        # Check for mismatches
        mismatches = validation_combined[validation_combined["Match"] == "MISMATCH"]
        if not mismatches.empty:
            console.print("[yellow]WARNING: Validation found mismatches![/yellow]")
            # Show just the summary, not all rows
            mismatch_summary = mismatches.groupby(["SourceFile", "Sheet"]).size()
            console.print(f"Mismatches by file/sheet:\n{mismatch_summary}")
        elif verbose:
            console.print("[green]Validation: All totals match![/green]")

    # Determine output modes
    sql_only = options.get("sql_only", False)
    both = options.get("both", False)
    excel_output = not sql_only
    sql_output = sql_only or both

    # SQL Server upload
    if sql_output:
        from depivot.sql_upload import (
            upload_to_sql_server,
            transform_dataframe_for_sql,
            fetch_l2_proj_mapping,
        )
        from depivot.exceptions import DatabaseError

        sql_connection_string = options.get("sql_connection_string")
        sql_table = options.get("sql_table")
        sql_mode = options.get("sql_mode", "append")
        sql_l2_lookup_table = options.get("sql_l2_lookup_table", "[dbo].[Intel_Site_Names]")
        var_name = options.get("var_name", "variable")
        value_name = options.get("value_name", "value")

        try:
            # Fetch L2_Proj mapping
            if verbose:
                console.print("[cyan]Fetching L2_Proj mapping from SQL Server...[/cyan]")

            l2_proj_mapping = fetch_l2_proj_mapping(
                connection_string=sql_connection_string,
                lookup_table=sql_l2_lookup_table,
            )

            if verbose:
                console.print(f"[cyan]Fetched {len(l2_proj_mapping)} L2_Proj mappings[/cyan]")

            # Transform data to SQL schema
            if verbose:
                console.print("[cyan]Transforming data for SQL Server...[/cyan]")

            sql_df = transform_dataframe_for_sql(
                df=combined_df,
                l2_proj_mapping=l2_proj_mapping,
                var_name=var_name,
                value_name=value_name,
                verbose=verbose,
            )

            # Upload to SQL Server
            sql_stats = upload_to_sql_server(
                df=sql_df,
                connection_string=sql_connection_string,
                table_name=sql_table,
                mode=sql_mode,
                verbose=verbose,
            )

            console.print(
                f"[green]SQL: Uploaded {sql_stats['rows_uploaded']} rows to {sql_table} (mode: {sql_mode})[/green]"
            )

        except Exception as e:
            console.print(f"[red]SQL Upload Error: {e}[/red]")
            raise DatabaseError(f"SQL upload failed: {e}")

    # Excel output (if requested)
    if excel_output:
        try:
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                combined_df.to_excel(writer, sheet_name=output_sheet_name, index=False)

                if validation_combined is not None:
                    validation_combined.to_excel(writer, sheet_name="Validation", index=False)

            if verbose:
                sheet_count = 1 + (1 if validation_combined is not None else 0)
                console.print(
                    f"[green]OK Wrote {sheet_count} sheet(s) to {output_file}[/green]"
                )

        except Exception as e:
            raise FileProcessingError(f"Error writing output file {output_file}: {e}")

    return {
        "input_files": [str(f) for f in input_files],
        "output_file": str(output_file),
        "sheets_processed": total_sheets,
        "total_rows": total_rows,
    }


def depivot_batch(
    input_dir: Path,
    output_dir: Path,
    pattern: str = "*.xlsx",
    recursive: bool = False,
    suffix: str = "_unpivoted",
    **options,
) -> Dict[str, List]:
    """Batch process multiple Excel files.

    Args:
        input_dir: Directory containing input files
        output_dir: Directory for output files
        pattern: Glob pattern for finding files
        recursive: Search subdirectories recursively
        suffix: Suffix for output filenames
        **options: Additional options passed to depivot_file

    Returns:
        Dictionary with lists of successful and failed files

    Raises:
        ValidationError: If directories are invalid
    """
    if not input_dir.is_dir():
        raise FileProcessingError(f"Input path is not a directory: {input_dir}")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all matching files
    files = find_excel_files(input_dir, pattern, recursive)

    if not files:
        console.print(
            f"[yellow]No files matching pattern '{pattern}' found in {input_dir}[/yellow]"
        )
        return {"successful": [], "failed": []}

    console.print(f"[cyan]Found {len(files)} file(s) to process[/cyan]")

    successful = []
    failed = []

    # Process each file
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing files...", total=len(files))

        for file in files:
            try:
                # Generate output filename
                output_file = output_dir / f"{file.stem}{suffix}.xlsx"

                progress.update(
                    task, description=f"[cyan]Processing {file.name}...", advance=0
                )

                # Process the file
                result = depivot_file(
                    input_file=file, output_file=output_file, **options
                )

                successful.append(result)
                console.print(f"[green]OK {file.name}[/green]")

            except Exception as e:
                failed.append({"file": str(file), "error": str(e)})
                console.print(f"[red]ERROR {file.name}: {e}[/red]")

            progress.advance(task)

    # Summary
    console.print(
        f"\n[cyan]Summary:[/cyan] {len(successful)} successful, {len(failed)} failed"
    )

    return {"successful": successful, "failed": failed}
