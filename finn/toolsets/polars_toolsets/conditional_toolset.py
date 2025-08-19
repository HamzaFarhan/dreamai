from datetime import datetime
from decimal import Decimal, getcontext

import polars as pl
from pydantic import BaseModel
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_file

getcontext().prec = 28


class Condition(BaseModel):
    condition_column: str
    condition: str


def _is_iso_date(value_str: str) -> bool:
    """Check if a string is in ISO date format."""
    try:
        datetime.fromisoformat(value_str.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _parse_condition(condition: str, column_expr: pl.Expr) -> pl.Expr:
    """Parse a condition string and return a Polars expression."""
    condition = condition.strip()

    # Handle comparison operators
    if condition.startswith(">="):
        value_str = condition[2:].strip()
        if _is_iso_date(value_str):
            date_value = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
            return column_expr.str.to_datetime() >= date_value
        else:
            value = float(value_str)
            return column_expr >= value
    elif condition.startswith("<="):
        value_str = condition[2:].strip()
        if _is_iso_date(value_str):
            date_value = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
            return column_expr.str.to_datetime() <= date_value
        else:
            value = float(value_str)
            return column_expr <= value
    elif condition.startswith(">"):
        value_str = condition[1:].strip()
        if _is_iso_date(value_str):
            date_value = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
            return column_expr.str.to_datetime() > date_value
        else:
            value = float(value_str)
            return column_expr > value
    elif condition.startswith("<"):
        value_str = condition[1:].strip()
        if _is_iso_date(value_str):
            date_value = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
            return column_expr.str.to_datetime() < date_value
        else:
            value = float(value_str)
            return column_expr < value
    elif condition.startswith("="):
        value_str = condition[1:].strip()
        if _is_iso_date(value_str):
            date_value = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
            return column_expr.str.to_datetime() == date_value
        else:
            try:
                value = float(value_str)
                return column_expr == value
            except ValueError:
                # String comparison
                return column_expr == value_str.strip("\"'")
    elif condition.startswith("!=") or condition.startswith("<>"):
        value_str = condition[2:].strip()
        if _is_iso_date(value_str):
            date_value = datetime.fromisoformat(value_str.replace("Z", "+00:00"))
            return column_expr.str.to_datetime() != date_value
        else:
            try:
                value = float(value_str)
                return column_expr != value
            except ValueError:
                # String comparison
                return column_expr != value_str.strip("\"'")
    else:
        # Try direct equality comparison
        if _is_iso_date(condition):
            date_value = datetime.fromisoformat(condition.replace("Z", "+00:00"))
            return column_expr.str.to_datetime() == date_value
        else:
            try:
                value = float(condition)
                return column_expr == value
            except ValueError:
                # String comparison
                return column_expr == condition.strip("\"'")


def sumif(
    ctx: RunContext[FinnDeps],
    file_path: str,
    condition_column: str,
    condition: str,
    sum_column: str | None = None,
) -> Decimal:
    """
    Sum numbers that meet one condition.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        condition_column: Name of the column to evaluate condition on
        condition: Condition string (e.g., ">100", "=Sales", "<=50")
        sum_column: Name of the column to sum (defaults to condition_column)

    Returns:
        Sum of values meeting the condition

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30], "B": [100, 200, 300]})
        >>> sumif(df, "A", ">15", "B")
        500.0

        >>> sumif("data.csv", "sales", ">1000")
        # Reads data.csv and returns sum of sales where sales > 1000
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if sum_column is None:
        sum_column = condition_column
    try:
        condition_expr = _parse_condition(condition, pl.col(condition_column))
        result = df.select(pl.col(sum_column).filter(condition_expr).sum()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error computing sumif: {e}")


def sumifs(
    ctx: RunContext[FinnDeps],
    file_path: str,
    sum_column: str,
    conditions: list[Condition],
) -> Decimal:
    """
    Sum numbers that meet multiple conditions.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        sum_column: Name of the column to sum
        conditions: List of conditions to apply

    Returns:
        Sum of values meeting all conditions

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30], "B": [100, 200, 300], "C": ["X", "Y", "X"]})
        >>> sumifs(df, "B", A=">15", C="=X")
        300.0
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        filter_expr = pl.lit(True)
        for condition in conditions:
            condition_expr = _parse_condition(condition.condition, pl.col(condition.condition_column))
            filter_expr = filter_expr & condition_expr

        result = df.select(pl.col(sum_column).filter(filter_expr).sum()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error computing sumifs: {e}")


def countif(
    ctx: RunContext[FinnDeps],
    file_path: str,
    condition_column: str,
    condition: str,
) -> int:
    """
    Count cells that meet one condition.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        condition_column: Name of the column to evaluate condition on
        condition: Condition string (e.g., ">100", "=Sales", "<=50")

    Returns:
        Count of cells meeting the condition

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30, 40]})
        >>> countif(df, "A", ">25")
        2
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    try:
        condition_expr = _parse_condition(condition, pl.col(condition_column))
        result = df.select(condition_expr.sum()).item()
        return int(result)
    except Exception as e:
        raise ModelRetry(f"Error computing countif: {e}")


def countifs(ctx: RunContext[FinnDeps], file_path: str, conditions: list[Condition]) -> int:
    """
    Count cells that meet multiple conditions.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        conditions: List of conditions to apply

    Returns:
        Count of cells meeting all conditions

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30], "B": [100, 200, 300], "C": ["X", "Y", "X"]})
        >>> countifs(df, A=">15", C="=X")
        1
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    try:
        filter_expr = pl.lit(True)
        for condition in conditions:
            condition_expr = _parse_condition(condition.condition, pl.col(condition.condition_column))
            filter_expr = filter_expr & condition_expr

        result = df.select(filter_expr.sum()).item()
        return int(result)
    except Exception as e:
        raise ModelRetry(f"Error computing countifs: {e}")


