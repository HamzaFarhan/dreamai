from datetime import date, datetime, time, timedelta
from typing import Literal

from dateutil.relativedelta import relativedelta
from pydantic_ai import ModelRetry


def today() -> str:
    """
    Return the current date.

    Returns:
        Current date in ISO format (YYYY-MM-DD)

    Example:
        >>> today()
        '2025-07-30'
    """
    return date.today().isoformat()


def now() -> str:
    """
    Return the current date and time.

    Returns:
        Current date and time in ISO format

    Example:
        >>> now()
        '2025-07-30T20:30:18.123456'
    """
    return datetime.now().isoformat()


def create_date(year: int, month: int, day: int) -> str:
    """
    Construct a date from year, month, and day components.

    Args:
        year: Year component
        month: Month component (1-12)
        day: Day component (1-31)

    Returns:
        Date value in ISO format

    Example:
        >>> create_date(2025, 4, 15)
        '2025-04-15'
    """
    return date(year, month, day).isoformat()


def extract_year(date_str: str) -> int:
    """
    Extract the year from a date.

    Args:
        date_str: Date string in ISO format

    Returns:
        Integer year

    Example:
        >>> extract_year("2025-04-15")
        2025
    """
    return datetime.fromisoformat(date_str).year


def extract_month(date_str: str) -> int:
    """
    Extract the month from a date.

    Args:
        date_str: Date string in ISO format

    Returns:
        Integer month (1-12)

    Example:
        >>> extract_month("2025-04-15")
        4
    """
    return datetime.fromisoformat(date_str).month


def extract_day(date_str: str) -> int:
    """
    Extract the day from a date.

    Args:
        date_str: Date string in ISO format

    Returns:
        Integer day (1-31)

    Example:
        >>> extract_day("2025-04-15")
        15
    """
    return datetime.fromisoformat(date_str).day


def edate(start_date: str, months: int) -> str:
    """
    Calculate a date a given number of months before or after a specified date.

    Args:
        start_date: Starting date in ISO format
        months: Number of months to add (positive) or subtract (negative)

    Returns:
        Date value in ISO format

    Example:
        >>> edate("2025-04-15", 3)
        '2025-07-15'
        >>> edate("2025-04-15", -1)
        '2025-03-15'
    """
    dt = datetime.fromisoformat(start_date).date()
    return (dt + relativedelta(months=months)).isoformat()


def eomonth(start_date: str, months: int) -> str:
    """
    Find the end of the month for a given date.

    Args:
        start_date: Starting date in ISO format
        months: Number of months to add (positive) or subtract (negative)

    Returns:
        Date value (end of month) in ISO format

    Example:
        >>> eomonth("2025-04-15", 1)
        '2025-05-31'
        >>> eomonth("2025-04-15", 0)
        '2025-04-30'
    """
    dt = datetime.fromisoformat(start_date).date()
    # Move to the target month, then to the last day of that month
    target_month = dt + relativedelta(months=months)
    # Move to the first day of next month, then back one day
    next_month = target_month.replace(day=1) + relativedelta(months=1)
    end_of_month = next_month - timedelta(days=1)
    return end_of_month.isoformat()


def datedif(start_date: str, end_date: str, unit: str) -> int:
    """
    Calculate the difference between two dates.

    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        unit: Unit of difference ('D' for days, 'M' for months, 'Y' for years)

    Returns:
        Integer difference in specified unit

    Example:
        >>> datedif("2025-01-01", "2025-01-15", "D")
        14
        >>> datedif("2025-01-01", "2026-01-01", "Y")
        1
    """
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    if unit.upper() == "D":
        return (end - start).days
    elif unit.upper() == "M":
        return (end.year - start.year) * 12 + (end.month - start.month)
    elif unit.upper() == "Y":
        return end.year - start.year
    else:
        raise ModelRetry("Unit must be 'D', 'M', or 'Y'")


