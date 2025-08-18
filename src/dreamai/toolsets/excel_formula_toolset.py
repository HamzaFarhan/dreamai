from pathlib import Path
from typing import Any

from openpyxl import load_workbook


# Custom Exceptions
class SheetNotFoundError(Exception):
    """Raised when a specified sheet is not found in the workbook."""

    pass


class FormulaError(Exception):
    """Raised when there's an error with formula syntax or parameters."""

    pass


class FileOperationError(Exception):
    """Raised when file operations fail."""

    pass


# Formula Writing Functions
def _write_formula(excel_path: str, sheet_name: str, cell: str, formula: str) -> str:
    """
    Helper function to write a formula to a cell.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        formula: Excel formula (without leading =)

    Returns:
        str: Excel file path

    Raises:
        FileNotFoundError: If Excel file doesn't exist
        SheetNotFoundError: If sheet doesn't exist
        FormulaError: If formula is invalid
        FileOperationError: If operation fails
    """
    try:
        excel_file = Path(excel_path)
        if not excel_file.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        wb = load_workbook(excel_path)

        if sheet_name not in wb.sheetnames:
            raise SheetNotFoundError(f"Sheet '{sheet_name}' not found")

        ws = wb[sheet_name]

        # Ensure formula starts with =
        if not formula.startswith("="):
            formula = "=" + formula

        ws[cell] = formula
        wb.save(excel_path)

        return str(excel_file.absolute())

    except (FileNotFoundError, SheetNotFoundError):
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write formula: {e}")


# Date Functions
def write_date_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes date functions to Excel cells.

    Supported functions: DATE, DAY, HOUR, MINUTE, MONTH, NOW, SECOND, TIME, TODAY, WEEKDAY, YEAR

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the date function
        function_args: Function arguments

    Returns:
        str: Excel file path

    Example:
        write_date_function("file.xlsx", "Sheet1", "A1", "TODAY")
        write_date_function("file.xlsx", "Sheet1", "B1", "DATE", 2023, 12, 25)
    """
    try:
        function_name = function_name.upper()

        valid_functions = {
            "DATE",
            "DAY",
            "HOUR",
            "MINUTE",
            "MONTH",
            "NOW",
            "SECOND",
            "TIME",
            "TODAY",
            "WEEKDAY",
            "YEAR",
        }

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid date function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        # Build formula
        if function_args:
            args_str = ",".join(str(arg) for arg in function_args)
            formula = f"{function_name}({args_str})"
        else:
            formula = f"{function_name}()"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write date function: {e}")


# Financial Functions
def write_financial_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes financial functions to Excel cells.

    Supported functions: FV, IRR, NPV, PMT, PV

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the financial function
        function_args: Function arguments

    Returns:
        str: Excel file path

    Example:
        write_financial_function("file.xlsx", "Sheet1", "A1", "PV", 0.05, 10, -1000)
    """
    try:
        function_name = function_name.upper()

        valid_functions = {"FV", "IRR", "NPV", "PMT", "PV"}

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid financial function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        if not function_args:
            raise FormulaError(f"Financial function {function_name} requires arguments")

        args_str = ",".join(str(arg) for arg in function_args)
        formula = f"{function_name}({args_str})"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write financial function: {e}")


# Logical Functions
def write_logical_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, conditions: list[Any]
) -> str:
    """
    Writes logical functions to Excel cells.

    Supported functions: AND, FALSE, IF, IFERROR, NOT, OR, TRUE

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the logical function
        conditions: Function conditions/arguments

    Returns:
        str: Excel file path

    Example:
        write_logical_function("file.xlsx", "Sheet1", "A1", "IF", "B1>10", '"Yes"', '"No"')
    """
    try:
        function_name = function_name.upper()

        valid_functions = {"AND", "FALSE", "IF", "IFERROR", "NOT", "OR", "TRUE"}

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid logical function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        if function_name in ["FALSE", "TRUE"] and conditions:
            raise FormulaError(f"Function {function_name} takes no arguments")

        if function_name in ["FALSE", "TRUE"]:
            formula = f"{function_name}()"
        else:
            if not conditions:
                raise FormulaError(f"Function {function_name} requires arguments")
            conditions_str = ",".join(str(condition) for condition in conditions)
            formula = f"{function_name}({conditions_str})"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write logical function: {e}")


