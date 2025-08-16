from decimal import Decimal, getcontext

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_df, save_df_to_analysis_dir

getcontext().prec = 28


def cohort_analysis(
    ctx: RunContext[FinnDeps],
    file_path: str,
    customer_id_col: str,
    order_date_col: str,
    value_col: str,
    analysis_result_file_name: str,
) -> str:
    """
    Create cohort retention/revenue tables.

    Args:
        file_path: Path to the CSV or Parquet file
        customer_id_col: Name of the customer ID column
        order_date_col: Name of the order date column
        value_col: Name of the value (revenue) column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with cohort metrics

    Example:
        >>> cohort_analysis("transactions.parquet", "customer_id", "order_date", "revenue", "cohort_analysis")
        # Returns path to saved cohort metrics DataFrame
    """
    try:
        df = load_df(ctx, file_path)
        df = df.with_columns(pl.col(order_date_col).str.strptime(pl.Date, "%Y-%m-%d"))

        cohort_df = (
            df.group_by(customer_id_col)
            .agg(pl.col(order_date_col).min().alias("cohort_date"))
            .with_columns(pl.col("cohort_date").dt.truncate("1mo").alias("cohort"))
        )

        df = df.join(cohort_df, on=customer_id_col, how="left")
        df = df.with_columns(
            ((pl.col(order_date_col).dt.truncate("1mo") - pl.col("cohort")).dt.total_months()).alias("period")
        )

        cohort_metrics = (
            df.group_by(["cohort", "period"])
            .agg(pl.col(value_col).sum().alias("revenue"), pl.col(customer_id_col).n_unique().alias("customers"))
            .sort(["cohort", "period"])
        )

        pivot_df = cohort_metrics.pivot(values=["revenue", "customers"], index="cohort", on="period")

        return save_df_to_analysis_dir(ctx, pivot_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in cohort_analysis: {e}")


def retention_rate(
    ctx: RunContext[FinnDeps], file_path: str, period_col: str, active_col: str, analysis_result_file_name: str
) -> str:
    """
    Calculate customer retention rates by period.

    Args:
        file_path: Path to the CSV or Parquet file
        period_col: Name of the period column
        active_col: Name of the active flag column
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with retention percentages

    Example:
        >>> retention_rate("activity.csv", "month", "active", "retention_rates")
        # Returns path to saved retention rates DataFrame
    """
    try:
        df = load_df(ctx, file_path)

        period_active = (
            df.group_by(period_col).agg(pl.col(active_col).sum().alias("active_count")).sort(period_col)
        )

        period_active = period_active.with_columns(
            pl.col("active_count").shift(1).alias("previous_active")
        ).drop_nulls()

        retention_df = period_active.with_columns(
            (pl.col("active_count") / pl.col("previous_active")).alias("retention_rate")
        )

        return save_df_to_analysis_dir(ctx, retention_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in retention_rate: {e}")


def churn_rate(ctx: RunContext[FinnDeps], file_path: str, churned_flag_col: str) -> Decimal:
    """
    Calculate customer churn rates.

    Args:
        file_path: Path to the CSV or Parquet file
        churned_flag_col: Name of the churned flag column

    Returns:
        Churn rate as Decimal

    Example:
        >>> churn_rate("status.csv", "churned_flag")
        # Returns churn rate
    """
    try:
        df = load_df(ctx, file_path)
        result = df.select(pl.col(churned_flag_col).mean()).item()
        return Decimal(str(result))
    except Exception as e:
        raise ModelRetry(f"Error in churn_rate: {e}")


def ltv_calculation(arpu: float, churn_rate: float, profit_margin: float) -> Decimal:
    """
    Calculate Customer Lifetime Value.

    Args:
        arpu: Average revenue per user
        churn_rate: Churn rate
        profit_margin: Profit margin

    Returns:
        Lifetime value as Decimal

    Example:
        >>> ltv_calculation(50, 0.05, 0.3)
        # Returns LTV
    """
    try:
        ltv = (arpu * profit_margin) / churn_rate
        return Decimal(str(ltv))
    except Exception as e:
        raise ModelRetry(f"Error in ltv_calculation: {e}")


def payback_period(
    ctx: RunContext[FinnDeps], file_path: str, cash_flow_col: str, initial_investment: float
) -> int | None:
    """
    Calculate when cumulative profit equals initial investment.

    Args:
        file_path: Path to the CSV or Parquet file
        cash_flow_col: Name of the cash flow column
        initial_investment: Initial investment amount

    Returns:
        Period number or None

    Example:
        >>> payback_period("cashflows.csv", "cash_flow", 1000)
        # Returns period number
    """
    try:
        df = load_df(ctx, file_path)
        cash_flows = df.select(pl.col(cash_flow_col)).to_series().to_list()
        cumulative = 0
        for period, cf in enumerate(cash_flows, 1):
            cumulative += cf
            if cumulative >= initial_investment:
                return period
        return None
    except Exception as e:
        raise ModelRetry(f"Error in payback_period: {e}")


def assign_cohort(
    ctx: RunContext[FinnDeps],
    file_path: str,
    customer_id_col: str,
    date_col: str,
    cohort_period: str,
    analysis_result_file_name: str,
) -> str:
    """
    Assign a cohort identifier to each customer based on their first transaction or sign-up date.

    Args:
        file_path: Path to the CSV or Parquet file
        customer_id_col: Name of the customer ID column
        date_col: Name of the date column
        cohort_period: Period for cohort (e.g., 'M' for month, 'Q' for quarter)
        analysis_result_file_name: Descriptive name for the result file

    Returns:
        Path to the saved DataFrame with cohort column

    Example:
        >>> assign_cohort("customers.csv", "customer_id", "signup_date", "M", "cohort_assigned")
        # Returns path to saved DataFrame with cohort column
    """
    try:
        df = load_df(ctx, file_path)
        df = df.with_columns(pl.col(date_col).str.strptime(pl.Date, "%Y-%m-%d"))

        first_dates = (
            df.group_by(customer_id_col)
            .agg(pl.col(date_col).min().alias("first_date"))
            .with_columns(pl.col("first_date").dt.truncate(cohort_period).alias("cohort"))
        )

        result_df = df.join(first_dates, on=customer_id_col, how="left")

        return save_df_to_analysis_dir(ctx, result_df, analysis_result_file_name)
    except Exception as e:
        raise ModelRetry(f"Error in assign_cohort: {e}")


def arpu(total_revenue: float, total_users: int) -> Decimal:
    """
    Calculate the average revenue generated per user or account over a specific period.

    Args:
        total_revenue: Total revenue
        total_users: Total users

    Returns:
        ARPU as Decimal

    Example:
        >>> arpu(100000, 500)
        # Returns ARPU
    """
    try:
        arpu_value = total_revenue / total_users
        return Decimal(str(arpu_value))
    except Exception as e:
        raise ModelRetry(f"Error in arpu: {e}")
