from collections.abc import Callable
from datetime import datetime
from typing import Any

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_df, save_df_to_analysis_dir
from .tool_exceptions import ConfigurationError, DataQualityError, ValidationError


def _validate_dataframe_input(df: pl.DataFrame, function_name: str) -> pl.DataFrame:
    """
    Standardized input validation for DataFrame data.

    Args:
        df: Input DataFrame to validate
        function_name: Name of calling function for error messages

    Returns:
        pl.DataFrame: Validated Polars DataFrame

    Raises:
        ValidationError: If input is invalid
        DataQualityError: If DataFrame is empty
    """
    if not isinstance(df, pl.DataFrame):
        raise ValidationError(f"Input must be a Polars DataFrame for {function_name}")

    if df.is_empty():
        raise DataQualityError(
            f"Input DataFrame is empty for {function_name}", "Provide a DataFrame with at least one row of data"
        )

    return df


def _validate_column_exists(df: pl.DataFrame, column: str, function_name: str) -> None:
    """
    Validate that a column exists in the DataFrame.

    Args:
        df: DataFrame to check
        column: Column name to validate
        function_name: Name of calling function for error messages

    Raises:
        ValidationError: If column doesn't exist
    """
    if column not in df.columns:
        raise ValidationError(
            f"Column '{column}' not found in DataFrame for {function_name}. Available columns: {df.columns}"
        )


def _parse_date_string(date_str: str, function_name: str) -> pl.Expr:
    """
    Parse date string into Polars date expression.

    Args:
        date_str: Date string to parse
        function_name: Name of calling function for error messages

    Returns:
        pl.Expr: Polars date expression

    Raises:
        DataQualityError: If date string is invalid
    """
    try:
        # Try to parse as ISO format first (YYYY-MM-DD)
        if len(date_str) == 10 and date_str.count("-") == 2:
            year, month, day = map(int, date_str.split("-"))
            return pl.date(year, month, day)
        else:
            # Try to parse with datetime and convert
            parsed_date = datetime.fromisoformat(date_str).date()
            return pl.date(parsed_date.year, parsed_date.month, parsed_date.day)
    except (ValueError, TypeError) as e:
        raise DataQualityError(
            f"Invalid date format '{date_str}' in {function_name}: {str(e)}",
            "Use ISO format (YYYY-MM-DD) or valid datetime string",
        )


def _create_operator_expression(column: str, operator: str, value: Any, function_name: str) -> pl.Expr:
    """
    Create Polars expression for comparison operations.

    Args:
        column: Column name
        operator: Comparison operator string
        value: Value to compare against
        function_name: Name of calling function for error messages

    Returns:
        pl.Expr: Polars filter expression

    Raises:
        ConfigurationError: If operator is not supported
    """
    col_expr = pl.col(column)

    operator_map: dict[str, Callable[..., pl.Expr]] = {
        ">": lambda c, v: c > v,
        "<": lambda c, v: c < v,
        ">=": lambda c, v: c >= v,
        "<=": lambda c, v: c <= v,
        "==": lambda c, v: c == v,
        "!=": lambda c, v: c != v,
        "=": lambda c, v: c == v,  # Alternative equality
    }

    if operator not in operator_map:
        raise ConfigurationError(
            f"Unsupported operator '{operator}' in {function_name}. "
            f"Supported operators: {list(operator_map.keys())}"
        )

    try:
        return operator_map[operator](col_expr, value)
    except Exception as e:
        raise DataQualityError(
            f"Error creating filter expression for {column} {operator} {value} in {function_name}: {str(e)}",
            "Ensure value type is compatible with column data type",
        )


