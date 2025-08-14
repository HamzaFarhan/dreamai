from decimal import Decimal, getcontext
from typing import Any, Literal

import polars as pl
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps
from .file_toolset import load_df

getcontext().prec = 28


def vlookup(
    ctx: RunContext[FinnDeps],
    file_path: str,
    lookup_value: str | int | float,
    table_array_column: str,
    return_column: str,
    range_lookup: bool = False,
) -> str | Decimal | None:
    """
    Search for a value in a vertical range (column) and return corresponding value.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        lookup_value: The value to search for
        table_array_column: Column to search in
        return_column: Column to return value from
        range_lookup: If True, finds approximate match (default False for exact match)

    Returns:
        Value from return_column corresponding to the lookup_value

    Example:
        >>> df = pl.DataFrame({"ID": [1, 2, 3], "Name": ["Alice", "Bob", "Charlie"]})
        >>> vlookup(df, 2, "ID", "Name")
        "Bob"
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        if range_lookup:
            # Approximate match - find largest value <= lookup_value
            filtered = df.filter(pl.col(table_array_column) <= lookup_value)
            if filtered.height == 0:
                return None
            result = filtered.sort(table_array_column, descending=True).select(return_column).item(0)
        else:
            # Exact match
            filtered = df.filter(pl.col(table_array_column) == lookup_value)
            if filtered.height == 0:
                return None
            result = filtered.select(return_column).item(0)
    except Exception as e:
        raise ModelRetry(f"Error during VLOOKUP: {e}")

    # Use Decimal for numeric results
    if isinstance(result, (int, float)):
        return Decimal(str(result))
    return result


def hlookup(
    ctx: RunContext[FinnDeps],
    file_path: str,
    lookup_value: str | int | float,
    lookup_row_index: int,
    return_row_index: int,
    range_lookup: bool = False,
) -> str | Decimal | None:
    """
    Search for a value in a horizontal range (row) and return corresponding value.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        lookup_value: The value to search for
        lookup_row_index: Row index to search in (0-based)
        return_row_index: Row index to return value from (0-based)
        range_lookup: If True, finds approximate match (default False for exact match)

    Returns:
        Value from return_row_index corresponding to the lookup_value

    Example:
        >>> df = pl.DataFrame({"A": [1, 10], "B": [2, 20], "C": [3, 30]})
        >>> hlookup(df, 2, 0, 1)
        20
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    if lookup_row_index >= df.height or return_row_index >= df.height:
        raise ModelRetry("Row index out of bounds")
    try:
        # Get the lookup row as a list
        lookup_row = df.row(lookup_row_index)
        return_row = df.row(return_row_index)

        if range_lookup:
            # Find largest value <= lookup_value
            best_match_idx = None
            for i, val in enumerate(lookup_row):
                if val <= lookup_value:
                    if best_match_idx is None or val > lookup_row[best_match_idx]:
                        best_match_idx = i
            if best_match_idx is None:
                return None
            result = return_row[best_match_idx]
        else:
            # Exact match
            try:
                col_index = lookup_row.index(lookup_value)
                result = return_row[col_index]
            except ValueError:
                return None
    except Exception as e:
        raise ModelRetry(f"Error during HLOOKUP: {e}")

    if isinstance(result, (int, float)):
        return Decimal(str(result))
    return result


