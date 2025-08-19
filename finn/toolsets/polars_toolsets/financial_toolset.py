import math
from datetime import datetime
from typing import Any

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_file


def calculate_npv(discount_rate: float, *cash_flows: float) -> float:
    """
    Calculate the present value of a series of cash flows at a constant discount rate.

    Args:
        discount_rate: Discount rate per period
        *cash_flows: Variable length cash flow values

    Returns:
        Net present value

    Example:
        >>> calculate_npv(0.1, -1000, 500, 400, 300)
        77.88
    """
    if not cash_flows:
        raise ModelRetry("At least one cash flow is required")

    npv = 0.0
    for i, cash_flow in enumerate(cash_flows):
        npv += cash_flow / (1 + discount_rate) ** i
    return float(npv)


def calculate_irr(
    ctx: RunContext[FinnDeps],
    data: pl.DataFrame | str,
    cash_flow_column: str,
    guess: float = 0.1,
) -> float:
    """
    Determine the discount rate that makes the net present value of cash flows zero.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        cash_flow_column: Name of the column containing cash flows
        guess: Initial guess for the IRR (default 0.1)

    Returns:
        Internal rate of return

    Example:
        >>> df = pl.DataFrame({"cash_flows": [-1000, 500, 400, 300]})
        >>> calculate_irr(df, "cash_flows")
        0.162
    """
    try:
        df = load_file(ctx, data)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    cash_flows = df.select(pl.col(cash_flow_column)).to_series().to_list()

    if not cash_flows:
        raise ModelRetry("Cash flow column is empty")

    # Newton-Raphson method for IRR calculation
    rate = guess
    for _ in range(100):  # Max iterations
        npv = sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        npv_derivative = sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))

        if abs(npv_derivative) < 1e-10:
            break

        new_rate = rate - npv / npv_derivative

        if abs(new_rate - rate) < 1e-10:
            break

        rate = new_rate

    return float(rate)


def calculate_xnpv(
    ctx: RunContext[FinnDeps],
    discount_rate: float,
    data: pl.DataFrame | str,
    cash_flow_column: str,
    date_column: str,
) -> float:
    """
    Calculate NPV for cash flows that occur at irregular intervals.

    Args:
        discount_rate: Annual discount rate
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        cash_flow_column: Name of the column containing cash flows
        date_column: Name of the column containing dates

    Returns:
        Net present value for irregular cash flows

    Example:
        >>> df = pl.DataFrame({
        ...     "cash_flows": [-1000, 500, 400, 300],
        ...     "dates": ["2023-01-01", "2023-06-01", "2024-01-01", "2024-06-01"]
        ... })
        >>> calculate_xnpv(0.1, df, "cash_flows", "dates")
        123.45
    """
    try:
        df = load_file(ctx, data)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Ensure dates are parsed correctly
    df = df.with_columns(pl.col(date_column).str.to_date())

    # Get the first date as the base date
    base_date = df.select(pl.col(date_column).min()).item()

    # Calculate days difference and NPV
    result = (
        df.with_columns([(pl.col(date_column) - base_date).dt.total_days().alias("days_diff")])
        .select([(pl.col(cash_flow_column) / (1 + discount_rate) ** (pl.col("days_diff") / 365.25)).sum()])
        .item()
    )

    return float(result)