def filter_by_date_range(
    ctx: RunContext[FinnDeps],
    file_path: str,
    *,
    date_column: str,
    start_date: str,
    end_date: str,
    output_filename: str,
) -> str:
    """
    Filter DataFrame by date range using Polars optimized date operations.

    Args:
        file_path: Path to the input file
        date_column: Name of the date column
        start_date: Start date (ISO format YYYY-MM-DD)
        end_date: End date (ISO format YYYY-MM-DD)
        output_filename: Filename to save filtered results

    Returns:
        Path: Path to saved filtered DataFrame

    Example:
        >>> result_path = FILTER_BY_DATE_RANGE(
        ...     "transactions.parquet",
        ...     date_column='transaction_date',
        ...     start_date='2024-01-01',
        ...     end_date='2024-12-31',
        ...     output_filename='filtered_transactions.parquet'
        ... )
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Input validation
    df = _validate_dataframe_input(df, "FILTER_BY_DATE_RANGE")
    _validate_column_exists(df, date_column, "FILTER_BY_DATE_RANGE")

    try:
        # Parse date strings to Polars date expressions
        start_date_expr = _parse_date_string(start_date, "FILTER_BY_DATE_RANGE")
        end_date_expr = _parse_date_string(end_date, "FILTER_BY_DATE_RANGE")

        # Validate date range
        start_dt = datetime.fromisoformat(start_date).date()
        end_dt = datetime.fromisoformat(end_date).date()
        if start_dt > end_dt:
            raise ValidationError("Start date must be before or equal to end date")

        # Core filtering operation using Polars is_between for optimal performance
        # First ensure the date column is properly parsed as date type
        filtered_df = df.with_columns(
            pl.col(date_column).str.to_date(format="%Y-%m-%d", strict=False).alias(date_column)
        ).filter(pl.col(date_column).is_between(start_date_expr, end_date_expr))

        # Validate results
        if filtered_df.is_empty():
            raise ModelRetry(
                f"No records found in date range {start_date} to {end_date}\nCheck date range and ensure data exists in the specified period",
            )

        # Save results to analysis directory
        return save_df_to_analysis_dir(ctx, filtered_df, output_filename)

    except Exception as e:
        raise ModelRetry(f"Date range filtering failed: {str(e)}")


def filter_by_value(
    ctx: RunContext[FinnDeps],
    file_path: str,
    *,
    column: str,
    operator: str,
    value: Any,
    output_filename: str,
) -> str:
    """
    Filter DataFrame by column values using comparison operators.

    Args:
        file_path: Path to the input file
        column: Column name to filter on
        operator: Comparison operator ('>', '<', '>=', '<=', '==', '!=')
        value: Value to compare against
        output_filename: Filename to save filtered results

    Returns:
        Path: Path to saved filtered DataFrame

    Example:
        >>> result_path = FILTER_BY_VALUE(
        ...     "sales.parquet",
        ...     column='amount',
        ...     operator='>',
        ...     value=1000,
        ...     output_filename='high_value_sales.parquet'
        ... )
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Input validation
    df = _validate_dataframe_input(df, "FILTER_BY_VALUE")
    _validate_column_exists(df, column, "FILTER_BY_VALUE")

    try:
        # Create filter expression
        filter_expr = _create_operator_expression(column, operator, value, "FILTER_BY_VALUE")

        # Core filtering operation
        filtered_df = df.filter(filter_expr)

        # Validate results
        if filtered_df.is_empty():
            raise ModelRetry(
                f"No records found matching condition: {column} {operator} {value}\nAdjust filter criteria or check data values",
            )

        # Save results to analysis directory
        return save_df_to_analysis_dir(ctx, filtered_df, output_filename)

    except Exception as e:
        raise ModelRetry(f"Value filtering failed: {str(e)}")


def filter_by_multiple_conditions(
    ctx: RunContext[FinnDeps], file_path: str, *, conditions_dict: dict[str, Any], output_filename: str
) -> str:
    """
    Filter DataFrame by multiple conditions using AND logic.

    Args:
        file_path: Path to the input file
        conditions_dict: Dictionary of conditions {column: value} or {column: 'operator:value'}
        output_filename: Filename to save filtered results

    Returns:
        Path: Path to saved filtered DataFrame

    Example:
        >>> result_path = FILTER_BY_MULTIPLE_CONDITIONS(
        ...     "data.parquet",
        ...     conditions_dict={'region': 'North', 'sales': '>:1000', 'status': 'active'},
        ...     output_filename='filtered_data.parquet'
        ... )
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Input validation
    df = _validate_dataframe_input(df, "FILTER_BY_MULTIPLE_CONDITIONS")

    if not conditions_dict:
        raise ModelRetry("Conditions dictionary cannot be empty")

    try:
        filter_expressions: list[pl.Expr] = []

        for column, condition in conditions_dict.items():
            # Validate column exists
            _validate_column_exists(df, column, "FILTER_BY_MULTIPLE_CONDITIONS")

            # Parse condition
            if isinstance(condition, str) and ":" in condition:
                # Format: 'operator:value' (e.g., '>:1000')
                operator, value_str = condition.split(":", 1)
                # Try to convert value to appropriate type
                try:
                    # Try int first, then float, then keep as string
                    if value_str.isdigit() or (value_str.startswith("-") and value_str[1:].isdigit()):
                        value = int(value_str)
                    elif "." in value_str:
                        value = float(value_str)
                    else:
                        value = value_str
                except ValueError:
                    value = value_str
            else:
                # Direct equality comparison
                operator = "=="
                value = condition

            # Create filter expression
            filter_expr = _create_operator_expression(column, operator, value, "FILTER_BY_MULTIPLE_CONDITIONS")
            filter_expressions.append(filter_expr)

        # Combine all conditions with AND logic
        combined_filter = filter_expressions[0]
        for expr in filter_expressions[1:]:
            combined_filter = combined_filter & expr

        # Core filtering operation
        filtered_df = df.filter(combined_filter)

        # Validate results
        if filtered_df.is_empty():
            raise ModelRetry(
                f"No records found matching all conditions: {conditions_dict}\nRelax filter criteria or check data values",
            )

        # Save results to analysis directory
        return save_df_to_analysis_dir(ctx, filtered_df, output_filename)

    except Exception as e:
        raise ModelRetry(f"Multiple conditions filtering failed: {str(e)}")


def top_n(
    ctx: RunContext[FinnDeps],
    file_path: str,
    *,
    column: str,
    n: int,
    output_filename: str,
    ascending: bool = False,
) -> str:
    """
    Select top N records by value using Polars optimized top_k operation.

    Args:
        file_path: Path to the input file
        column: Column to sort by
        n: Number of records to select
        ascending: Sort order (False for descending/top values, True for ascending)
        output_filename: Filename to save selected results

    Returns:
        Path: Path to saved DataFrame with top N records

    Example:
        >>> result_path = TOP_N(
        ...     "customers.parquet",
        ...     column='revenue',
        ...     n=10,
        ...     ascending=False,
        ...     output_filename='top_10_customers.parquet'
        ... )
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Input validation
    df = _validate_dataframe_input(df, "TOP_N")
    _validate_column_exists(df, column, "TOP_N")

    if not isinstance(n, int) or n <= 0:
        raise ModelRetry("n must be a positive integer")

    if n > len(df):
        raise ModelRetry(
            f"Requested {n} records but DataFrame only has {len(df)} rows\nReduce n to {len(df)} or less"
        )

    try:
        if ascending:
            # For ascending order, we want the smallest values (bottom_k)
            selected_df = df.bottom_k(n, by=column)
        else:
            # For descending order, we want the largest values (top_k)
            selected_df = df.top_k(n, by=column)

        # Save results to analysis directory
        return save_df_to_analysis_dir(ctx, selected_df, output_filename)

    except Exception as e:
        raise ModelRetry(f"TOP_N selection failed: {str(e)}")