def yearfrac(start_date: str, end_date: str, basis: int = 0) -> float:
    """
    Calculate the fraction of a year between two dates.

    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        basis: Day count basis (0 = US (NASD) 30/360, 1 = Actual/Actual, etc.)

    Returns:
        Decimal fraction of year

    Example:
        >>> yearfrac("2025-01-01", "2025-07-01")
        0.5
    """
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    if basis == 0:  # US (NASD) 30/360
        # Simplified 30/360 calculation
        days = (end - start).days
        return days / 360.0
    else:  # Actual/Actual
        days = (end - start).days
        # Approximate year length (simplified)
        return days / 365.25


def weekday(serial_number: str, return_type: int = 1) -> int:
    """
    Return day of week as number.

    Args:
        serial_number: Date string in ISO format
        return_type: Type of numbering (1 = Sunday=1, Monday=2, ..., 2 = Monday=1, Tuesday=2, ...)

    Returns:
        Integer (1-7) representing day of week

    Example:
        >>> weekday("2024-01-01")  # Monday
        2
        >>> weekday("2024-01-01", 2)  # Monday with type 2
        1
    """
    dt = datetime.fromisoformat(serial_number).date()
    weekday_num = dt.weekday()  # Monday=0, Sunday=6

    if return_type == 1:
        # Sunday=1, Monday=2, ..., Saturday=7
        return weekday_num + 2 if weekday_num < 6 else 1
    elif return_type == 2:
        # Monday=1, Tuesday=2, ..., Sunday=7
        return weekday_num + 1
    else:
        raise ModelRetry("return_type must be 1 or 2")


def quarter(date_str: str) -> int:
    """
    Extract quarter from date.

    Args:
        date_str: Date string in ISO format

    Returns:
        Integer (1-4) representing quarter

    Example:
        >>> quarter("2024-07-15")
        3
    """
    dt = datetime.fromisoformat(date_str).date()
    return (dt.month - 1) // 3 + 1


def create_time(hour: int, minute: int, second: int) -> str:
    """
    Create time value from hours, minutes, seconds.

    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)

    Returns:
        Time value in ISO format

    Example:
        >>> create_time(14, 30, 0)
        '14:30:00'
    """
    return time(hour, minute, second).isoformat()


def extract_hour(serial_number: str) -> int:
    """
    Extract hour from time.

    Args:
        serial_number: Time string in ISO format

    Returns:
        Integer (0-23) representing hour

    Example:
        >>> extract_hour("14:30:00")
        14
    """
    if "T" in serial_number:
        # DateTime string
        dt = datetime.fromisoformat(serial_number)
        return dt.hour
    else:
        # Time string
        t = time.fromisoformat(serial_number)
        return t.hour


def extract_minute(serial_number: str) -> int:
    """
    Extract minute from time.

    Args:
        serial_number: Time string in ISO format

    Returns:
        Integer (0-59) representing minute

    Example:
        >>> extract_minute("14:30:45")
        30
    """
    if "T" in serial_number:
        # DateTime string
        dt = datetime.fromisoformat(serial_number)
        return dt.minute
    else:
        # Time string
        t = time.fromisoformat(serial_number)
        return t.minute


def extract_second(serial_number: str) -> int:
    """
    Extract second from time.

    Args:
        serial_number: Time string in ISO format

    Returns:
        Integer (0-59) representing second

    Example:
        >>> extract_second("14:30:45")
        45
    """
    if "T" in serial_number:
        # DateTime string
        dt = datetime.fromisoformat(serial_number)
        return dt.second
    else:
        # Time string
        t = time.fromisoformat(serial_number)
        return t.second


