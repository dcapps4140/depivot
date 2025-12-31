"""CLI interface for depivot using Click."""

from pathlib import Path

import click
from rich.console import Console

from depivot.core import depivot_batch, depivot_file
from depivot.exceptions import DepivotError
from depivot.utils import generate_output_filename, parse_column_list

console = Console()


@click.command()
@click.argument("input_path", type=str)
@click.argument("output_path", type=str, required=False)
@click.option(
    "--id-vars",
    "-i",
    help="Identifier columns to keep (comma-separated, e.g., 'ID,Name'). If not specified, a row index will be added.",
)
@click.option(
    "--value-vars",
    "-v",
    help="Columns to unpivot (comma-separated). If not specified, all non-id columns will be used.",
)
@click.option(
    "--var-name",
    default="variable",
    help="Name for the variable column in output (default: 'variable')",
)
@click.option(
    "--value-name",
    default="value",
    help="Name for the value column in output (default: 'value')",
)
@click.option(
    "--index-name",
    default="Row",
    help="Name for auto-generated row index column when no --id-vars specified (default: 'Row')",
)
@click.option(
    "--data-type-col",
    default="DataType",
    help="Name for data type column (default: 'DataType'). Auto-detects Actual/Budget/Forecast from sheet names.",
)
@click.option(
    "--data-type-override",
    help="Override auto-detected data type (e.g., 'Actual', 'Budget'). Use when sheet name detection is incorrect.",
)
@click.option(
    "--forecast-start",
    help="Month when forecast starts (e.g., 'Jun'). Months before are Actual, after are Forecast. Only applies to Actual sheets.",
)
@click.option(
    "--release-date",
    help="Release date in YYYY-MM format (e.g., '2025-02'). Auto-extracted from filename if not specified.",
)
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip validation report generation (validation is enabled by default)",
)
@click.option(
    "--combine-sheets",
    is_flag=True,
    help="Combine all sheets into a single output worksheet (adds SourceSheet column)",
)
@click.option(
    "--output-sheet-name",
    default="Data",
    help="Name for combined output sheet when using --combine-sheets (default: 'Data')",
)
@click.option(
    "--pattern",
    "-p",
    default="*.xlsx",
    help="Glob pattern for batch processing (default: '*.xlsx')",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for batch processing",
)
@click.option(
    "--exclude-cols",
    "-e",
    help="Columns to exclude from processing (comma-separated)",
)
@click.option(
    "--include-cols",
    help="Only include these columns (comma-separated)",
)
@click.option(
    "--sheet-names",
    "-s",
    help="Specific sheets to process (comma-separated). Default: all sheets",
)
@click.option(
    "--skip-sheets",
    help="Sheet names to skip (comma-separated)",
)
@click.option(
    "--header-row",
    type=int,
    default=0,
    help="Row number containing column headers (0-indexed, default: 0)",
)
@click.option(
    "--suffix",
    default="_unpivoted",
    help="Suffix for output filenames in batch mode (default: '_unpivoted')",
)
@click.option(
    "--drop-na",
    is_flag=True,
    help="Drop rows with NA values after unpivoting",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recursively search subdirectories in batch mode",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing output files",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Verbose output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be done without executing",
)
@click.version_option(version="0.1.0", prog_name="depivot")
def main(
    input_path,
    output_path,
    id_vars,
    value_vars,
    var_name,
    value_name,
    index_name,
    data_type_col,
    data_type_override,
    forecast_start,
    release_date,
    no_validate,
    combine_sheets,
    output_sheet_name,
    pattern,
    output_dir,
    exclude_cols,
    include_cols,
    sheet_names,
    skip_sheets,
    header_row,
    suffix,
    drop_na,
    recursive,
    overwrite,
    verbose,
    dry_run,
):
    """Depivot Excel files from wide to long format.

    INPUT_PATH can be a single Excel file or a directory for batch processing.

    OUTPUT_PATH is optional for single files (defaults to <input>_unpivoted.xlsx).
    For batch processing, use --output-dir instead.

    Examples:

        \b
        # Process single file with multiple sheets
        depivot data.xlsx --id-vars "ID,Name" --var-name "Month"

        \b
        # Process only specific sheets
        depivot data.xlsx --id-vars "ID" --sheet-names "Sales,Revenue"

        \b
        # Skip certain sheets
        depivot data.xlsx --id-vars "ID" --skip-sheets "Metadata"

        \b
        # Batch process directory
        depivot ./data/ --id-vars "ID" --output-dir ./output/
    """
    try:
        # Convert string paths to Path objects
        input_path_str = input_path
        output_path_obj = Path(output_path) if output_path else None

        # Parse column lists
        id_vars_list = parse_column_list(id_vars) if id_vars else []
        value_vars_list = parse_column_list(value_vars) if value_vars else None
        include_cols_list = parse_column_list(include_cols) if include_cols else None
        exclude_cols_list = parse_column_list(exclude_cols) if exclude_cols else None

        # Check for wildcard patterns in input path
        has_wildcards = '*' in input_path_str or '?' in input_path_str

        if has_wildcards:
            # Unescape wildcards (for bash escaping with backslashes)
            import re
            unescaped_pattern = input_path_str.replace(r'\*', '*').replace(r'\?', '?')

            # Expand wildcards to list of files
            from glob import glob
            matching_files = [Path(f) for f in glob(unescaped_pattern) if Path(f).is_file()]
            if not matching_files:
                raise DepivotError(f"No files found matching pattern: {unescaped_pattern}")
            if verbose:
                console.print(f"[cyan]Found {len(matching_files)} file(s) matching pattern[/cyan]")
                for f in matching_files:
                    console.print(f"  - {f.name}")
        else:
            # Validate that non-wildcard path exists
            input_path_obj = Path(input_path_str)
            if not input_path_obj.exists():
                raise DepivotError(f"Input path does not exist: {input_path_str}")
            matching_files = None

        # Determine if batch or single file processing
        is_batch = input_path_obj.is_dir() if not has_wildcards else False

        if dry_run:
            console.print("[yellow]DRY RUN - No files will be modified[/yellow]")
            if is_batch:
                console.print(f"Would process directory: {input_path_str}")
                console.print(f"Pattern: {pattern}")
                console.print(f"Recursive: {recursive}")
            elif has_wildcards:
                console.print(f"Would process wildcard pattern: {input_path_str}")
                console.print(f"Matching {len(matching_files)} file(s)")
            else:
                console.print(f"Would process file: {input_path_str}")
            if id_vars_list:
                console.print(f"ID variables: {', '.join(id_vars_list)}")
            else:
                console.print(f"No ID variables - will add row index '{index_name}'")
            if value_vars_list:
                console.print(f"Value variables: {', '.join(value_vars_list)}")
            if sheet_names:
                console.print(f"Sheet names: {sheet_names}")
            if skip_sheets:
                console.print(f"Skip sheets: {skip_sheets}")
            return

        # Prepare common options
        options = {
            "id_vars": id_vars_list,
            "value_vars": value_vars_list,
            "var_name": var_name,
            "value_name": value_name,
            "include_cols": include_cols_list,
            "exclude_cols": exclude_cols_list,
            "sheet_names": sheet_names,
            "skip_sheets": skip_sheets,
            "header_row": header_row,
            "drop_na": drop_na,
            "overwrite": overwrite,
            "verbose": verbose,
            "index_col_name": index_name,
            "data_type_col": data_type_col,
            "data_type_override": data_type_override,
            "forecast_start": forecast_start,
            "release_date": release_date,
            "no_validate": no_validate,
            "combine_sheets": combine_sheets,
            "output_sheet_name": output_sheet_name,
        }

        if is_batch:
            # Batch processing
            if not output_dir:
                raise DepivotError(
                    "For batch processing, --output-dir must be specified"
                )

            result = depivot_batch(
                input_dir=input_path_obj,
                output_dir=output_dir,
                pattern=pattern,
                recursive=recursive,
                suffix=suffix,
                **options,
            )

            # Report results
            if result["failed"]:
                console.print("\n[red]Failed files:[/red]")
                for failed in result["failed"]:
                    console.print(f"  {failed['file']}: {failed['error']}")

        elif has_wildcards:
            # Multi-file wildcard processing
            if not output_path_obj:
                raise DepivotError(
                    "For wildcard processing, OUTPUT_PATH must be specified"
                )

            # Import the multi-file processing function
            from depivot.core import depivot_multi_file

            result = depivot_multi_file(
                input_files=matching_files,
                output_file=output_path_obj,
                **options,
            )

            console.print(
                f"\n[green]SUCCESS: Processed {len(matching_files)} file(s) with "
                f"{result['sheets_processed']} sheet(s) and {result['total_rows']} total rows[/green]"
            )
            console.print(f"[cyan]Output: {result['output_file']}[/cyan]")

        else:
            # Single file processing
            if not output_path_obj:
                output_path_obj = generate_output_filename(input_path_obj, suffix)

            result = depivot_file(input_file=input_path_obj, output_file=output_path_obj, **options)

            console.print(
                f"\n[green]SUCCESS: Depivoted {result['sheets_processed']} "
                f"sheet(s) with {result['total_rows']} total rows[/green]"
            )
            console.print(f"[cyan]Output: {result['output_file']}[/cyan]")

    except DepivotError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        if verbose:
            console.print_exception()
        raise click.Abort()


if __name__ == "__main__":
    main()
