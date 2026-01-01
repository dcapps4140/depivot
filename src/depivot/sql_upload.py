"""SQL Server upload functionality for depivot."""

from typing import Dict, Optional

import pandas as pd
import pyodbc
from rich.console import Console

from depivot.exceptions import ColumnError, DatabaseError

console = Console()

# Month name to period number mapping
MONTH_TO_PERIOD = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "sept": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def convert_month_to_period(month_str: str) -> int:
    """Convert month name to period number (Jan->1, Feb->2, etc.)

    Args:
        month_str: Month name (e.g., 'Jan', 'February', 'jan')

    Returns:
        Period number (1-12)

    Raises:
        ValueError: If month name is invalid
    """
    if pd.isna(month_str):
        raise ValueError("Month value is NaN")

    month_lower = str(month_str).lower().strip()
    period = MONTH_TO_PERIOD.get(month_lower)

    if period is None:
        raise ValueError(f"Unrecognized month name: '{month_str}'")

    return period


def extract_fiscal_year(release_date: str) -> int:
    """Extract fiscal year from release date string.

    Args:
        release_date: Release date in YYYY-MM format (e.g., '2025-02')

    Returns:
        Fiscal year as integer (e.g., 2025)

    Raises:
        ValueError: If release_date format is invalid
    """
    if pd.isna(release_date):
        raise ValueError("ReleaseDate is NaN")

    try:
        # Handle both YYYY-MM and YYYY_MM formats
        release_str = str(release_date).strip()
        year_part = release_str.split("-")[0] if "-" in release_str else release_str.split("_")[0]
        return int(year_part)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid ReleaseDate format: '{release_date}'. Expected YYYY-MM format.") from e