def date_range(start_date: str, end_date: str, frequency: Literal["D", "W", "M", "Q", "Y"]) -> list[str]:
    """
    Generate a series of dates between a start and end date with a specified frequency.

    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        frequency: Frequency ('D' for day, 'W' for week, 'M' for month-end, 'Q' for quarter-end, 'Y' for year-end)

    Returns:
        List of dates in ISO format

    Example:
        >>> date_range("2025-01-01", "2025-03-31", "M")
        ['2025-01-31', '2025-02-28', '2025-03-31']
    """
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    dates: list[str] = []
    current = start

    if frequency.upper() == "D":
        while current <= end:
            dates.append(current.isoformat())
            current += timedelta(days=1)
    elif frequency.upper() == "W":
        while current <= end:
            dates.append(current.isoformat())
            current += timedelta(weeks=1)
    elif frequency.upper() == "M":
        # Month-end dates
        current = start.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
        while current <= end:
            dates.append(current.isoformat())
            current = current.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
    elif frequency.upper() == "Q":
        # Quarter-end dates (March, June, September, December)
        current_month = ((start.month - 1) // 3 + 1) * 3
        current_year = start.year
        if current_month > 12:
            current_month = 3
            current_year += 1
        else:
            current = date(current_year, current_month, 1) + relativedelta(months=1) - timedelta(days=1)
            if current < start:
                current_month += 3
                if current_month > 12:
                    current_month = 3
                    current_year += 1

        while True:
            current = date(current_year, current_month, 1) + relativedelta(months=1) - timedelta(days=1)
            if current > end:
                break
            dates.append(current.isoformat())
            current_month += 3
            if current_month > 12:
                current_month = 3
                current_year += 1
    elif frequency.upper() == "Y":
        # Year-end dates
        current_year = start.year
        if start.month == 12 and start.day == 31:
            current = start
        else:
            current = date(current_year, 12, 31)
            if current < start:
                current_year += 1
                current = date(current_year, 12, 31)

        while current <= end:
            dates.append(current.isoformat())
            current_year += 1
            current = date(current_year, 12, 31)

    return dates


def workday(start_date: str, days: int, holidays: list[str] | None = None) -> str:
    """
    Return a future or past date excluding weekends and holidays.

    Args:
        start_date: Starting date in ISO format
        days: Number of working days to add (positive) or subtract (negative)
        holidays: Optional list of holiday dates in ISO format

    Returns:
        Date value in ISO format

    Example:
        >>> workday("2025-07-30", 5)
        '2025-08-06'
        >>> workday("2025-07-30", -2)
        '2025-07-24'
    """
    if holidays is None:
        holidays = []

    holiday_dates = {datetime.fromisoformat(h).date() for h in holidays}
    current = datetime.fromisoformat(start_date).date()

    if days >= 0:
        # Add working days
        while days > 0:
            current += timedelta(days=1)
            # Skip weekends (Saturday=5, Sunday=6) and holidays
            if current.weekday() < 5 and current not in holiday_dates:
                days -= 1
    else:
        # Subtract working days
        while days < 0:
            current -= timedelta(days=1)
            # Skip weekends (Saturday=5, Sunday=6) and holidays
            if current.weekday() < 5 and current not in holiday_dates:
                days += 1

    return current.isoformat()


def networkdays(start_date: str, end_date: str, holidays: list[str] | None = None) -> int:
    """
    Count working days between two dates.

    Args:
        start_date: Start date in ISO format
        end_date: End date in ISO format
        holidays: Optional list of holiday dates in ISO format

    Returns:
        Integer number of working days

    Example:
        >>> networkdays("2025-07-28", "2025-08-01")
        5
        >>> networkdays("2025-07-28", "2025-08-01", ["2025-07-30"])
        4
    """
    if holidays is None:
        holidays = []

    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    holiday_dates = {datetime.fromisoformat(h).date() for h in holidays}

    # Ensure start <= end
    if start > end:
        start, end = end, start

    working_days = 0
    current = start

    while current <= end:
        # Count weekdays (Monday=0 to Friday=4) that are not holidays
        if current.weekday() < 5 and current not in holiday_dates:
            working_days += 1
        current += timedelta(days=1)

    return working_days