def index_lookup(
    ctx: RunContext[FinnDeps], file_path: str, row_num: int, column_num: int | None = None
) -> str | Decimal | list[Any] | None:
    """
    Return a value at a given position in a DataFrame.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        row_num: Row number (0-based)
        column_num: Column number (0-based), if None returns entire row

    Returns:
        Value at specified position or entire row if column_num is None

    Example:
        >>> df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        >>> index_lookup(df, 1, 0)
        2
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    try:
        if row_num >= df.height or row_num < 0:
            return None

        if column_num is None:
            row_data = df.row(row_num)
            # Use Decimal for numeric values
            return [Decimal(str(x)) if isinstance(x, (int, float)) else x for x in row_data]

        if column_num >= df.width or column_num < 0:
            return None

        result = df.item(row_num, column_num)
    except Exception as e:
        raise ModelRetry(f"Error during INDEX_LOOKUP: {e}")
    if isinstance(result, (int, float)):
        return Decimal(str(result))
    return result


def match_lookup(
    ctx: RunContext[FinnDeps],
    file_path: str,
    lookup_value: str | int | float,
    lookup_column: str,
    match_type: Literal[0, 1, -1] = 0,
) -> int | None:
    """
    Find the relative position of an item in a column.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        lookup_value: Value to search for
        lookup_column: Column to search in
        match_type: 0 for exact match, 1 for largest value <= lookup_value, -1 for smallest value >= lookup_value

    Returns:
        0-based position of the match, or None if not found

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30, 40]})
        >>> match_lookup(df, 30, "A", 0)
        2
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")
    try:
        if match_type == 0:
            # Exact match
            matches = df.with_row_index().filter(pl.col(lookup_column) == lookup_value)
            if matches.height == 0:
                return None
            return int(matches.select("index").item(0))
        elif match_type == 1:
            # Largest value <= lookup_value
            filtered = df.with_row_index().filter(pl.col(lookup_column) <= lookup_value)
            if filtered.height == 0:
                return None
            result = filtered.sort(lookup_column, descending=True).select("index").item(0)
            return int(result)
        elif match_type == -1:
            # Smallest value >= lookup_value
            filtered = df.with_row_index().filter(pl.col(lookup_column) >= lookup_value)
            if filtered.height == 0:
                return None
            result = filtered.sort(lookup_column).select("index").item(0)
            return int(result)
        else:
            raise ModelRetry("match_type must be -1, 0, or 1")
    except Exception as e:
        raise ModelRetry(f"Error during MATCH_LOOKUP: {e}")


def xlookup(
    ctx: RunContext[FinnDeps],
    file_path: str,
    lookup_value: str | int | float,
    lookup_column: str,
    return_column: str,
    if_not_found: str | Decimal | None = None,
) -> str | Decimal | None:
    """
    Modern, flexible lookup function replacing VLOOKUP/HLOOKUP.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        lookup_value: Value to search for
        lookup_column: Column to search in
        return_column: Column to return value from
        if_not_found: Value to return if not found

    Returns:
        Value from return_column or if_not_found value

    Example:
        >>> df = pl.DataFrame({"ID": [1, 2, 3], "Name": ["Alice", "Bob", "Charlie"]})
        >>> xlookup(df, 2, "ID", "Name", "Not Found")
        "Bob"
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        filtered = df.filter(pl.col(lookup_column) == lookup_value)
        if filtered.height == 0:
            return if_not_found

        result = filtered.select(return_column).item(0)
        if isinstance(result, (int, float)):
            return Decimal(str(result))
        return result
    except Exception as e:
        raise ModelRetry(f"Error during XLOOKUP: {e}")


def offset_range(
    ctx: RunContext[FinnDeps],
    file_path: str,
    reference_row: int,
    reference_col: int,
    rows_offset: int,
    cols_offset: int,
    height: int | None = None,
    width: int | None = None,
) -> list[list[Any]] | None:
    """
    Create dynamic ranges based on reference point.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        reference_row: Starting row (0-based)
        reference_col: Starting column (0-based)
        rows_offset: Number of rows to offset
        cols_offset: Number of columns to offset
        height: Number of rows to return (default 1)
        width: Number of columns to return (default 1)

    Returns:
        List of lists representing the range

    Example:
        >>> df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9]})
        >>> offset_range(df, 0, 0, 1, 1, 2, 2)
        [[5, 6], [8, 9]]
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        start_row = reference_row + rows_offset
        start_col = reference_col + cols_offset

        if height is None:
            height = 1
        if width is None:
            width = 1

        end_row = start_row + height
        end_col = start_col + width

        if start_row < 0 or start_col < 0 or end_row > df.height or end_col > df.width:
            return None

        result: list[list[Any]] = []
        for row in range(start_row, end_row):
            row_data: list[Any] = []
            for col in range(start_col, end_col):
                val = df.item(row, col)
                row_data.append(Decimal(str(val)) if isinstance(val, (int, float)) else val)
            result.append(row_data)

        return result
    except Exception as e:
        raise ModelRetry(f"Error during OFFSET_RANGE: {e}")


