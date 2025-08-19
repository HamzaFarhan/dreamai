from collections.abc import Callable
from typing import Literal

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_file, save_df_to_analysis_dir


def create_pivot_table(
    ctx: RunContext[FinnDeps],
    file_path: str,
    index_cols: list[str],
    value_cols: list[str],
    column_col: str,
    agg_func: Literal["sum", "mean", "count", "min", "max"],
    analysis_result_file_name: str,
) -> str:
    """
    Create pivot tables with aggregations by groups.

    Args:
        file_path: Path to the CSV or Parquet file
        index_cols: Columns to use as index
        value_cols: Columns to aggregate
        column_col: Column to pivot on (becomes new columns)
        agg_func: Aggregation function to apply
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing pivot table

    Example:
        >>> create_pivot_table("sales.parquet", ['region'], ['revenue'], 'product', 'sum', 'pivot_result')
        # Returns path to saved pivot table
    """
    try:
        df = load_file(ctx, file_path)

        # Create pivot table
        if value_cols:
            agg_expr = getattr(pl.col(value_cols[0]), agg_func)()
            result_df = df.pivot(
                on=column_col,
                index=index_cols,
                values=value_cols[0],
                aggregate_function=agg_expr,
            )
        else:
            result_df = df.pivot(
                on=column_col,
                index=index_cols,
                values=None,
                aggregate_function=None,
            )

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in create_pivot_table: {e}")


def unpivot_data(
    ctx: RunContext[FinnDeps],
    file_path: str,
    id_vars: list[str],
    value_vars: list[str],
    analysis_result_file_name: str,
) -> str:
    """
    Transform wide data to long format.

    Args:
        file_path: Path to the CSV or Parquet file
        id_vars: Identifier columns to keep
        value_vars: Columns to unpivot
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame in long format

    Example:
        >>> unpivot_data("data.parquet", ['customer_id'], ['Q1', 'Q2', 'Q3', 'Q4'], 'unpivoted_data')
        # Returns path to saved unpivoted data
    """
    try:
        df = load_file(ctx, file_path)

        # Unpivot the data
        result_df = df.unpivot(index=id_vars, on=value_vars, variable_name="variable", value_name="value")

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in unpivot_data: {e}")


def group_by(
    ctx: RunContext[FinnDeps],
    file_path: str,
    group_cols: list[str],
    agg_func: Literal["sum", "mean", "count", "min", "max"],
    analysis_result_file_name: str,
) -> str:
    """
    Group data and apply aggregation functions.

    Args:
        file_path: Path to the CSV or Parquet file
        group_cols: Columns to group by
        agg_func: Aggregation function to apply
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with grouped data

    Example:
        >>> group_by("sales.parquet", ['category'], 'sum', 'grouped_sales')
        # Returns path to saved grouped data
    """
    try:
        df = load_file(ctx, file_path)

        # Group and aggregate
        agg_exprs: list[pl.Expr] = []
        for col in df.columns:
            if col not in group_cols:
                agg_exprs.append(getattr(pl.col(col), agg_func)().alias(f"{col}_{agg_func}"))

        result_df = df.group_by(group_cols).agg(*agg_exprs)

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in group_by: {e}")


def cross_tabulation(
    ctx: RunContext[FinnDeps],
    file_path: str,
    row_vars: list[str],
    col_vars: list[str],
    value_vars: list[str],
    analysis_result_file_name: str,
) -> str:
    """
    Create cross-tabulation tables.

    Args:
        file_path: Path to the CSV or Parquet file
        row_vars: Row variables for cross-tabulation
        col_vars: Column variables for cross-tabulation
        value_vars: Value columns to aggregate
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing cross-tabulation

    Example:
        >>> cross_tabulation("data.parquet", ['region'], ['product'], ['sales'], 'crosstab_result')
        # Returns path to saved cross-tabulation table
    """
    try:
        df = load_file(ctx, file_path)

        # Create cross-tabulation
        result_df = df.pivot(on=col_vars, index=row_vars, values=value_vars, aggregate_function="sum")

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in cross_tabulation: {e}")


def group_by_agg(
    ctx: RunContext[FinnDeps],
    file_path: str,
    group_by_cols: list[str],
    agg_dict: dict[str, list[str]],
    analysis_result_file_name: str,
) -> str:
    """
    Group a DataFrame by one or more columns and then apply one or more aggregation functions.

    Args:
        file_path: Path to the CSV or Parquet file
        group_by_cols: List of columns to group by
        agg_dict: Dictionary mapping columns to list of aggregation functions
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with grouped aggregations

    Example:
        >>> group_by_agg("data.parquet", ['region'], {'revenue': ['sum'], 'customers': ['count']}, 'grouped_agg')
        # Returns path to saved grouped aggregation results
    """
    try:
        df = load_file(ctx, file_path)

        # Build aggregation expressions
        agg_map: dict[str, Callable[[str], pl.Expr]] = {
            "sum": pl.sum,
            "mean": pl.mean,
            "count": pl.count,
            "min": pl.min,
            "max": pl.max,
        }
        agg_exprs: list[pl.Expr] = []
        for col, funcs in agg_dict.items():
            for func in funcs:
                if func in agg_map:
                    agg_func_expr = agg_map[func]
                    agg_exprs.append(agg_func_expr(col).alias(f"{col}_{func}"))
        result_df = df.group_by(group_by_cols).agg(*agg_exprs)

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in group_by_agg: {e}")