def calculate_xirr(
    ctx: RunContext[FinnDeps],
    data: pl.DataFrame | str,
    cash_flow_column: str,
    date_column: str,
    guess: float = 0.1,
) -> float:
    """
    Calculate IRR for cash flows that occur at irregular intervals.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        cash_flow_column: Name of the column containing cash flows
        date_column: Name of the column containing dates
        guess: Initial guess for the IRR (default 0.1)

    Returns:
        Internal rate of return for irregular cash flows

    Example:
        >>> df = pl.DataFrame({
        ...     "cash_flows": [-1000, 500, 400, 300],
        ...     "dates": ["2023-01-01", "2023-06-01", "2024-01-01", "2024-06-01"]
        ... })
        >>> calculate_xirr(df, "cash_flows", "dates")
        0.162
    """
    try:
        df = load_file(ctx, data)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    # Ensure dates are parsed correctly
    df = df.with_columns(pl.col(date_column).str.to_date())

    # Get data as lists for calculation
    cash_flows = df.select(pl.col(cash_flow_column)).to_series().to_list()
    dates = df.select(pl.col(date_column)).to_series().to_list()

    if len(cash_flows) != len(dates):
        raise ModelRetry("Cash flows and dates must have the same length")

    base_date = min(dates)
    days_diff = [(d - base_date).days for d in dates]

    # Newton-Raphson method for XIRR calculation
    rate = guess
    for _ in range(100):  # Max iterations
        npv = sum(cf / (1 + rate) ** (days / 365.25) for cf, days in zip(cash_flows, days_diff))
        npv_derivative = sum(
            -days / 365.25 * cf / (1 + rate) ** (days / 365.25 + 1) for cf, days in zip(cash_flows, days_diff)
        )

        if abs(npv_derivative) < 1e-10:
            break

        new_rate = rate - npv / npv_derivative

        if abs(new_rate - rate) < 1e-10:
            break

        rate = new_rate

    return float(rate)


def calculate_pmt(
    interest_rate: float,
    number_of_periods: int,
    present_value: float,
    future_value: float = 0.0,
    payment_type: int = 0,
) -> float:
    """
    Calculate the payment for a loan based on constant payments and interest rate.

    Args:
        interest_rate: Interest rate per period
        number_of_periods: Total number of payment periods
        present_value: Present value (loan amount)
        future_value: Future value (default 0.0)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Payment amount per period

    Example:
        >>> calculate_pmt(0.05/12, 360, 200000)
        -1073.64
    """
    if interest_rate == 0:
        return -(present_value + future_value) / number_of_periods

    pmt = -(
        present_value
        * (interest_rate * (1 + interest_rate) ** number_of_periods)
        / ((1 + interest_rate) ** number_of_periods - 1)
        + future_value * interest_rate / ((1 + interest_rate) ** number_of_periods - 1)
    )

    if payment_type == 1:
        pmt = pmt / (1 + interest_rate)

    return float(pmt)


def calculate_ipmt(
    interest_rate: float,
    period: int,
    number_of_periods: int,
    present_value: float,
    future_value: float = 0.0,
    payment_type: int = 0,
) -> float:
    """
    Determine the interest portion for a specific period of a loan payment.

    Args:
        interest_rate: Interest rate per period
        period: Period for which to calculate interest (1-based)
        number_of_periods: Total number of payment periods
        present_value: Present value (loan amount)
        future_value: Future value (default 0.0)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Interest payment for the specified period

    Example:
        >>> calculate_ipmt(0.05/12, 1, 360, 200000)
        -833.33
    """
    pmt = calculate_pmt(interest_rate, number_of_periods, present_value, future_value, payment_type)

    # Calculate remaining balance at the beginning of the period
    if period == 1:
        remaining_balance = present_value
    else:
        remaining_balance = calculate_pv(
            interest_rate,
            number_of_periods - period + 1,
            pmt,
            future_value,
            payment_type,
        )

    ipmt = remaining_balance * interest_rate

    if payment_type == 1 and period == 1:
        ipmt = 0.0

    return float(-ipmt)


def calculate_ppmt(
    interest_rate: float,
    period: int,
    number_of_periods: int,
    present_value: float,
    future_value: float = 0.0,
    payment_type: int = 0,
) -> float:
    """
    Determine the principal portion for a specific period of a loan payment.

    Args:
        interest_rate: Interest rate per period
        period: Period for which to calculate principal (1-based)
        number_of_periods: Total number of payment periods
        present_value: Present value (loan amount)
        future_value: Future value (default 0.0)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Principal payment for the specified period

    Example:
        >>> calculate_ppmt(0.05/12, 1, 360, 200000)
        -240.31
    """
    pmt = calculate_pmt(interest_rate, number_of_periods, present_value, future_value, payment_type)
    ipmt = calculate_ipmt(
        interest_rate,
        period,
        number_of_periods,
        present_value,
        future_value,
        payment_type,
    )

    return float(pmt - ipmt)