def indirect_reference(ctx: RunContext[FinnDeps], file_path: str, ref_text: str) -> str | Decimal | None:
    """
    Create references based on text strings (simplified version).

    Args:
        file_path: Path to the data file (CSV or Parquet)
        ref_text: Text reference in format "column_name" or "column_name[row_index]"

    Returns:
        Value at the referenced location

    Example:
        >>> df = pl.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        >>> indirect_reference(df, "A[1]")
        2
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        if "[" in ref_text and "]" in ref_text:
            # Format: column_name[row_index]
            col_name = ref_text.split("[")[0]
            row_index = int(ref_text.split("[")[1].split("]")[0])

            if col_name not in df.columns or row_index >= df.height:
                return None

            result = df.select(col_name).item(row_index)
        else:
            # Just column name - return first value
            if ref_text not in df.columns:
                return None
            result = df.select(ref_text).item(0)

        if isinstance(result, (int, float)):
            return Decimal(str(result))
        return result
    except Exception as e:
        raise ModelRetry(f"Error during INDIRECT_REFERENCE: {e}")


def choose_value(
    ctx: RunContext[FinnDeps], file_path: str, index_column: str, index_num: int, *value_columns: str
) -> str | Decimal | None:
    """
    Return a value from a list based on index number.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        index_column: Column containing index values
        index_num: Index number to match
        value_columns: Columns to choose from based on position

    Returns:
        Selected value from the appropriate column

    Example:
        >>> df = pl.DataFrame({"idx": [1, 2, 3], "A": [10, 20, 30], "B": [40, 50, 60]})
        >>> choose_value(df, "idx", 2, "A", "B")
        50
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        if not value_columns:
            return None

        # Find row with matching index
        filtered = df.filter(pl.col(index_column) == index_num)
        if filtered.height == 0:
            return None

        # Choose column based on index (1-based)
        if index_num < 1 or index_num > len(value_columns):
            return None

        chosen_column = value_columns[index_num - 1]
        if chosen_column not in df.columns:
            return None

        result = filtered.select(chosen_column).item(0)
        if isinstance(result, (int, float)):
            return Decimal(str(result))
        return result
    except Exception as e:
        raise ModelRetry(f"Error during CHOOSE_VALUE: {e}")