# Lookup Functions
def write_lookup_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes lookup functions to Excel cells.

    Supported functions: CHOOSE, COLUMN, COLUMNS, HLOOKUP, INDEX, INDIRECT,
                        MATCH, OFFSET, ROW, ROWS, VLOOKUP

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the lookup function
        function_args: Function arguments

    Returns:
        str: Excel file path

    Example:
        write_lookup_function("file.xlsx", "Sheet1", "A1", "VLOOKUP", "B1", "D:E", 2, "FALSE")
    """
    try:
        function_name = function_name.upper()

        valid_functions = {
            "CHOOSE",
            "COLUMN",
            "COLUMNS",
            "HLOOKUP",
            "INDEX",
            "INDIRECT",
            "MATCH",
            "OFFSET",
            "ROW",
            "ROWS",
            "VLOOKUP",
        }

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid lookup function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        if function_args:
            args_str = ",".join(str(arg) for arg in function_args)
            formula = f"{function_name}({args_str})"
        else:
            formula = f"{function_name}()"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write lookup function: {e}")


# Math Functions
def write_math_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes math functions to Excel cells.

    Supported functions: ABS, ACOS, ASIN, ATAN, ATAN2, CEILING, COMBIN, COS,
                        COUNTIF, COUNTIFS, DEGREES, EVEN, EXP, FACT, FLOOR,
                        INT, LN, LOG, LOG10, MAX, MIN, MOD, ODD, PI, POWER,
                        PRODUCT, RADIANS, RAND, RANDBETWEEN, ROUND, ROUNDDOWN,
                        ROUNDUP, SIGN, SIN, SQRT, SUM, SUMIF, SUMIFS,
                        SUMPRODUCT, TAN, TRUNC

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the math function
        function_args: Function arguments

    Returns:
        str: Excel file path

    Example:
        write_math_function("file.xlsx", "Sheet1", "A1", "SUM", "B1:B10")
    """
    try:
        function_name = function_name.upper()

        valid_functions = {
            "ABS",
            "ACOS",
            "ASIN",
            "ATAN",
            "ATAN2",
            "CEILING",
            "COMBIN",
            "COS",
            "COUNTIF",
            "COUNTIFS",
            "DEGREES",
            "EVEN",
            "EXP",
            "FACT",
            "FLOOR",
            "INT",
            "LN",
            "LOG",
            "LOG10",
            "MAX",
            "MIN",
            "MOD",
            "ODD",
            "PI",
            "POWER",
            "PRODUCT",
            "RADIANS",
            "RAND",
            "RANDBETWEEN",
            "ROUND",
            "ROUNDDOWN",
            "ROUNDUP",
            "SIGN",
            "SIN",
            "SQRT",
            "SUM",
            "SUMIF",
            "SUMIFS",
            "SUMPRODUCT",
            "TAN",
            "TRUNC",
        }

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid math function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        # Functions that take no parameters
        no_param_functions = {"PI", "RAND"}

        if function_name in no_param_functions:
            if function_args:
                raise FormulaError(f"Function {function_name} takes no arguments")
            formula = f"{function_name}()"
        else:
            if not function_args:
                raise FormulaError(f"Function {function_name} requires arguments")
            args_str = ",".join(str(arg) for arg in function_args)
            formula = f"{function_name}({args_str})"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write math function: {e}")


# Statistical Functions
def write_statistical_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes statistical functions to Excel cells.

    Supported functions: AVERAGE, AVERAGEIF, AVERAGEIFS, COUNT, COUNTA, COUNTBLANK,
                        LARGE, MEDIAN, MODE, PERCENTILE, QUARTILE, RANK, SMALL, STDEV, VAR

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the statistical function
        function_args: Function data/arguments

    Returns:
        str: Excel file path

    Example:
        write_statistical_function("file.xlsx", "Sheet1", "A1", "AVERAGE", "B1:B10")
    """
    try:
        function_name = function_name.upper()

        valid_functions = {
            "AVERAGE",
            "AVERAGEIF",
            "AVERAGEIFS",
            "COUNT",
            "COUNTA",
            "COUNTBLANK",
            "LARGE",
            "MEDIAN",
            "MODE",
            "PERCENTILE",
            "QUARTILE",
            "RANK",
            "SMALL",
            "STDEV",
            "VAR",
        }

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid statistical function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        if not function_args:
            raise FormulaError(f"Statistical function {function_name} requires data")

        args_str = ",".join(str(item) for item in function_args)
        formula = f"{function_name}({args_str})"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write statistical function: {e}")


# Text Functions
def write_text_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes text functions to Excel cells.

    Supported functions: CHAR, CLEAN, CODE, CONCATENATE, EXACT, FIND, LEFT, LEN,
                        LOWER, MID, PROPER, REPLACE, REPT, RIGHT, SEARCH, SUBSTITUTE,
                        TEXT, TRIM, UPPER, VALUE

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the text function
        function_args: Function text arguments

    Returns:
        str: Excel file path

    Example:
        write_text_function("file.xlsx", "Sheet1", "A1", "CONCATENATE", "A1", "B1")
    """
    try:
        function_name = function_name.upper()

        valid_functions = {
            "CHAR",
            "CLEAN",
            "CODE",
            "CONCATENATE",
            "EXACT",
            "FIND",
            "LEFT",
            "LEN",
            "LOWER",
            "MID",
            "PROPER",
            "REPLACE",
            "REPT",
            "RIGHT",
            "SEARCH",
            "SUBSTITUTE",
            "TEXT",
            "TRIM",
            "UPPER",
            "VALUE",
        }

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid text function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        if not function_args:
            raise FormulaError(f"Text function {function_name} requires arguments")

        args_str = ",".join(str(arg) for arg in function_args)
        formula = f"{function_name}({args_str})"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write text function: {e}")