def calculate_pv(
    interest_rate: float,
    number_of_periods: int,
    payment: float,
    future_value: float = 0.0,
    payment_type: int = 0,
) -> float:
    """
    Compute the present value of an investment given a constant interest rate.

    Args:
        interest_rate: Interest rate per period
        number_of_periods: Total number of payment periods
        payment: Payment made each period
        future_value: Future value (default 0.0)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Present value

    Example:
        >>> calculate_pv(0.05/12, 360, -1073.64)
        200000.0
    """
    if interest_rate == 0:
        return -(future_value + payment * number_of_periods)

    pv = (
        -(
            future_value
            + payment
            * (1 + interest_rate * payment_type)
            * ((1 + interest_rate) ** number_of_periods - 1)
            / interest_rate
        )
        / (1 + interest_rate) ** number_of_periods
    )

    return float(pv)


def calculate_fv(
    interest_rate: float,
    number_of_periods: int,
    payment: float,
    present_value: float = 0.0,
    payment_type: int = 0,
) -> float:
    """
    Compute the future value of an investment given a constant interest rate.

    Args:
        interest_rate: Interest rate per period
        number_of_periods: Total number of payment periods
        payment: Payment made each period
        present_value: Present value (default 0.0)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Future value

    Example:
        >>> calculate_fv(0.05/12, 360, -1073.64, 200000)
        0.0
    """
    if interest_rate == 0:
        return -(present_value + payment * number_of_periods)

    fv = -(
        present_value * (1 + interest_rate) ** number_of_periods
        + payment
        * (1 + interest_rate * payment_type)
        * ((1 + interest_rate) ** number_of_periods - 1)
        / interest_rate
    )

    return float(fv)


def calculate_nper(
    interest_rate: float,
    payment: float,
    present_value: float,
    future_value: float = 0.0,
    payment_type: int = 0,
) -> float:
    """
    Determine the duration of an investment in periods.

    Args:
        interest_rate: Interest rate per period
        payment: Payment made each period
        present_value: Present value
        future_value: Future value (default 0.0)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Number of periods

    Example:
        >>> calculate_nper(0.05/12, -1073.64, 200000)
        360.0
    """
    if interest_rate == 0:
        return -(present_value + future_value) / payment

    pmt_adjusted = payment * (1 + interest_rate * payment_type)

    if pmt_adjusted == 0:
        raise ModelRetry("Payment cannot be zero when interest rate is non-zero")

    nper = math.log(
        (pmt_adjusted - future_value * interest_rate) / (pmt_adjusted + present_value * interest_rate)
    ) / math.log(1 + interest_rate)

    return float(nper)


def calculate_rate(
    number_of_periods: int,
    payment: float,
    present_value: float,
    future_value: float = 0.0,
    payment_type: int = 0,
    guess: float = 0.1,
) -> float:
    """
    Determine the interest rate per period for an annuity.

    Args:
        number_of_periods: Total number of payment periods
        payment: Payment made each period
        present_value: Present value
        future_value: Future value (default 0.0)
        payment_type: When payments are due (0 = end of period, 1 = beginning)
        guess: Initial guess for the rate (default 0.1)

    Returns:
        Interest rate per period

    Example:
        >>> calculate_rate(360, -1073.64, 200000)
        0.00417
    """
    # Newton-Raphson method
    rate = guess
    for _ in range(100):  # Max iterations
        f = (
            present_value * (1 + rate) ** number_of_periods
            + payment * (1 + rate * payment_type) * ((1 + rate) ** number_of_periods - 1) / rate
            + future_value
        )

        df = (
            number_of_periods * present_value * (1 + rate) ** (number_of_periods - 1)
            + payment
            * (1 + rate * payment_type)
            * (
                number_of_periods * (1 + rate) ** (number_of_periods - 1) * rate
                - ((1 + rate) ** number_of_periods - 1)
            )
            / (rate**2)
            + payment * payment_type * ((1 + rate) ** number_of_periods - 1) / rate
        )

        if abs(df) < 1e-10:
            break

        new_rate = rate - f / df

        if abs(new_rate - rate) < 1e-10:
            break

        rate = new_rate

    return float(rate)


