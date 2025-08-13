from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, getcontext

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from .file_toolset import load_df, save_df_to_analysis_dir
from .finn_deps import FinnDeps

getcontext().prec = 28


def calculate_sum(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the sum of a column in a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to sum

    Returns:
        Sum of the column values

    Example:
        >>> calculate_sum("data.parquet", "sales")
        # Reads data.parquet and returns sum of sales column
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).sum()).item()
    return Decimal(str(result))


def calculate_average(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the average (mean) of a column in a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to average

    Returns:
        Average of the column values

    Example:
        >>> calculate_average("data.csv", "sales")
        # Reads data.csv and returns average of sales column
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).mean()).item()
    return Decimal(str(result))


def calculate_min(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Find the minimum value in a column of a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to find minimum value

    Returns:
        Minimum value in the column

    Example:
        >>> calculate_min("data.csv", "sales")
        # Reads data.csv and returns minimum of sales column
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).min()).item()
    return Decimal(str(result))


def calculate_max(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Find the maximum value in a column of a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to find maximum value

    Returns:
        Maximum value in the column

    Example:
        >>> calculate_max("data.csv", "sales")
        # Reads data.csv and returns maximum of sales column
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).max()).item()
    return Decimal(str(result))


def calculate_product(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the product of a column in a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate product

    Returns:
        Product of the column values

    Example:
        >>> calculate_product("data.csv", "A")
        # Reads data.csv and returns product of column A
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).product()).item()
    return Decimal(str(result))


def calculate_median(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the median of a column in a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate median

    Returns:
        Median of the column values

    Example:
        >>> calculate_median("data.csv", "A")
        # Reads data.csv and returns median of column A
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).median()).item()
    return Decimal(str(result))


def calculate_mode(ctx: RunContext[FinnDeps], file_path: str, column: str) -> list[Decimal]:
    """
    Find the most frequently occurring value(s) in a column.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to find mode

    Returns:
        List of mode values (multiple if ties)

    Example:
        >>> calculate_mode("data.csv", "A")
        # Reads data.csv and returns mode(s) of column A
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    modes = df.select(pl.col(column).mode()).to_series().to_list()
    return [Decimal(str(m)) for m in modes if m is not None]


def calculate_percentile(ctx: RunContext[FinnDeps], file_path: str, column: str, percentile: float) -> Decimal:
    """
    Calculate the specified percentile of a column in a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column to calculate percentile
        percentile: Percentile value between 0 and 1

    Returns:
        Percentile value

    Example:
        >>> calculate_percentile("data.csv", "A", 0.5)
        # Reads data.csv and returns 50th percentile of column A
    """
    if not 0 <= percentile <= 1:
        raise ModelRetry("Percentile must be between 0 and 1")
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).quantile(percentile)).item()
    return Decimal(str(result))


def calculate_power(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    power: float,
    analysis_result_file_name: str,
) -> str:
    """
    Raise each value in a column to the specified power and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        power: The exponent
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing powered values

    Example:
        >>> calculate_power("data.csv", "A", 2, "squared_values")
        # Returns path to saved DataFrame with squared values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).pow(power)).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_power_{power}": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_sqrt(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate the square root of each value in a column and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing square root values

    Example:
        >>> calculate_sqrt("data.csv", "A", "sqrt_values")
        # Returns path to saved DataFrame with square root values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).sqrt()).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_sqrt": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_exp(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate e raised to the power of each value in a column and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing exponential values

    Example:
        >>> calculate_exp("data.csv", "A", "exp_values")
        # Returns path to saved DataFrame with exponential values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).exp()).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_exp": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_ln(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate the natural logarithm of each value in a column and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing natural log values

    Example:
        >>> calculate_ln("data.csv", "A", "ln_values")
        # Returns path to saved DataFrame with natural log values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).log()).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_ln": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_log(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    base: float,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate the logarithm of each value in a column with specified base and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        base: The base of the logarithm
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing log values

    Example:
        >>> calculate_log("data.csv", "A", 10, "log10_values")
        # Returns path to saved DataFrame with log base 10 values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).log(base)).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_log_{base}": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_abs(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate the absolute value of each value in a column and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing absolute values

    Example:
        >>> calculate_abs("data.csv", "A", "abs_values")
        # Returns path to saved DataFrame with absolute values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).abs()).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_abs": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_sign(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Return the sign of each value in a column (-1, 0, or 1) and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing sign values

    Example:
        >>> calculate_sign("data.csv", "A", "sign_values")
        # Returns path to saved DataFrame with sign values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).sign()).to_series().to_list()
    result_values = [int(r) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_sign": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_mod(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    divisor: float,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate the remainder after division for each value in a column and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        divisor: The divisor
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing modulus values

    Example:
        >>> calculate_mod("data.csv", "A", 5, "mod_values")
        # Returns path to saved DataFrame with modulus values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column) % divisor).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_mod_{divisor}": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_round(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    num_digits: int,
    analysis_result_file_name: str,
) -> str:
    """
    Round each value in a column to the specified number of digits and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        num_digits: Number of decimal places
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing rounded values

    Example:
        >>> calculate_round("data.csv", "A", 2, "rounded_values")
        # Returns path to saved DataFrame with rounded values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column)).to_series().to_list()
    quant = Decimal("1").scaleb(-num_digits)
    result_values = [Decimal(str(r)).quantize(quant, rounding=ROUND_HALF_UP) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_round_{num_digits}": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_roundup(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    num_digits: int,
    analysis_result_file_name: str,
) -> str:
    """
    Round up each value in a column to the specified number of digits and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        num_digits: Number of decimal places
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing rounded up values

    Example:
        >>> calculate_roundup("data.csv", "A", 2, "roundup_values")
        # Returns path to saved DataFrame with rounded up values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column)).to_series().to_list()
    quant = Decimal("1").scaleb(-num_digits)
    result_values = [Decimal(str(r)).quantize(quant, rounding=ROUND_CEILING) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_roundup_{num_digits}": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_rounddown(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    num_digits: int,
    analysis_result_file_name: str,
) -> str:
    """
    Round down each value in a column to the specified number of digits and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        num_digits: Number of decimal places
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing rounded down values

    Example:
        >>> calculate_rounddown("data.csv", "A", 2, "rounddown_values")
        # Returns path to saved DataFrame with rounded down values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column)).to_series().to_list()
    quant = Decimal("1").scaleb(-num_digits)
    result_values = [Decimal(str(r)).quantize(quant, rounding=ROUND_FLOOR) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_rounddown_{num_digits}": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_weighted_average(
    ctx: RunContext[FinnDeps],
    file_path: str,
    value_column: str,
    weight_column: str,
) -> Decimal:
    """
    Calculate the weighted average of values using weights.

    Args:
        file_path: Path to the CSV or Parquet file
        value_column: Name of the values column
        weight_column: Name of the weights column

    Returns:
        Weighted average

    Example:
        >>> calculate_weighted_average("data.csv", "values", "weights")
        # Reads data.csv and returns weighted average
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select((pl.col(value_column) * pl.col(weight_column)).sum() / pl.col(weight_column).sum()).item()
    return Decimal(str(result))


