from decimal import Decimal, getcontext
from typing import Literal

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_df, save_df_to_analysis_dir

getcontext().prec = 28


def stdev_p(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the standard deviation for a full population.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate population standard deviation

    Returns:
        Population standard deviation

    Example:
        =STDEV.P(data_range)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.col(column).std(ddof=0)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in stdev_p: {e}")


def stdev_s(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the standard deviation for a sample.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate sample standard deviation

    Returns:
        Sample standard deviation

    Example:
        =STDEV.S(data_range)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.col(column).std(ddof=1)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in stdev_s: {e}")


def var_p(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate variance for a population.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate population variance

    Returns:
        Population variance

    Example:
        =VAR.P(data_range)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.col(column).var(ddof=0)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in var_p: {e}")


def var_s(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate variance for a sample.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate sample variance

    Returns:
        Sample variance

    Example:
        =VAR.S(data_range)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.col(column).var(ddof=1)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in var_s: {e}")


def median(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Determine the middle value in a dataset.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate median

    Returns:
        Median value

    Example:
        =MEDIAN(data_range)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.col(column).median()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in median: {e}")


def mode(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Find the most frequently occurring value in a dataset.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to find mode

    Returns:
        Mode value (first if multiple)

    Example:
        =MODE(data_range)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.col(column).mode()).item(0, 0)
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in mode: {e}")


def correl(ctx: RunContext[FinnDeps], file_path: str, column1: str, column2: str) -> Decimal:
    """
    Measure the correlation between two datasets.

    Args:
        file_path: Path to the CSV or Parquet file
        column1: Name of the first column
        column2: Name of the second column

    Returns:
        Correlation coefficient (-1 to 1)

    Example:
        =CORREL(range1, range2)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.corr(column1, column2)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in correl: {e}")


def covariance_p(ctx: RunContext[FinnDeps], file_path: str, column1: str, column2: str) -> Decimal:
    """
    Calculate covariance for a population.

    Args:
        file_path: Path to the CSV or Parquet file
        column1: Name of the first column
        column2: Name of the second column

    Returns:
        Population covariance

    Example:
        =COVARIANCE.P(range1, range2)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.cov(column1, column2, ddof=0)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in covariance_p: {e}")


def covariance_s(ctx: RunContext[FinnDeps], file_path: str, column1: str, column2: str) -> Decimal:
    """
    Calculate covariance for a sample.

    Args:
        file_path: Path to the CSV or Parquet file
        column1: Name of the first column
        column2: Name of the second column

    Returns:
        Sample covariance

    Example:
        =COVARIANCE.S(range1, range2)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.cov(column1, column2, ddof=1)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in covariance_s: {e}")


def trend(
    ctx: RunContext[FinnDeps],
    file_path: str,
    known_ys: str,
    known_xs: str | None = None,
    new_xs: str | None = None,
    const: bool = True,
    analysis_result_file_name: str = "trend_results",
) -> str:
    """
    Predict future values based on linear trends.

    Args:
        file_path: Path to the CSV or Parquet file
        known_ys: Column name for known y values
        known_xs: Column name for known x values (optional)
        new_xs: Column name for new x values to predict (optional)
        const: If True, include constant term (default True)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to saved DataFrame with predicted values

    Example:
        =TREND(known_y's, [known_x's], [new_x's])
    """
    try:
        df = load_df(ctx, file_path)
        y = df.select(pl.col(known_ys)).to_series().to_list()
        if known_xs:
            x = df.select(pl.col(known_xs)).to_series().to_list()
        else:
            x = list(range(1, len(y) + 1))

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi**2 for xi in x)

        if const:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = sum_xy / sum_x2
            intercept = 0

        if new_xs:
            predict_x = df.select(pl.col(new_xs)).to_series().to_list()
        else:
            predict_x = list(range(len(y) + 1, len(y) + len(y) + 1))  # Predict next n values

        predicted = [intercept + slope * xi for xi in predict_x]

        result_df = pl.DataFrame({"predicted": [Decimal(str(p)) for p in predicted]})
        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in trend: {e}")


def forecast(
    ctx: RunContext[FinnDeps],
    file_path: str,
    new_x: float,
    known_ys: str,
    known_xs: str,
) -> Decimal:
    """
    Predict a future value based on linear regression.

    Args:
        file_path: Path to the CSV or Parquet file
        new_x: New x value to predict for
        known_ys: Column name for known y values
        known_xs: Column name for known x values

    Returns:
        Predicted value

    Example:
        =FORECAST(new_x, known_y's, known_x's)
    """
    try:
        df = load_df(ctx, file_path)
        y = df.select(pl.col(known_ys)).to_series().to_list()
        x = df.select(pl.col(known_xs)).to_series().to_list()

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (n - 1)
        var_x = sum((xi - mean_x) ** 2 for xi in x) / (n - 1)
        slope = cov / var_x
        intercept = mean_y - slope * mean_x

        result = intercept + slope * new_x
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in forecast: {e}")


def forecast_linear(
    ctx: RunContext[FinnDeps],
    file_path: str,
    new_x: float,
    known_ys: str,
    known_xs: str,
) -> Decimal:
    """
    Predict a future value based on linear regression (newer version).

    Args:
        file_path: Path to the CSV or Parquet file
        new_x: New x value to predict for
        known_ys: Column name for known y values
        known_xs: Column name for known x values

    Returns:
        Predicted value

    Example:
        =FORECAST.LINEAR(new_x, known_y's, known_x's)
    """
    # Same as forecast
    return forecast(ctx, file_path, new_x, known_ys, known_xs)


def growth(
    ctx: RunContext[FinnDeps],
    file_path: str,
    known_ys: str,
    known_xs: str | None = None,
    new_xs: str | None = None,
    const: bool = True,
    analysis_result_file_name: str = "growth_results",
) -> str:
    """
    Forecast exponential growth trends.

    Args:
        file_path: Path to the CSV or Parquet file
        known_ys: Column name for known y values
        known_xs: Column name for known x values (optional)
        new_xs: Column name for new x values to predict (optional)
        const: If True, include constant term (default True)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to saved DataFrame with predicted values

    Example:
        =GROWTH(known_y's, [known_x's], [new_x's])
    """
    try:
        import math

        df = load_df(ctx, file_path)
        y = [math.log(yi) for yi in df.select(pl.col(known_ys)).to_series().to_list() if yi > 0]
        if known_xs:
            x = df.select(pl.col(known_xs)).to_series().to_list()[: len(y)]
        else:
            x = list(range(1, len(y) + 1))

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi**2 for xi in x)

        if const:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = sum_xy / sum_x2
            intercept = 0

        if new_xs:
            predict_x = df.select(pl.col(new_xs)).to_series().to_list()
        else:
            predict_x = list(range(len(y) + 1, len(y) + len(y) + 1))

        predicted = [math.exp(intercept + slope * xi) for xi in predict_x]

        result_df = pl.DataFrame({"predicted": [Decimal(str(p)) for p in predicted]})
        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in growth: {e}")


def slope(ctx: RunContext[FinnDeps], file_path: str, known_ys: str, known_xs: str) -> Decimal:
    """
    Calculate slope of linear regression line.

    Args:
        file_path: Path to the CSV or Parquet file
        known_ys: Column name for known y values
        known_xs: Column name for known x values

    Returns:
        Slope value

    Example:
        SLOPE(B1:B10, A1:A10)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.cov(known_ys, known_xs, ddof=1) / pl.col(known_xs).var(ddof=1)).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in slope: {e}")


def intercept(ctx: RunContext[FinnDeps], file_path: str, known_ys: str, known_xs: str) -> Decimal:
    """
    Calculate y-intercept of linear regression line.

    Args:
        file_path: Path to the CSV or Parquet file
        known_ys: Column name for known y values
        known_xs: Column name for known x values

    Returns:
        Intercept value

    Example:
        INTERCEPT(B1:B10, A1:A10)
    """
    try:
        df = load_df(ctx, file_path)
        slope_val = slope(ctx, file_path, known_ys, known_xs)
        mean_y = df.select(pl.col(known_ys).mean()).item()
        mean_x = df.select(pl.col(known_xs).mean()).item()
        result = mean_y - float(slope_val) * mean_x
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in intercept: {e}")


def rsq(ctx: RunContext[FinnDeps], file_path: str, known_ys: str, known_xs: str) -> Decimal:
    """
    Calculate R-squared of linear regression.

    Args:
        file_path: Path to the CSV or Parquet file
        known_ys: Column name for known y values
        known_xs: Column name for known x values

    Returns:
        R-squared value

    Example:
        RSQ(B1:B10, A1:A10)
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.corr(known_ys, known_xs) ** 2).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in rsq: {e}")


def linest(
    ctx: RunContext[FinnDeps],
    file_path: str,
    known_ys: str,
    known_xs: str,
    const: bool = True,
    stats: bool = True,
    analysis_result_file_name: str = "linest_results",
) -> str:
    """
    Calculate linear regression statistics.

    Args:
        file_path: Path to the CSV or Parquet file
        known_ys: Column name for known y values
        known_xs: Column name for known x values
        const: If True, include constant term (default True)
        stats: If True, return additional stats (default True)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to saved DataFrame with regression statistics

    Example:
        LINEST(B1:B10, A1:A10, TRUE, TRUE)
    """
    try:
        df = load_df(ctx, file_path)
        y = df.select(pl.col(known_ys)).to_series().to_list()
        x = df.select(pl.col(known_xs)).to_series().to_list()

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi**2 for xi in x)
        sum_y2 = sum(yi**2 for yi in y)

        if const:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = sum_xy / sum_x2
            intercept = 0

        if stats:
            predicted = [intercept + slope * xi for xi in x]
            residuals = [yi - pi for yi, pi in zip(y, predicted)]
            ss_res = sum(r**2 for r in residuals)
            ss_tot = sum((yi - sum_y / n) ** 2 for yi in y)
            r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0
            df_res = n - 2 if const else n - 1
            se_slope = (
                (ss_res / df_res / (sum_x2 - sum_x**2 / n)) ** 0.5 if const else (ss_res / df_res / sum_x2) ** 0.5
            )
            # Add more stats as needed

            result_dict = {
                "slope": Decimal(str(slope)),
                "intercept": Decimal(str(intercept)),
                "r2": Decimal(str(r2)),
                "se_slope": Decimal(str(se_slope)),
                # Add more
            }
        else:
            result_dict = {"slope": Decimal(str(slope)), "intercept": Decimal(str(intercept))}

        result_df = pl.DataFrame(result_dict)
        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in linest: {e}")


def logest(
    ctx: RunContext[FinnDeps],
    file_path: str,
    known_ys: str,
    known_xs: str,
    const: bool = True,
    stats: bool = True,
    analysis_result_file_name: str = "logest_results",
) -> str:
    """
    Calculate exponential regression statistics.

    Args:
        file_path: Path to the CSV or Parquet file
        known_ys: Column name for known y values
        known_xs: Column name for known x values
        const: If True, include constant term (default True)
        stats: If True, return additional stats (default True)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to saved DataFrame with regression statistics

    Example:
        LOGEST(B1:B10, A1:A10, TRUE, TRUE)
    """
    try:
        import math

        df = load_df(ctx, file_path)
        y_log = [math.log(yi) for yi in df.select(pl.col(known_ys)).to_series().to_list() if yi > 0]
        x = df.select(pl.col(known_xs)).to_series().to_list()[: len(y_log)]

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y_log)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y_log))
        sum_x2 = sum(xi**2 for xi in x)

        if const:
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = sum_xy / sum_x2
            intercept = 0

        b = math.exp(slope)
        a = math.exp(intercept)

        if stats:
            # Similar to linest, calculate additional stats
            result_dict = {
                "b": Decimal(str(b)),
                "a": Decimal(str(a)),
                # Add more stats
            }
        else:
            result_dict = {"b": Decimal(str(b)), "a": Decimal(str(a))}

        result_df = pl.DataFrame(result_dict)
        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in logest: {e}")


def rank(
    ctx: RunContext[FinnDeps],
    file_path: str,
    number: float,
    ref_column: str,
    order: Literal[0, 1] = 0,
) -> Decimal:
    """
    Calculate rank of number in array.

    Args:
        file_path: Path to the CSV or Parquet file
        number: Number to rank
        ref_column: Column name for reference array
        order: 0 for descending (default), 1 for ascending

    Returns:
        Rank value

    Example:
        RANK(85, A1:A10, 0)
    """
    try:
        df = load_df(ctx, file_path)
        descending = order == 0
        result = df.select(
            (
                pl.col(ref_column)
                .rank(method="min", descending=descending)
                .filter(pl.col(ref_column) == number)
                .min()
            )
        ).item()
        return Decimal(str(result)) if result else Decimal("0")
    except Exception as e:
        raise ModelRetry(f"Error in rank: {e}")


def percentrank(
    ctx: RunContext[FinnDeps],
    file_path: str,
    ref_column: str,
    x: float,
    significance: int = 3,
) -> Decimal:
    """
    Calculate percentile rank.

    Args:
        file_path: Path to the CSV or Parquet file
        ref_column: Column name for array
        x: Value to rank
        significance: Number of significant digits (default 3)

    Returns:
        Percentile rank

    Example:
        PERCENTRANK(A1:A10, 85)
    """
    try:
        df = load_df(ctx, file_path)
        array = df.select(pl.col(ref_column)).to_series().drop_nulls().sort().to_list()
        n = len(array)
        if n == 0:
            return Decimal("0")

        rank = sum(1 for a in array if a < x) + (sum(1 for a in array if a == x) + 1) / 2
        pct = (rank - 1) / (n - 1)

        quant = Decimal("1").scaleb(-significance)
        return Decimal(str(pct)).quantize(quant)
    except Exception as e:
        raise ModelRetry(f"Error in percentrank: {e}")