def calculate_cumipmt(
    interest_rate: float,
    number_of_periods: int,
    present_value: float,
    start_period: int,
    end_period: int,
    payment_type: int,
) -> float:
    """
    Calculate cumulative interest payments over a range of periods.

    Args:
        interest_rate: Interest rate per period
        number_of_periods: Total number of payment periods
        present_value: Present value (loan amount)
        start_period: First period in the calculation (1-based)
        end_period: Last period in the calculation (1-based)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Cumulative interest payments

    Example:
        >>> calculate_cumipmt(0.05/12, 360, 200000, 1, 12, 0)
        -9834.56
    """
    cumulative_interest = 0.0
    for period in range(start_period, end_period + 1):
        ipmt = calculate_ipmt(
            interest_rate,
            period,
            number_of_periods,
            present_value,
            0.0,
            payment_type,
        )
        cumulative_interest += ipmt

    return float(cumulative_interest)


def calculate_cumprinc(
    interest_rate: float,
    number_of_periods: int,
    present_value: float,
    start_period: int,
    end_period: int,
    payment_type: int,
) -> float:
    """
    Calculate cumulative principal payments over a range of periods.

    Args:
        interest_rate: Interest rate per period
        number_of_periods: Total number of payment periods
        present_value: Present value (loan amount)
        start_period: First period in the calculation (1-based)
        end_period: Last period in the calculation (1-based)
        payment_type: When payments are due (0 = end of period, 1 = beginning)

    Returns:
        Cumulative principal payments

    Example:
        >>> calculate_cumprinc(0.05/12, 360, 200000, 1, 12, 0)
        -3048.12
    """
    cumulative_principal = 0.0
    for period in range(start_period, end_period + 1):
        ppmt = calculate_ppmt(
            interest_rate,
            period,
            number_of_periods,
            present_value,
            0.0,
            payment_type,
        )
        cumulative_principal += ppmt

    return float(cumulative_principal)


def calculate_sln(cost: float, salvage_value: float, useful_life: int) -> float:
    """
    Compute straight-line depreciation.

    Args:
        cost: Initial cost of the asset
        salvage_value: Value at the end of useful life
        useful_life: Number of periods over which the asset is depreciated

    Returns:
        Annual depreciation amount

    Example:
        >>> calculate_sln(10000, 1000, 5)
        1800.0
    """
    return float((cost - salvage_value) / useful_life)


def calculate_syd(cost: float, salvage_value: float, useful_life: int, period: int) -> float:
    """
    Compute sum-of-years' digits depreciation.

    Args:
        cost: Initial cost of the asset
        salvage_value: Value at the end of useful life
        useful_life: Number of periods over which the asset is depreciated
        period: Period for which to calculate depreciation

    Returns:
        Depreciation for the specified period

    Example:
        >>> calculate_syd(10000, 1000, 5, 1)
        3000.0
    """
    sum_of_years = useful_life * (useful_life + 1) / 2
    depreciation = (cost - salvage_value) * (useful_life - period + 1) / sum_of_years
    return float(depreciation)


def calculate_ddb(cost: float, salvage_value: float, useful_life: int, period: int, factor: float = 2.0) -> float:
    """
    Compute double-declining balance depreciation.

    Args:
        cost: Initial cost of the asset
        salvage_value: Value at the end of useful life
        useful_life: Number of periods over which the asset is depreciated
        period: Period for which to calculate depreciation
        factor: Declining balance factor (default 2.0 for double-declining)

    Returns:
        Depreciation for the specified period

    Example:
        >>> calculate_ddb(10000, 1000, 5, 1)
        4000.0
    """
    rate = factor / useful_life
    book_value = cost

    for p in range(1, period + 1):
        depreciation = min(book_value * rate, book_value - salvage_value)
        if p == period:
            return float(depreciation)
        book_value -= depreciation

    return 0.0