def stack_data(
    ctx: RunContext[FinnDeps], file_path: str, columns_to_stack: list[str], analysis_result_file_name: str
) -> str:
    """
    Stack multiple columns into single column.

    Args:
        file_path: Path to the CSV or Parquet file
        columns_to_stack: Columns to stack
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with stacked columns

    Example:
        >>> stack_data("data.parquet", ['Q1', 'Q2', 'Q3', 'Q4'], 'stacked_data')
        # Returns path to saved stacked data
    """
    try:
        df = load_file(ctx, file_path)

        # Stack columns using unpivot
        id_vars = [col for col in df.columns if col not in columns_to_stack]
        result_df = df.unpivot(index=id_vars, on=columns_to_stack, variable_name="quarter", value_name="value")

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in stack_data: {e}")


def unstack_data(
    ctx: RunContext[FinnDeps], file_path: str, level_to_unstack: str, analysis_result_file_name: str
) -> str:
    """
    Unstack index level to columns.

    Args:
        file_path: Path to the CSV or Parquet file
        level_to_unstack: Level/column to unstack
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with unstacked data

    Example:
        >>> unstack_data("stacked_data.parquet", 'quarter', 'unstacked_data')
        # Returns path to saved unstacked data
    """
    try:
        df = load_file(ctx, file_path)

        # Unstack by pivoting
        # Assuming the data has a value column and the level column to unstack
        value_col = [col for col in df.columns if col not in [level_to_unstack] and col != "value"]
        if value_col and "value" in df.columns:
            result_df = df.pivot(
                values="value",
                index=[col for col in df.columns if col not in [level_to_unstack, "value"]],
                on=level_to_unstack,
            )
        else:
            # Fallback if no explicit value column found
            result_df = df

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in unstack_data: {e}")


def merge_data(
    ctx: RunContext[FinnDeps],
    left_path: str,
    right_path: str,
    join_keys: str | list[str],
    join_type: Literal["inner", "left", "outer", "cross"],
    analysis_result_file_name: str,
) -> str:
    """
    Merge/join two DataFrames.

    Args:
        left_path: Path to the left CSV or Parquet file
        right_path: Path to the right CSV or Parquet file
        join_keys: Key(s) to join on
        join_type: Type of join to perform
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with merged data

    Example:
        >>> merge_data("sales.parquet", "customer.parquet", 'customer_id', 'left', 'merged_data')
        # Returns path to saved merged data
    """
    try:
        left_df = load_file(ctx, left_path)
        right_df = load_file(ctx, right_path)

        # Perform merge/join
        if isinstance(join_keys, str):
            join_keys = [join_keys]

        result_df = left_df.join(right_df, on=join_keys, how=join_type)

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in merge_data: {e}")


def concat_data(
    ctx: RunContext[FinnDeps], file_paths: list[str], axis: Literal[0, 1], analysis_result_file_name: str
) -> str:
    """
    Concatenate DataFrames.

    Args:
        file_paths: List of paths to CSV or Parquet files
        axis: 0 for row-wise concatenation, 1 for column-wise
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with concatenated data

    Example:
        >>> concat_data(["df1.parquet", "df2.parquet", "df3.parquet"], axis=0, 'concatenated_data')
        # Returns path to saved concatenated data
    """
    try:
        dfs = [load_file(ctx, path) for path in file_paths]

        # Concatenate DataFrames
        if axis == 0:
            # Vertical concatenation (stack rows)
            result_df = pl.concat(dfs, how="vertical")
        else:
            # Horizontal concatenation (join columns)
            result_df = pl.concat(dfs, how="horizontal")

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in concat_data: {e}")


def fill_forward(ctx: RunContext[FinnDeps], file_path: str, column: str, analysis_result_file_name: str) -> str:
    """
    Forward fill missing values.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Column to forward fill
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with forward filled values

    Example:
        >>> fill_forward("data.parquet", 'revenue_series', 'filled_data')
        # Returns path to saved data with forward filled values
    """
    try:
        df = load_file(ctx, file_path)

        # Forward fill missing values in specified column
        result_df = df.with_columns(pl.col(column).forward_fill().alias(f"{column}_filled"))

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in fill_forward: {e}")


def interpolate_values(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    method: Literal["linear", "nearest"],
    analysis_result_file_name: str,
) -> str:
    """
    Interpolate missing values.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Column to interpolate
        method: Interpolation method ('linear' or 'nearest')
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with interpolated values

    Example:
        >>> interpolate_values("data.parquet", 'data_series', 'linear', 'interpolated_data')
        # Returns path to saved data with interpolated values
    """
    try:
        df = load_file(ctx, file_path)

        # Interpolate missing values in specified column
        if method == "linear":
            result_df = df.with_columns(pl.col(column).interpolate().alias(f"{column}_interpolated"))
        else:
            result_df = df.with_columns(
                pl.col(column)
                .fill_null(strategy="forward")
                .fill_null(strategy="backward")
                .alias(f"{column}_interpolated")
            )

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in interpolate_values: {e}")