# Info Functions
def write_info_function(
    excel_path: str, sheet_name: str, cell: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes info functions to Excel cells.

    Supported functions: ISBLANK, ISERROR, ISNUMBER, ISTEXT

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        function_name: Name of the info function
        function_args: Function arguments

    Returns:
        str: Excel file path

    Example:
        write_info_function("file.xlsx", "Sheet1", "A1", "ISBLANK", "B1")
    """
    try:
        function_name = function_name.upper()

        valid_functions = {"ISBLANK", "ISERROR", "ISNUMBER", "ISTEXT"}

        if function_name not in valid_functions:
            raise FormulaError(
                f"Invalid info function: {function_name}. Valid functions: {sorted(valid_functions)}"
            )

        if not function_args:
            raise FormulaError(f"Info function {function_name} requires arguments")

        args_str = ",".join(str(arg) for arg in function_args)
        formula = f"{function_name}({args_str})"

        return _write_formula(excel_path, sheet_name, cell, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write info function: {e}")


# Utility Functions
def write_formula_to_cell(excel_path: str, sheet_name: str, cell: str, formula: str) -> str:
    """
    Writes any custom formula to a cell.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell: Cell reference (e.g., 'A1')
        formula: Complete Excel formula (with or without leading =)

    Returns:
        str: Excel file path

    Example:
        write_formula_to_cell("file.xlsx", "Sheet1", "A1", "=SUM(B1:B10)*0.1")
    """
    return _write_formula(excel_path, sheet_name, cell, formula)


# Batch Operations
def write_multiple_formulas(excel_path: str, sheet_name: str, formulas: dict[str, str]) -> str:
    """
    Writes multiple formulas to cells in a single operation.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        formulas: Dict mapping cell references to formulas

    Returns:
        str: Excel file path

    Example:
        write_multiple_formulas("file.xlsx", "Sheet1", {
            "A1": "=SUM(B1:B10)",
            "A2": "=AVERAGE(B1:B10)",
            "A3": "=MAX(B1:B10)"
        })
    """
    try:
        excel_file = Path(excel_path)
        if not excel_file.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        wb = load_workbook(excel_path)

        if sheet_name not in wb.sheetnames:
            raise SheetNotFoundError(f"Sheet '{sheet_name}' not found")

        ws = wb[sheet_name]

        for cell, formula in formulas.items():
            if not formula.startswith("="):
                formula = "=" + formula
            ws[cell] = formula

        wb.save(excel_path)
        return str(excel_file.absolute())

    except (FileNotFoundError, SheetNotFoundError):
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write multiple formulas: {e}")


if __name__ == "__main__":
    # Example usage
    try:
        # Example formulas
        excel_path = "example.xlsx"

        # Math formulas
        write_math_function(excel_path, "Sheet", "D1", "SUM", ["C2:C4"])
        write_statistical_function(excel_path, "Sheet", "D2", "AVERAGE", ["C2:C4"])
        write_math_function(excel_path, "Sheet", "D3", "MAX", ["C2:C4"])

        # Date formulas
        write_date_function(excel_path, "Sheet", "E1", "TODAY", [])
        write_date_function(excel_path, "Sheet", "E2", "YEAR", ["E1"])

        print("Formulas added to Excel file!")

    except Exception as e:
        print(f"Error: {e}")