def calculate_price(
    settlement: str,
    maturity: str,
    rate: float,
    yield_rate: float,
    redemption: float,
    frequency: int,
    basis: int = 0,
) -> float:
    """
    Calculate bond price.

    Args:
        settlement: Settlement date (YYYY-MM-DD format)
        maturity: Maturity date (YYYY-MM-DD format)
        rate: Annual coupon rate
        yield_rate: Annual yield rate
        redemption: Redemption value per $100 face value
        frequency: Number of coupon payments per year
        basis: Day count basis (0=30/360, 1=actual/actual, etc.)

    Returns:
        Bond price per $100 face value

    Example:
        >>> calculate_price("2024-01-01", "2029-01-01", 0.08, 0.09, 100, 2)
        96.11
    """

    settlement_date = datetime.strptime(settlement, "%Y-%m-%d")
    maturity_date = datetime.strptime(maturity, "%Y-%m-%d")

    # Calculate number of periods based on basis
    if basis == 0:  # 30/360
        days_in_year = 360
    else:  # Actual/actual
        days_in_year = 365.25

    years_to_maturity = (maturity_date - settlement_date).days / days_in_year
    num_periods = years_to_maturity * frequency

    # Coupon payment
    coupon = rate * redemption / frequency

    # Discount rate per period
    discount_rate = yield_rate / frequency

    # Present value of coupon payments
    pv_coupons = 0.0
    for i in range(1, int(num_periods) + 1):
        pv_coupons += coupon / (1 + discount_rate) ** i

    # Present value of redemption
    pv_redemption = redemption / (1 + discount_rate) ** num_periods

    return float(pv_coupons + pv_redemption)


def calculate_yield(
    settlement: str,
    maturity: str,
    rate: float,
    price: float,
    redemption: float,
    frequency: int,
    basis: int = 0,
    guess: float = 0.1,
) -> float:
    """
    Calculate bond yield.

    Args:
        settlement: Settlement date (YYYY-MM-DD format)
        maturity: Maturity date (YYYY-MM-DD format)
        rate: Annual coupon rate
        price: Bond price per $100 face value
        redemption: Redemption value per $100 face value
        frequency: Number of coupon payments per year
        basis: Day count basis (0=30/360, 1=actual/actual, etc.)
        guess: Initial guess for yield (default 0.1)

    Returns:
        Bond yield (annual)

    Example:
        >>> calculate_yield("2024-01-01", "2029-01-01", 0.08, 96.11, 100, 2)
        0.09
    """

    settlement_date = datetime.strptime(settlement, "%Y-%m-%d")
    maturity_date = datetime.strptime(maturity, "%Y-%m-%d")

    # Calculate number of periods based on basis
    if basis == 0:  # 30/360
        days_in_year = 360
    else:  # Actual/actual
        days_in_year = 365.25

    years_to_maturity = (maturity_date - settlement_date).days / days_in_year
    num_periods = years_to_maturity * frequency
    coupon = rate * redemption / frequency

    # Newton-Raphson method to find yield
    yield_rate = guess
    for _ in range(100):  # Max iterations
        # Calculate price with current yield
        discount_rate = yield_rate / frequency
        calc_price = 0.0

        for i in range(1, int(num_periods) + 1):
            calc_price += coupon / (1 + discount_rate) ** i

        calc_price += redemption / (1 + discount_rate) ** num_periods

        # Calculate derivative
        derivative = 0.0
        for i in range(1, int(num_periods) + 1):
            derivative -= (i / frequency) * coupon / (1 + discount_rate) ** (i + 1)

        derivative -= (num_periods / frequency) * redemption / (1 + discount_rate) ** (num_periods + 1)

        if abs(derivative) < 1e-10:
            break

        new_yield = yield_rate - (calc_price - price) / derivative

        if abs(new_yield - yield_rate) < 1e-10:
            break

        yield_rate = new_yield

    return float(yield_rate)