def calculate_geometric_mean(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the geometric mean of a column.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column

    Returns:
        Geometric mean

    Example:
        >>> calculate_geometric_mean("data.csv", "A")
        # Reads data.csv and returns geometric mean of column A
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.exp(pl.col(column).log().mean())).item()
    return Decimal(str(result))


def calculate_harmonic_mean(ctx: RunContext[FinnDeps], file_path: str, column: str) -> Decimal:
    """
    Calculate the harmonic mean of a column.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column

    Returns:
        Harmonic mean

    Example:
        >>> calculate_harmonic_mean("data.csv", "A")
        # Reads data.csv and returns harmonic mean of column A
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    n = df.select(pl.col(column).count()).item()
    sum_inv = df.select((1 / pl.col(column)).sum()).item()
    return Decimal(str(n)) / Decimal(str(sum_inv))


def calculate_cumsum(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate the cumulative sum of a column and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing cumulative sum values

    Example:
        >>> calculate_cumsum("data.csv", "A", "cumsum_values")
        # Returns path to saved DataFrame with cumulative sum values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).cum_sum()).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_cumsum": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_cumprod(
    ctx: RunContext[FinnDeps],
    file_path: str,
    column: str,
    analysis_result_file_name: str,
) -> str:
    """
    Calculate the cumulative product of a column and save results to a DataFrame.

    Args:
        file_path: Path to the CSV or Parquet file
        column: Name of the column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame containing cumulative product values

    Example:
        >>> calculate_cumprod("data.csv", "A", "cumprod_values")
        # Returns path to saved DataFrame with cumulative product values
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    result = df.select(pl.col(column).cum_prod()).to_series().to_list()
    result_values = [Decimal(str(r)) for r in result if r is not None]

    result_df = pl.DataFrame({f"{column}_cumprod": result_values})
    return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)


def calculate_variance_weighted(
    ctx: RunContext[FinnDeps],
    file_path: str,
    value_column: str,
    weight_column: str,
) -> Decimal:
    """
    Calculate the weighted variance of values.

    Args:
        file_path: Path to the CSV or Parquet file
        value_column: Name of the values column
        weight_column: Name of the weights column

    Returns:
        Weighted variance

    Example:
        >>> calculate_variance_weighted("data.csv", "values", "weights")
        # Reads data.csv and returns weighted variance
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    wmean = df.select((pl.col(value_column) * pl.col(weight_column)).sum() / pl.col(weight_column).sum()).item()
    weighted_var = df.select(
        (pl.col(weight_column) * (pl.col(value_column) - wmean).pow(2)).sum() / pl.col(weight_column).sum()
    ).item()
    return Decimal(str(weighted_var))