def averageif(
    ctx: RunContext[FinnDeps],
    file_path: str,
    condition_column: str,
    condition: str,
    average_column: str | None = None,
) -> Decimal:
    """
    Calculate average of cells that meet one condition.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        condition_column: Name of the column to evaluate condition on
        condition: Condition string (e.g., ">100", "=Sales", "<=50")
        average_column: Name of the column to average (defaults to condition_column)

    Returns:
        Average of values meeting the condition

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30], "B": [100, 200, 300]})
        >>> averageif(df, "A", ">15", "B")
        250.0
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if average_column is None:
        average_column = condition_column
    try:
        condition_expr = _parse_condition(condition, pl.col(condition_column))
        result = df.select(pl.col(average_column).filter(condition_expr).mean()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error computing averageif: {e}")


def averageifs(
    ctx: RunContext[FinnDeps],
    file_path: str,
    average_column: str,
    conditions: list[Condition],
) -> Decimal:
    """
    Calculate average of cells that meet multiple conditions.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        average_column: Name of the column to average
        conditions: List of conditions to apply

    Returns:
        Average of values meeting all conditions

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30], "B": [100, 200, 300], "C": ["X", "Y", "X"]})
        >>> averageifs(df, "B", A=">15", C="=X")
        300.0
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    try:
        filter_expr = pl.lit(True)
        for condition in conditions:
            condition_expr = _parse_condition(condition.condition, pl.col(condition.condition_column))
            filter_expr = filter_expr & condition_expr

        result = df.select(pl.col(average_column).filter(filter_expr).mean()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error computing averageifs: {e}")


def maxifs(
    ctx: RunContext[FinnDeps],
    file_path: str,
    max_column: str,
    conditions: list[Condition],
) -> Decimal:
    """
    Find maximum value based on multiple criteria.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        max_column: Name of the column to find maximum value
        conditions: List of conditions to apply

    Returns:
        Maximum value meeting all conditions

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30], "B": [100, 200, 300], "C": ["X", "Y", "X"]})
        >>> maxifs(df, "B", A=">15", C="=X")
        300.0
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    try:
        filter_expr = pl.lit(True)
        for condition in conditions:
            condition_expr = _parse_condition(condition.condition, pl.col(condition.condition_column))
            filter_expr = filter_expr & condition_expr

        result = df.select(pl.col(max_column).filter(filter_expr).max()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error computing maxifs: {e}")


def minifs(
    ctx: RunContext[FinnDeps],
    file_path: str,
    min_column: str,
    conditions: list[Condition],
) -> Decimal:
    """
    Find minimum value based on multiple criteria.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        min_column: Name of the column to find minimum value
        conditions: List of conditions to apply

    Returns:
        Minimum value meeting all conditions

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30], "B": [100, 200, 300], "C": ["X", "Y", "X"]})
        >>> minifs(df, "B", A=">15", C="=X")
        300.0
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    try:
        filter_expr = pl.lit(True)
        for condition in conditions:
            condition_expr = _parse_condition(condition.condition, pl.col(condition.condition_column))
            filter_expr = filter_expr & condition_expr

        result = df.select(pl.col(min_column).filter(filter_expr).min()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error computing minifs: {e}")


def sumproduct(ctx: RunContext[FinnDeps], file_path: str, *columns: str) -> Decimal:
    """
    Sum the products of corresponding ranges.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        *columns: Column names to multiply together

    Returns:
        Sum of products

    Example:
        >>> df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        >>> sumproduct(df, "A", "B")
        32.0  # (1*4) + (2*5) + (3*6) = 4 + 10 + 18 = 32
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if len(columns) < 2:
        raise ModelRetry("SUMPRODUCT requires at least 2 columns")

    # Start with first column
    product_expr = pl.col(columns[0])

    # Multiply by remaining columns
    for col in columns[1:]:
        product_expr = product_expr * pl.col(col)

    result = df.select(product_expr.sum()).item()
    return Decimal(str(result))


def aggregate(
    ctx: RunContext[FinnDeps],
    file_path: str,
    function_num: int,
    options: int,
    column: str,
) -> Decimal:
    """
    Perform various aggregations with error handling and filtering.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        function_num: Function number (1=AVERAGE, 2=COUNT, 3=COUNTA, 4=MAX, 5=MIN, 6=PRODUCT, 9=SUM)
        options: Options for handling errors and hidden rows (5=ignore errors)
        column: Name of the column to aggregate

    Returns:
        Aggregated value

    Example:
        >>> df = pl.DataFrame({"A": [1, 2, 3, 4, 5]})
        >>> aggregate(df, 9, 5, "A")  # SUM ignoring errors
        15.0
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Handle options - if 5, ignore errors (nulls)
    col_expr = pl.col(column)
    if options == 5:
        col_expr = col_expr.drop_nulls()

    # Apply function based on function_num
    if function_num == 1:  # AVERAGE
        result = df.select(col_expr.mean()).item()
    elif function_num == 2:  # COUNT
        result = df.select(col_expr.count()).item()
        return Decimal(str(result))
    elif function_num == 3:  # COUNTA
        result = df.select(col_expr.count()).item()
        return Decimal(str(result))
    elif function_num == 4:  # MAX
        result = df.select(col_expr.max()).item()
    elif function_num == 5:  # MIN
        result = df.select(col_expr.min()).item()
    elif function_num == 6:  # PRODUCT
        result = df.select(col_expr.product()).item()
    elif function_num == 9:  # SUM
        result = df.select(col_expr.sum()).item()
    else:
        raise ModelRetry(f"Unsupported function number: {function_num}")

    return Decimal(str(result))


def subtotal(ctx: RunContext[FinnDeps], file_path: str, function_num: int, column: str) -> Decimal:
    """
    Calculate subtotals with filtering capability.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        function_num: Function number (101=AVERAGE, 102=COUNT, 103=COUNTA, 104=MAX, 105=MIN, 106=PRODUCT, 109=SUM)
        column: Name of the column to aggregate

    Returns:
        Subtotal value

    Example:
        >>> df = pl.DataFrame({"A": [1, 2, 3, 4, 5]})
        >>> subtotal(df, 109, "A")  # SUM of visible cells
        15.0
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    col_expr = pl.col(column)

    # Apply function based on function_num (100+ means ignore hidden rows, but we don't have that info)
    base_func = function_num % 100

    if base_func == 1:  # AVERAGE
        result = df.select(col_expr.mean()).item()
    elif base_func == 2:  # COUNT
        result = df.select(col_expr.count()).item()
        return Decimal(str(result))
    elif base_func == 3:  # COUNTA
        result = df.select(col_expr.count()).item()
        return Decimal(str(result))
    elif base_func == 4:  # MAX
        result = df.select(col_expr.max()).item()
    elif base_func == 5:  # MIN
        result = df.select(col_expr.min()).item()
    elif base_func == 6:  # PRODUCT
        result = df.select(col_expr.product()).item()
    elif base_func == 9:  # SUM
        result = df.select(col_expr.sum()).item()
    else:
        raise ModelRetry(f"Unsupported function number: {function_num}")

    return Decimal(str(result))


def countblank(ctx: RunContext[FinnDeps], file_path: str, column: str) -> int:
    """
    Count blank/empty cells in a range.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        column: Name of the column to count blank cells

    Returns:
        Count of blank cells

    Example:
        >>> df = pl.DataFrame({"A": [1, None, 3, None, 5]})
        >>> countblank(df, "A")
        2
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    result = df.select(pl.col(column).is_null().sum()).item()
    return int(result)


def counta(ctx: RunContext[FinnDeps], file_path: str, column: str) -> int:
    """
    Count non-empty cells in a range.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        column: Name of the column to count non-empty cells

    Returns:
        Count of non-empty cells

    Example:
        >>> df = pl.DataFrame({"A": [1, None, 3, None, 5]})
        >>> counta(df, "A")
        3
    """
    try:
        df = load_file(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    result = df.select(pl.col(column).is_not_null().sum()).item()
    return int(result)