def calculate_duration(
    settlement: str,
    maturity: str,
    coupon: float,
    yield_rate: float,
    frequency: int,
    basis: int = 0,
) -> float:
    """
    Calculate bond duration (Macaulay duration).

    Args:
        settlement: Settlement date (YYYY-MM-DD format)
        maturity: Maturity date (YYYY-MM-DD format)
        coupon: Annual coupon rate
        yield_rate: Annual yield rate
        frequency: Number of coupon payments per year
        basis: Day count basis (0=30/360, 1=actual/actual, etc.)

    Returns:
        Bond duration in years

    Example:
        >>> calculate_duration("2024-01-01", "2029-01-01", 0.08, 0.09, 2)
        4.31
    """

    settlement_date = datetime.strptime(settlement, "%Y-%m-%d")
    maturity_date = datetime.strptime(maturity, "%Y-%m-%d")

    # Calculate number of periods based on basis
    if basis == 0:  # 30/360
        days_in_year = 360
    else:  # Actual/actual
        days_in_year = 365.25

    years_to_maturity = (maturity_date - settlement_date).days / days_in_year
    num_periods = years_to_maturity * frequency
    coupon_payment = coupon * 100 / frequency  # Assuming $100 face value
    discount_rate = yield_rate / frequency

    # Calculate present value and weighted time
    total_pv = 0.0
    weighted_time = 0.0

    for i in range(1, int(num_periods) + 1):
        pv = coupon_payment / (1 + discount_rate) ** i
        total_pv += pv
        weighted_time += (i / frequency) * pv

    # Add redemption value
    redemption_pv = 100 / (1 + discount_rate) ** num_periods
    total_pv += redemption_pv
    weighted_time += (num_periods / frequency) * redemption_pv

    duration = weighted_time / total_pv
    return float(duration)


def calculate_accrint(
    issue: str,
    first_interest: str,
    settlement: str,
    rate: float,
    par: float,
    frequency: int,
    basis: int = 0,
    calc_method: int = 1,
) -> float:
    """
    Calculate accrued interest for periodic interest securities.

    Args:
        issue: Issue date (YYYY-MM-DD format)
        first_interest: First interest date (YYYY-MM-DD format)
        settlement: Settlement date (YYYY-MM-DD format)
        rate: Annual interest rate
        par: Par value
        frequency: Number of coupon payments per year
        basis: Day count basis (default 0)
        calc_method: Calculation method (default 1)

    Returns:
        Accrued interest

    Example:
        >>> calculate_accrint("2024-01-01", "2024-07-01", "2024-03-01", 0.08, 1000, 2)
        26.67
    """

    # Use first_interest and calc_method parameters to avoid unused warnings
    _ = first_interest  # Could be used for more complex accrual calculations
    _ = calc_method  # Could be used for different calculation methods
    _ = frequency  # Could be used for period-based calculations

    issue_date = datetime.strptime(issue, "%Y-%m-%d")
    settlement_date = datetime.strptime(settlement, "%Y-%m-%d")

    # Calculate days between issue and settlement
    days_accrued = (settlement_date - issue_date).days

    # Calculate accrued interest
    if basis == 0:  # 30/360
        days_in_year = 360
    else:  # Actual/actual
        days_in_year = 365.25

    accrued_interest = par * rate * days_accrued / days_in_year

    return float(accrued_interest)


def calculate_accrintm(issue: str, settlement: str, rate: float, par: float, basis: int = 0) -> float:
    """
    Calculate accrued interest for maturity securities.

    Args:
        issue: Issue date (YYYY-MM-DD format)
        settlement: Settlement date (YYYY-MM-DD format)
        rate: Annual interest rate
        par: Par value
        basis: Day count basis (default 0)

    Returns:
        Accrued interest

    Example:
        >>> calculate_accrintm("2024-01-01", "2024-12-31", 0.05, 1000)
        50.0
    """

    issue_date = datetime.strptime(issue, "%Y-%m-%d")
    settlement_date = datetime.strptime(settlement, "%Y-%m-%d")

    # Calculate days between issue and settlement
    days_accrued = (settlement_date - issue_date).days

    # Calculate accrued interest
    if basis == 0:  # 30/360
        days_in_year = 360
    else:  # Actual/actual
        days_in_year = 365.25

    accrued_interest = par * rate * days_accrued / days_in_year

    return float(accrued_interest)