def lookup_vector(
    ctx: RunContext[FinnDeps],
    file_path: str,
    lookup_value: str | int | float,
    lookup_column: str,
    result_column: str,
) -> str | Decimal | None:
    """
    Simple lookup function (vector form).

    Args:
        file_path: Path to the data file (CSV or Parquet)
        lookup_value: Value to search for
        lookup_column: Column to search in
        result_column: Column to return value from

    Returns:
        Value from result_column

    Example:
        >>> df = pl.DataFrame({"keys": [1, 2, 3], "values": ["A", "B", "C"]})
        >>> lookup_vector(df, 2, "keys", "values")
        "B"
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        filtered = df.filter(pl.col(lookup_column) <= lookup_value)
        if filtered.height == 0:
            return None

        result = filtered.sort(lookup_column, descending=True).select(result_column).item(0)
        if isinstance(result, (int, float)):
            return Decimal(str(result))
        return result
    except Exception as e:
        raise ModelRetry(f"Error during LOOKUP_VECTOR: {e}")


def address_cell(
    row_num: int, column_num: int, abs_num: int = 1, a1_style: bool = True, sheet_text: str | None = None
) -> str:
    """
    Create cell address as text.

    Args:
        row_num: Row number (1-based)
        column_num: Column number (1-based)
        abs_num: Reference type (1=absolute, 2=absolute row/relative col, 3=relative row/absolute col, 4=relative)
        a1_style: If True use A1 style, if False use R1C1 style
        sheet_text: Sheet name to include

    Returns:
        Text string representing cell address

    Example:
        >>> address_cell(1, 1, 1, True, "Sheet1")
        "Sheet1!$A$1"
    """
    try:
        if a1_style:
            # Convert column number to letter
            col_letter = ""
            col = column_num
            while col > 0:
                col -= 1
                col_letter = chr(65 + (col % 26)) + col_letter
                col //= 26

            # Apply absolute/relative formatting
            if abs_num == 1:  # Absolute
                address = f"${col_letter}${row_num}"
            elif abs_num == 2:  # Absolute row, relative column
                address = f"{col_letter}${row_num}"
            elif abs_num == 3:  # Relative row, absolute column
                address = f"${col_letter}{row_num}"
            else:  # Relative
                address = f"{col_letter}{row_num}"
        else:
            # R1C1 style
            if abs_num == 1:  # Absolute
                address = f"R{row_num}C{column_num}"
            elif abs_num == 2:  # Absolute row, relative column
                address = f"R{row_num}C[{column_num}]"
            elif abs_num == 3:  # Relative row, absolute column
                address = f"R[{row_num}]C{column_num}"
            else:  # Relative
                address = f"R[{row_num}]C[{column_num}]"

        if sheet_text:
            address = f"{sheet_text}!{address}"

        return address
    except Exception as e:
        raise ModelRetry(f"Error during ADDRESS_CELL: {e}")


def row_number(
    ctx: RunContext[FinnDeps],
    file_path: str,
    reference_column: str | None = None,
    reference_value: str | int | float | None = None,
) -> int | list[int]:
    """
    Return row number of reference.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        reference_column: Column to search in (optional)
        reference_value: Value to find row number for (optional)

    Returns:
        Row number(s) (1-based) or list of row numbers

    Example:
        >>> df = pl.DataFrame({"A": [10, 20, 30]})
        >>> row_number(df, "A", 20)
        2
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        if reference_column is None:
            # Return all row numbers
            return list(range(1, df.height + 1))

        if reference_value is None:
            # Return row numbers for non-null values in column
            non_null_rows = df.with_row_index().filter(pl.col(reference_column).is_not_null())
            return [int(row) + 1 for row in non_null_rows.select("index").to_series().to_list()]

        # Find specific value
        matches = df.with_row_index().filter(pl.col(reference_column) == reference_value)
        if matches.height == 0:
            return []
        elif matches.height == 1:
            return int(matches.select("index").item(0)) + 1
        else:
            return [int(row) + 1 for row in matches.select("index").to_series().to_list()]
    except Exception as e:
        raise ModelRetry(f"Error during ROW_NUMBER: {e}")


def column_number(
    ctx: RunContext[FinnDeps], file_path: str, reference_column: str | None = None
) -> int | list[int]:
    """
    Return column number of reference.

    Args:
        file_path: Path to the data file (CSV or Parquet)
        reference_column: Column name to get number for (optional)

    Returns:
        Column number (1-based) or list of all column numbers

    Example:
        >>> df = pl.DataFrame({"A": [1], "B": [2], "C": [3]})
        >>> column_number(df, "B")
        2
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        if reference_column is None:
            # Return all column numbers
            return list(range(1, df.width + 1))

        if reference_column not in df.columns:
            return 0

        return df.columns.index(reference_column) + 1
    except Exception as e:
        raise ModelRetry(f"Error during COLUMN_NUMBER: {e}")


def rows_count(ctx: RunContext[FinnDeps], file_path: str) -> int:
    """
    Return number of rows in DataFrame.

    Args:
        file_path: Path to the data file (CSV or Parquet)

    Returns:
        Number of rows

    Example:
        >>> df = pl.DataFrame({"A": [1, 2, 3, 4, 5]})
        >>> rows_count(df)
        5
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        return df.height
    except Exception as e:
        raise ModelRetry(f"Error during ROWS_COUNT: {e}")


def columns_count(ctx: RunContext[FinnDeps], file_path: str) -> int:
    """
    Return number of columns in DataFrame.

    Args:
        file_path: Path to the data file (CSV or Parquet)

    Returns:
        Number of columns

    Example:
        >>> df = pl.DataFrame({"A": [1], "B": [2], "C": [3]})
        >>> columns_count(df)
        3
    """
    try:
        df = load_df(ctx, file_path)
    except Exception as e:
        raise ModelRetry(f"Error loading DataFrame: {e}")

    try:
        return df.width
    except Exception as e:
        raise ModelRetry(f"Error during COLUMNS_COUNT: {e}")