def bottom_n(ctx: RunContext[FinnDeps], file_path: str, *, column: str, n: int, output_filename: str) -> str:
    """
    Select bottom N records by value using Polars optimized bottom_k operation.

    Args:
        file_path: Path to the input file
        column: Column to sort by
        n: Number of records to select
        output_filename: Filename to save selected results

    Returns:
        Path: Path to saved DataFrame with bottom N records

    Example:
        >>> result_path = BOTTOM_N(
        ...     "products.parquet",
        ...     column='profit_margin',
        ...     n=5,
        ...     output_filename='lowest_margin_products.parquet'
        ... )
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Input validation
    df = _validate_dataframe_input(df, "BOTTOM_N")
    _validate_column_exists(df, column, "BOTTOM_N")

    if not isinstance(n, int) or n <= 0:
        raise ModelRetry("n must be a positive integer")

    if n > len(df):
        raise ModelRetry(
            f"Requested {n} records but DataFrame only has {len(df)} rows\nReduce n to {len(df)} or less"
        )

    try:
        # Use Polars bottom_k for optimal performance
        selected_df = df.bottom_k(n, by=column)

        # Save results to analysis directory
        return save_df_to_analysis_dir(ctx, selected_df, output_filename)

    except Exception as e:
        raise ModelRetry(f"BOTTOM_N selection failed: {str(e)}")


def sample_data(
    ctx: RunContext[FinnDeps],
    file_path: str,
    *,
    n_samples: int,
    random_state: int | None = None,
    output_filename: str,
) -> str:
    """
    Sample random records from DataFrame using Polars optimized sampling.

    Args:
        file_path: Path to the input file
        n_samples: Number of samples to take
        random_state: Random state for reproducibility (optional)
        output_filename: Filename to save sampled results

    Returns:
        Path: Path to saved DataFrame with sampled records

    Example:
        >>> result_path = SAMPLE_DATA(
        ...     "large_dataset.parquet",
        ...     n_samples=1000,
        ...     random_state=42,
        ...     output_filename='sample_data.parquet'
        ... )
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Input validation
    df = _validate_dataframe_input(df, "SAMPLE_DATA")

    if not isinstance(n_samples, int) or n_samples <= 0:
        raise ModelRetry("n_samples must be a positive integer")

    if n_samples > len(df):
        raise ModelRetry(
            f"Requested {n_samples} samples but DataFrame only has {len(df)} rows\nReduce n_samples to {len(df)} or less, or use sampling with replacement",
        )

    try:
        # Use Polars sample method for optimal performance
        if random_state is not None:
            sampled_df = df.sample(n=n_samples, seed=random_state)
        else:
            sampled_df = df.sample(n=n_samples)

        # Save results to analysis directory
        return save_df_to_analysis_dir(ctx, sampled_df, output_filename)

    except Exception as e:
        raise ModelRetry(f"Data sampling failed: {str(e)}")