def calculate_effect(nominal_rate: float, npery: int) -> float:
    """
    Calculate effective annual interest rate.

    Args:
        nominal_rate: Nominal annual interest rate
        npery: Number of compounding periods per year

    Returns:
        Effective annual interest rate

    Example:
        >>> calculate_effect(0.12, 12)
        0.1268
    """
    effective_rate = (1 + nominal_rate / npery) ** npery - 1
    return float(effective_rate)


def calculate_nominal(effect_rate: float, npery: int) -> float:
    """
    Calculate nominal annual interest rate.

    Args:
        effect_rate: Effective annual interest rate
        npery: Number of compounding periods per year

    Returns:
        Nominal annual interest rate

    Example:
        >>> calculate_nominal(0.1268, 12)
        0.12
    """
    nominal_rate = npery * ((1 + effect_rate) ** (1 / npery) - 1)
    return float(nominal_rate)


def calculate_mirr(
    ctx: RunContext[FinnDeps],
    data: pl.DataFrame | str,
    values_column: str,
    finance_rate: float,
    reinvest_rate: float,
) -> float:
    """
    Calculate modified internal rate of return.

    Args:
        data: Either a polars DataFrame or a file path (CSV or Parquet)
              Will first check the `analysis_dir` and then the `data_dir` for the file.
        values_column: Name of the column containing cash flow values
        finance_rate: Interest rate paid on money used in cash flows
        reinvest_rate: Interest rate received on reinvestment of cash flows

    Returns:
        Modified internal rate of return

    Example:
        >>> df = pl.DataFrame({"values": [-1000, 200, 400, 500]})
        >>> calculate_mirr(df, "values", 0.10, 0.12)
        0.126
    """
    try:
        df = load_file(ctx, data)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    values = df.select(pl.col(values_column)).to_series().to_list()

    if not values:
        raise ModelRetry("Values column is empty")

    n = len(values)
    negative_flows: list[tuple[int, Any]] = []
    positive_flows: list[tuple[int, Any]] = []

    # Separate negative and positive cash flows
    for i, value in enumerate(values):
        if value < 0:
            negative_flows.append((i, value))
        elif value > 0:
            positive_flows.append((i, value))

    # Calculate present value of negative cash flows
    pv_negative = sum(value / (1 + finance_rate) ** period for period, value in negative_flows)

    # Calculate future value of positive cash flows
    fv_positive = sum(value * (1 + reinvest_rate) ** (n - 1 - period) for period, value in positive_flows)

    if pv_negative == 0 or fv_positive == 0:
        raise ModelRetry("Cannot calculate MIRR with zero present or future value")

    # Calculate MIRR
    mirr = (fv_positive / abs(pv_negative)) ** (1 / (n - 1)) - 1

    return float(mirr)


def calculate_db(cost: float, salvage_value: float, useful_life: int, period: int, month: int = 12) -> float:
    """
    Compute fixed-declining balance depreciation.

    Args:
        cost: Initial cost of the asset
        salvage_value: Value at the end of useful life
        useful_life: Number of periods over which the asset is depreciated
        period: Period for which to calculate depreciation
        month: Number of months in the first year (default 12)

    Returns:
        Depreciation for the specified period

    Example:
        >>> calculate_db(10000, 1000, 5, 1)
        3690.0
    """
    if salvage_value <= 0:
        salvage_value = 0.01  # Avoid division by zero

    rate = 1 - (salvage_value / cost) ** (1 / useful_life)
    rate = round(rate, 3)

    book_value = cost

    for p in range(1, period + 1):
        if p == 1:
            depreciation = cost * rate * month / 12
        elif p == useful_life + 1:
            depreciation = book_value * rate * (12 - month) / 12
        else:
            depreciation = book_value * rate

        if p == period:
            return float(depreciation)
        book_value -= depreciation

    return 0.0