def fetch_l2_proj_mapping(
    connection_string: str,
    lookup_table: str = "[dbo].[Intel_Site_Names]",
) -> Dict[str, str]:
    """Fetch L2_Proj mapping from lookup table.

    Args:
        connection_string: SQL Server connection string
        lookup_table: Name of lookup table (default: '[dbo].[Intel_Site_Names]')

    Returns:
        Dictionary mapping Site Name -> L2_Proj

    Raises:
        DatabaseError: If query fails or table doesn't exist
    """
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Query to get Site Name -> L2_Proj mapping
        query = f"""
            SELECT DISTINCT [Site Name], [L2_Proj]
            FROM {lookup_table}
            WHERE [L2_Proj] IS NOT NULL AND [Site Name] IS NOT NULL
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        # Build mapping dictionary
        mapping = {row[0]: row[1] for row in rows}

        cursor.close()
        conn.close()

        return mapping

    except pyodbc.Error as e:
        raise DatabaseError(f"Failed to fetch L2_Proj mapping from {lookup_table}: {e}") from e


def transform_dataframe_for_sql(
    df: pd.DataFrame,
    l2_proj_mapping: Dict[str, str],
    var_name: str = "Month",
    value_name: str = "Amount",
    verbose: bool = False,
) -> pd.DataFrame:
    """Transform depivoted DataFrame to SQL Server schema.

    Transforms:
    - Site -> Site (direct)
    - Category -> Category (direct)
    - Month name -> Period (1-12)
    - Amount -> Actuals (direct)
    - DataType -> Status (direct)
    - ReleaseDate (YYYY-MM) -> FiscalYear (extract year)
    - Site -> L2_Proj (lookup from mapping)

    Args:
        df: Depivoted DataFrame
        l2_proj_mapping: Dictionary mapping Site to L2_Proj
        var_name: Name of variable column (default: 'Month')
        value_name: Name of value column (default: 'Amount')
        verbose: Print detailed progress

    Returns:
        Transformed DataFrame with SQL Server columns:
        [L2_Proj, Site, Category, FiscalYear, Period, Actuals, Status]

    Raises:
        ColumnError: If required columns are missing
        ValueError: If data transformation fails
    """
    # Make a copy to avoid modifying original
    sql_df = df.copy()

    # Validate required columns exist
    required_cols = ["Site", "Category", var_name, value_name]
    missing_cols = [col for col in required_cols if col not in sql_df.columns]
    if missing_cols:
        raise ColumnError(f"Required columns missing from DataFrame: {missing_cols}")

    # Convert Month to Period (1-12)
    if verbose:
        console.print(f"[cyan]Converting {var_name} to Period numbers...[/cyan]")

    try:
        sql_df["Period"] = sql_df[var_name].apply(convert_month_to_period)
    except ValueError as e:
        # Find invalid months
        invalid_months = []
        for month in sql_df[var_name].unique():
            try:
                convert_month_to_period(month)
            except ValueError:
                invalid_months.append(str(month))

        raise ColumnError(
            f"Invalid month values in '{var_name}' column: {', '.join(invalid_months)}"
        ) from e

    # Extract FiscalYear from ReleaseDate if available
    if "ReleaseDate" in sql_df.columns:
        if verbose:
            console.print("[cyan]Extracting FiscalYear from ReleaseDate...[/cyan]")

        try:
            sql_df["FiscalYear"] = sql_df["ReleaseDate"].apply(extract_fiscal_year)
        except ValueError as e:
            if verbose:
                console.print(f"[yellow]Warning: {e}. FiscalYear will be NULL.[/yellow]")
            sql_df["FiscalYear"] = None
    else:
        if verbose:
            console.print("[yellow]Warning: No ReleaseDate column. FiscalYear will be NULL.[/yellow]")
        sql_df["FiscalYear"] = None

    # Map Site to L2_Proj
    if verbose:
        console.print("[cyan]Mapping Site to L2_Proj...[/cyan]")

    sql_df["L2_Proj"] = sql_df["Site"].map(l2_proj_mapping)

    # Warn about missing L2_Proj mappings
    missing_sites = sql_df[sql_df["L2_Proj"].isna()]["Site"].unique()
    if len(missing_sites) > 0:
        console.print(
            f"[yellow]Warning: No L2_Proj mapping found for {len(missing_sites)} site(s): "
            f"{', '.join(missing_sites[:5])}{' ...' if len(missing_sites) > 5 else ''}[/yellow]"
        )

    # Rename columns to match SQL schema
    sql_df = sql_df.rename(columns={value_name: "Actuals"})

    # Use DataType as Status if available, otherwise set to NULL
    if "DataType" in sql_df.columns:
        sql_df["Status"] = sql_df["DataType"]
    else:
        if verbose:
            console.print("[yellow]Warning: No DataType column. Status will be NULL.[/yellow]")
        sql_df["Status"] = None

    # Select and reorder columns to match SQL Server table
    final_columns = ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status"]
    sql_df = sql_df[final_columns]

    return sql_df


def upload_to_sql_server(
    df: pd.DataFrame,
    connection_string: str,
    table_name: str,
    mode: str = "append",
    verbose: bool = False,
) -> Dict[str, int]:
    """Upload DataFrame to SQL Server table.

    Args:
        df: DataFrame to upload (must have correct schema)
        connection_string: SQL Server connection string
        table_name: Target table name (e.g., '[dbo].[FY25_Budget_Actuals_DIBS]')
        mode: 'append' or 'replace' (truncate then insert)
        verbose: Print detailed progress

    Returns:
        Dictionary with statistics:
        {
            'rows_uploaded': int,
            'rows_failed': int,
            'table': str,
            'mode': str
        }

    Raises:
        DatabaseError: If connection fails or insert fails
    """
    try:
        # Connect to SQL Server
        if verbose:
            console.print(f"[cyan]Connecting to SQL Server...[/cyan]")

        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Truncate table if replace mode
        if mode == "replace":
            if verbose:
                console.print(f"[yellow]Truncating table {table_name}...[/yellow]")

            try:
                cursor.execute(f"TRUNCATE TABLE {table_name}")
                conn.commit()
            except pyodbc.Error as e:
                console.print(f"[yellow]Warning: Could not truncate table: {e}. Continuing anyway...[/yellow]")

        # Prepare parameterized INSERT statement
        columns = ["L2_Proj", "Site", "Category", "FiscalYear", "Period", "Actuals", "Status"]
        placeholders = ", ".join(["?"] * len(columns))
        column_list = ", ".join([f"[{col}]" for col in columns])

        insert_sql = f"""
            INSERT INTO {table_name}
            ({column_list})
            VALUES ({placeholders})
        """

        # Convert DataFrame to list of tuples
        # Replace NaN with None for SQL NULL
        df_clean = df[columns].copy()
        df_clean = df_clean.replace({pd.NA: None, float('nan'): None})
        df_clean = df_clean.where(pd.notnull(df_clean), None)
        rows = df_clean.values.tolist()

        # Bulk insert using executemany for performance
        if verbose:
            console.print(f"[cyan]Uploading {len(rows)} rows to {table_name}...[/cyan]")

        cursor.executemany(insert_sql, rows)
        conn.commit()

        if verbose:
            console.print(f"[green]Successfully uploaded {len(rows)} rows to {table_name}[/green]")

        # Close connections
        cursor.close()
        conn.close()

        return {
            "rows_uploaded": len(rows),
            "rows_failed": 0,
            "table": table_name,
            "mode": mode,
        }

    except pyodbc.Error as e:
        # Rollback on error
        try:
            conn.rollback()
        except:
            pass

        raise DatabaseError(f"SQL Server upload failed: {e}") from e

    finally:
        # Ensure connections are closed
        try:
            cursor.close()
            conn.close()
        except:
            pass


def validate_sql_connection(connection_string: str) -> bool:
    """Test SQL Server connection.

    Args:
        connection_string: SQL Server connection string

    Returns:
        True if connection successful

    Raises:
        DatabaseError: If connection fails
    """
    try:
        conn = pyodbc.connect(connection_string)
        conn.close()
        return True
    except pyodbc.Error as e:
        raise DatabaseError(f"Cannot connect to SQL Server: {e}") from e
