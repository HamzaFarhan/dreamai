from decimal import Decimal, getcontext

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_df, save_df_to_analysis_dir

getcontext().prec = 28


def logical_if(
    ctx: RunContext[FinnDeps],
    file_path: str,
    logical_test_column: str,
    analysis_result_file_name: str,
    value_if_true_column: str | None = None,
    value_if_false_column: str | None = None,
    value_if_true_literal: str | float | int | None = None,
    value_if_false_literal: str | float | int | None = None,
) -> str:
    """
    Return different values depending on whether a condition is met.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        logical_test_column: Name of the column containing boolean test values
        value_if_true_column: Column name to use when condition is true (optional)
        value_if_false_column: Column name to use when condition is false (optional)
        value_if_true_literal: Literal value to use when condition is true (optional)
        value_if_false_literal: Literal value to use when condition is false (optional)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing IF results

    Example:
        >>> logical_if("data.csv", "budget_check", value_if_true_literal="Above Budget", value_if_false_literal="Within Budget", "if_results")
        # Returns path to saved DataFrame with conditional values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Determine value_if_true
    if value_if_true_column is not None:
        value_if_true = pl.col(value_if_true_column)
    elif value_if_true_literal is not None:
        value_if_true = pl.lit(value_if_true_literal)
    else:
        raise ModelRetry("Either value_if_true_column or value_if_true_literal must be provided")

    # Determine value_if_false
    if value_if_false_column is not None:
        value_if_false = pl.col(value_if_false_column)
    elif value_if_false_literal is not None:
        value_if_false = pl.lit(value_if_false_literal)
    else:
        raise ModelRetry("Either value_if_false_column or value_if_false_literal must be provided")

    result_df = df.with_columns(
        pl.when(pl.col(logical_test_column)).then(value_if_true).otherwise(value_if_false).alias("if_result")
    )

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_iferror(
    ctx: RunContext[FinnDeps],
    file_path: str,
    value_column: str,
    analysis_result_file_name: str,
    value_if_error_column: str | None = None,
    value_if_error_literal: str | float | int | None = None,
) -> str:
    """
    Return a specified value if a formula results in an error.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        value_column: Name of the column to check for errors
        value_if_error_column: Column name to use when error is found (optional)
        value_if_error_literal: Literal value to use when error is found (optional)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing IFERROR results

    Example:
        >>> logical_iferror("data.csv", "formula_result", value_if_error_literal="Error Found", "iferror_results")
        # Returns path to saved DataFrame with error handling
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Determine value_if_error
    if value_if_error_column is not None:
        value_if_error = pl.col(value_if_error_column)
    elif value_if_error_literal is not None:
        value_if_error = pl.lit(value_if_error_literal)
    else:
        raise ModelRetry("Either value_if_error_column or value_if_error_literal must be provided")

    result_df = df.with_columns(
        pl.when(pl.col(value_column).is_null())
        .then(value_if_error)
        .otherwise(pl.col(value_column))
        .alias("iferror_result")
    )

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_ifna(
    ctx: RunContext[FinnDeps],
    file_path: str,
    value_column: str,
    analysis_result_file_name: str,
    value_if_na_column: str | None = None,
    value_if_na_literal: str | float | int | None = None,
) -> str:
    """
    Return a specified value if a formula results in #N/A error.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        value_column: Name of the column to check for N/A values
        value_if_na_column: Column name to use when N/A is found (optional)
        value_if_na_literal: Literal value to use when N/A is found (optional)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing IFNA results

    Example:
        >>> logical_ifna("data.csv", "lookup_result", value_if_na_literal="Not Found", "ifna_results")
        # Returns path to saved DataFrame with N/A handling
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Determine value_if_na
    if value_if_na_column is not None:
        value_if_na = pl.col(value_if_na_column)
    elif value_if_na_literal is not None:
        value_if_na = pl.lit(value_if_na_literal)
    else:
        raise ModelRetry("Either value_if_na_column or value_if_na_literal must be provided")

    result_df = df.with_columns(
        pl.when(pl.col(value_column).is_null())
        .then(value_if_na)
        .otherwise(pl.col(value_column))
        .alias("ifna_result")
    )

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_ifs(
    ctx: RunContext[FinnDeps],
    file_path: str,
    conditions_and_values: list[tuple[str, str | float | int]],
    analysis_result_file_name: str,
) -> str:
    """
    Test multiple conditions without nesting several IF statements.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        conditions_and_values: List of tuples (condition_column, value) for each condition
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing IFS results

    Example:
        >>> logical_ifs("data.csv", [("high_check", "High"), ("medium_check", "Medium")], "ifs_results")
        # Returns path to saved DataFrame with multiple condition results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if not conditions_and_values:
        raise ModelRetry("At least one condition and value pair must be provided")

    # Build the when-then chain
    expr = pl.when(pl.col(conditions_and_values[0][0])).then(pl.lit(conditions_and_values[0][1]))

    for condition_col, value in conditions_and_values[1:]:
        expr = expr.when(pl.col(condition_col)).then(pl.lit(value))

    # Add final otherwise clause
    expr = expr.otherwise(pl.lit(None))

    result_df = df.with_columns(expr.alias("ifs_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_and(
    ctx: RunContext[FinnDeps],
    file_path: str,
    logical_columns: list[str],
    analysis_result_file_name: str,
) -> str:
    """
    Test if all conditions are true.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        logical_columns: List of column names containing boolean values
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing AND results

    Example:
        >>> logical_and("data.csv", ["condition1", "condition2"], "and_results")
        # Returns path to saved DataFrame with AND operation results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if not logical_columns:
        raise ModelRetry("At least one logical column must be provided")

    # Start with the first column
    expr = pl.col(logical_columns[0])

    # Chain AND operations for remaining columns
    for col in logical_columns[1:]:
        expr = expr & pl.col(col)

    result_df = df.with_columns(expr.alias("and_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_or(
    ctx: RunContext[FinnDeps],
    file_path: str,
    logical_columns: list[str],
    analysis_result_file_name: str,
) -> str:
    """
    Test if any condition is true.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        logical_columns: List of column names containing boolean values
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing OR results

    Example:
        >>> logical_or("data.csv", ["condition1", "condition2"], "or_results")
        # Returns path to saved DataFrame with OR operation results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if not logical_columns:
        raise ModelRetry("At least one logical column must be provided")

    # Start with the first column
    expr = pl.col(logical_columns[0])

    # Chain OR operations for remaining columns
    for col in logical_columns[1:]:
        expr = expr | pl.col(col)

    result_df = df.with_columns(expr.alias("or_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_not(
    ctx: RunContext[FinnDeps],
    file_path: str,
    logical_column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Reverse the logical value of a condition.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        logical_column: Name of the column containing boolean values
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing NOT results

    Example:
        >>> logical_not("data.csv", "condition", "not_results")
        # Returns path to saved DataFrame with NOT operation results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    result_df = df.with_columns(pl.col(logical_column).not_().alias("not_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_switch(
    ctx: RunContext[FinnDeps],
    file_path: str,
    expression_column: str,
    value_result_pairs: list[tuple[str | float | int, str | float | int]],
    analysis_result_file_name: str,
    default_value: str | float | int | None = None,
) -> str:
    """
    Compare expression against list of values and return corresponding result.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        expression_column: Name of the column to compare
        value_result_pairs: List of tuples (value_to_match, result_if_matched)
        default_value: Default value if no matches found (optional)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing SWITCH results

    Example:
        >>> logical_switch("data.csv", "grade", [(1, "One"), (2, "Two")], "Other", "switch_results")
        # Returns path to saved DataFrame with switch operation results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if not value_result_pairs:
        raise ModelRetry("At least one value-result pair must be provided")

    # Build the when-then chain
    expr = pl.when(pl.col(expression_column) == value_result_pairs[0][0]).then(pl.lit(value_result_pairs[0][1]))

    for value, result in value_result_pairs[1:]:
        expr = expr.when(pl.col(expression_column) == value).then(pl.lit(result))

    # Add default value
    if default_value is not None:
        expr = expr.otherwise(pl.lit(default_value))
    else:
        expr = expr.otherwise(pl.lit(None))

    result_df = df.with_columns(expr.alias("switch_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_xor(
    ctx: RunContext[FinnDeps],
    file_path: str,
    logical_columns: list[str],
    analysis_result_file_name: str,
) -> str:
    """
    Exclusive OR - returns TRUE if odd number of arguments are TRUE.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        logical_columns: List of column names containing boolean values
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing XOR results

    Example:
        >>> logical_xor("data.csv", ["condition1", "condition2", "condition3"], "xor_results")
        # Returns path to saved DataFrame with XOR operation results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if not logical_columns:
        raise ModelRetry("At least one logical column must be provided")

    # Count the number of True values
    true_count = pl.sum_horizontal([pl.col(col).cast(pl.Int32) for col in logical_columns])

    # XOR is true if odd number of inputs are true
    result_df = df.with_columns((true_count % 2 == 1).alias("xor_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def is_blank(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Test if cell is blank.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        column: Name of the column to test
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing ISBLANK results

    Example:
        >>> is_blank("data.csv", "value_column", "isblank_results")
        # Returns path to saved DataFrame with blank check results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    result_df = df.with_columns(pl.col(column).is_null().alias("is_blank_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def is_number(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Test if value is a number.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        column: Name of the column to test
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing ISNUMBER results

    Example:
        >>> is_number("data.csv", "value_column", "isnumber_results")
        # Returns path to saved DataFrame with number check results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Check if the column dtype is numeric
    column_dtype = df.schema[column]
    is_numeric = column_dtype.is_numeric()

    result_df = df.with_columns(pl.lit(is_numeric).alias("is_number_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def is_text(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Test if value is text.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        column: Name of the column to test
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing ISTEXT results

    Example:
        >>> is_text("data.csv", "value_column", "istext_results")
        # Returns path to saved DataFrame with text check results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Check if the column dtype is string
    column_dtype = df.schema[column]
    is_text = column_dtype == pl.String

    result_df = df.with_columns(pl.lit(is_text).alias("is_text_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def is_error(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Test if value is an error.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        column: Name of the column to test
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing ISERROR results

    Example:
        >>> is_error("data.csv", "calculation_result", "iserror_results")
        # Returns path to saved DataFrame with error check results
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    result_df = df.with_columns(pl.col(column).is_null().alias("is_error_result"))

    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def logical_and_scalar(ctx: RunContext[FinnDeps], file_path: str, logical_columns: list[str]) -> bool:
    """
    Test if all conditions are true across all rows (scalar result).

    Args:
        file_path: Path to the CSV or Parquet file
        logical_columns: List of column names containing boolean values

    Returns:
        True if all values in all specified columns are true, False otherwise

    Example:
        >>> logical_and_scalar("data.csv", ["condition1", "condition2"])
        True
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if not logical_columns:
        raise ModelRetry("At least one logical column must be provided")

    # Check if all values in all columns are true
    for col in logical_columns:
        # Use Decimal for consistency
        if not bool(Decimal(str(df.select(pl.col(col).all()).item()))):
            return False
    return True


def logical_or_scalar(ctx: RunContext[FinnDeps], file_path: str, logical_columns: list[str]) -> bool:
    """
    Test if any condition is true across all rows (scalar result).

    Args:
        file_path: Path to the CSV or Parquet file
        logical_columns: List of column names containing boolean values

    Returns:
        True if any value in any specified column is true, False otherwise

    Example:
        >>> logical_or_scalar("data.csv", ["condition1", "condition2"])
        True
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if not logical_columns:
        raise ModelRetry("At least one logical column must be provided")

    # Check if any value in any column is true
    for col in logical_columns:
        if bool(Decimal(str(df.select(pl.col(col).any()).item()))):
            return True
    return False
