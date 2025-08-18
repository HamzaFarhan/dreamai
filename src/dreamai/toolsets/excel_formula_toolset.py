import re
import warnings
from pathlib import Path
from typing import Any

import formulas  # type: ignore
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


def _validate_formula(excel_path: str, sheet_name: str, cell_ref: str, formula: str) -> None:
    """
    Comprehensive formula validation using the formulas library.

    This function validates Excel formulas by:
    1. Parsing the formula for syntax errors
    2. Checking sheet references exist
    3. Validating function names
    4. Detecting division by zero
    5. Evaluating the formula to catch runtime errors

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the sheet containing the formula
        cell_ref: Cell reference where formula will be placed (e.g., 'A1')
        formula: Excel formula (with or without leading =)

    Raises:
        FormulaError: If formula has any validation errors
    """
    # Ensure formula starts with =
    if not formula.startswith("="):
        formula = "=" + formula

    try:
        # Load the workbook to get available sheets and data
        wb = load_workbook(excel_path, data_only=False)
        available_sheets = wb.sheetnames

        # Create a dictionary of sheet data for formula evaluation
        sheets_data: dict[str, dict[str, Any]] = {}
        for sheet in available_sheets:
            ws = wb[sheet]
            sheet_data: dict[str, Any] = {}
            # Load all cell values from the sheet for full validation.
            # WARNING: This can be slow and memory-intensive for large Excel files.
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        sheet_data[cell.coordinate] = cell.value
            sheets_data[sheet] = sheet_data

        wb.close()

        # Step 1: Parse the formula for syntax errors
        parser = formulas.Parser()

        try:
            # Parse the formula
            ast = parser.ast(formula)  # type: ignore
            if ast is None or len(ast) < 2:  # type: ignore
                raise FormulaError(f"Invalid formula syntax: {formula}")
        except SyntaxError as e:
            # Handle specific syntax errors
            error_msg = str(e).lower()
            if "parenthes" in error_msg or "paren" in error_msg:
                # Count parentheses
                open_count = formula.count("(")
                close_count = formula.count(")")
                if open_count != close_count:
                    raise FormulaError(
                        f"Mismatched parentheses in formula: {formula} "
                        f"(found {open_count} '(' and {close_count} ')')"
                    )
                else:
                    raise FormulaError(f"Invalid parentheses structure in formula: {formula}")
            elif "unexpected" in error_msg:
                raise FormulaError(f"Unexpected token in formula: {formula} - {e}")
            else:
                raise FormulaError(f"Formula syntax error: {e}")
        except Exception as e:
            error_str = str(e).lower()
            if "token" in error_str:
                raise FormulaError(f"Invalid token in formula: {formula}")
            raise FormulaError(f"Formula parsing error: {e}")

        # Step 2: Validate sheet references
        # Extract sheet references (handles both 'Sheet Name'!A1 and SheetName!A1)
        sheet_pattern = r"(?:'([^']+)'|([A-Za-z_][\w\s]*))!"
        sheet_refs = re.findall(sheet_pattern, formula)

        for quoted_sheet, unquoted_sheet in sheet_refs:
            sheet_to_check = quoted_sheet if quoted_sheet else unquoted_sheet
            if sheet_to_check not in available_sheets:
                raise FormulaError(
                    f"Formula references non-existent sheet '{sheet_to_check}'. "
                    f"Available sheets: {', '.join(available_sheets)}"
                )

        # Step 2b: Validate range syntax
        # Regex to find malformed ranges like C:(C) or orders.G:(G)
        malformed_range_pattern = r"([A-Za-z_][\w\s]*\.)?([A-Z]{1,3}):\(\2\)"
        malformed_matches = re.finditer(malformed_range_pattern, formula)

        for match in malformed_matches:
            full_match = match.group(0)
            sheet_part = match.group(1) if match.group(1) else ""
            col_part = match.group(2)
            correct_range = f"{sheet_part}{col_part}:{col_part}"
            raise FormulaError(f"Malformed range reference '{full_match}' found. Did you mean '{correct_range}'?")

        # Step 2c: Validate sheet separator
        # Check for sheet.range syntax and suggest sheet!range
        for sheet in available_sheets:
            # Look for "sheet." followed by a cell/range reference. This now handles A1, A:A, and A1:A10 style ranges.
            pattern = rf"\b{re.escape(sheet)}\.([A-Z]{{1,3}}(?:\d{{1,7}})?(?::[A-Z]{{1,3}}(?:\d{{1,7}})?)?)\b"
            matches = re.finditer(pattern, formula)
            for match in matches:
                raise FormulaError(
                    f"Unsupported sheet reference '{match.group(0)}' found. "
                    f"Please use the standard '!' separator (e.g., '{sheet}!{match.group(1)}')."
                )

        # Step 3: Validate Excel function names
        # Extract function names from the formula (allow special characters like #)
        function_pattern = r"\b([A-Z][A-Z0-9#]*)\s*\("
        function_matches = re.findall(function_pattern, formula.upper())

        # Common Excel functions (expanded list, including functions with #)
        valid_excel_functions = {
            # Add functions with special characters
            "XLOOKUP#",
            "LET#",
            "FILTER#",
            "UNIQUE#",
            "SORT#",
            "SEQUENCE#",
            "LAMBDA#",
            # Math & Trig
            "ABS",
            "ACOS",
            "ACOSH",
            "ASIN",
            "ASINH",
            "ATAN",
            "ATAN2",
            "ATANH",
            "CEILING",
            "COMBIN",
            "COS",
            "COSH",
            "DEGREES",
            "EVEN",
            "EXP",
            "FACT",
            "FLOOR",
            "GCD",
            "INT",
            "LCM",
            "LN",
            "LOG",
            "LOG10",
            "MOD",
            "ODD",
            "PI",
            "POWER",
            "PRODUCT",
            "QUOTIENT",
            "RADIANS",
            "RAND",
            "RANDBETWEEN",
            "ROUND",
            "ROUNDDOWN",
            "ROUNDUP",
            "SIGN",
            "SIN",
            "SINH",
            "SQRT",
            "SUM",
            "SUMIF",
            "SUMIFS",
            "SUMPRODUCT",
            "TAN",
            "TANH",
            "TRUNC",
            # Statistical
            "AVERAGE",
            "AVERAGEIF",
            "AVERAGEIFS",
            "COUNT",
            "COUNTA",
            "COUNTBLANK",
            "COUNTIF",
            "COUNTIFS",
            "LARGE",
            "MAX",
            "MEDIAN",
            "MIN",
            "MODE",
            "PERCENTILE",
            "QUARTILE",
            "RANK",
            "SMALL",
            "STDEV",
            "STDEVP",
            "VAR",
            "VARP",
            # Text
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
            # Date & Time
            "DATE",
            "DATEVALUE",
            "DAY",
            "DAYS",
            "HOUR",
            "MINUTE",
            "MONTH",
            "NOW",
            "SECOND",
            "TIME",
            "TIMEVALUE",
            "TODAY",
            "WEEKDAY",
            "YEAR",
            # Lookup & Reference
            "ADDRESS",
            "CHOOSE",
            "COLUMN",
            "COLUMNS",
            "HLOOKUP",
            "INDEX",
            "INDIRECT",
            "LOOKUP",
            "MATCH",
            "OFFSET",
            "ROW",
            "ROWS",
            "VLOOKUP",
            # Logical
            "AND",
            "FALSE",
            "IF",
            "IFERROR",
            "IFNA",
            "IFS",
            "NOT",
            "OR",
            "TRUE",
            "XOR",
            "SWITCH",
            # Information
            "CELL",
            "ERROR.TYPE",
            "INFO",
            "ISBLANK",
            "ISERR",
            "ISERROR",
            "ISEVEN",
            "ISLOGICAL",
            "ISNA",
            "ISNONTEXT",
            "ISNUMBER",
            "ISODD",
            "ISREF",
            "ISTEXT",
            "N",
            "NA",
            "TYPE",
            # Financial
            "FV",
            "IRR",
            "MIRR",
            "NPER",
            "NPV",
            "PMT",
            "PPMT",
            "PV",
            "RATE",
            # Database
            "DAVERAGE",
            "DCOUNT",
            "DCOUNTA",
            "DGET",
            "DMAX",
            "DMIN",
            "DPRODUCT",
            "DSTDEV",
            "DSTDEVP",
            "DSUM",
            "DVAR",
            "DVARP",
            # Engineering
            "BIN2DEC",
            "BIN2HEX",
            "BIN2OCT",
            "DEC2BIN",
            "DEC2HEX",
            "DEC2OCT",
            "HEX2BIN",
            "HEX2DEC",
            "HEX2OCT",
            "OCT2BIN",
            "OCT2DEC",
            "OCT2HEX",
            # Array formulas
            "TRANSPOSE",
            "MMULT",
            "MINVERSE",
            "MDETERM",
            # Modern Excel functions with special characters
            "XLOOKUP#",
            "LET#",
            "FILTER#",
            "UNIQUE#",
            "SORT#",
            "SEQUENCE#",
            "LAMBDA#",
        }

        for func_name in function_matches:
            if func_name not in valid_excel_functions:
                # Check if it might be a custom function or typo
                suggestions = [f for f in valid_excel_functions if f.startswith(func_name[:2])]
                if suggestions:
                    raise FormulaError(
                        f"Unknown function '{func_name}' in formula. "
                        f"Did you mean one of: {', '.join(suggestions[:5])}?"
                    )
                else:
                    raise FormulaError(
                        f"Unknown function '{func_name}' in formula. This is not a valid Excel function."
                    )

        # Step 4: Check for obvious division by zero
        if "/0" in formula.replace(" ", ""):
            raise FormulaError("Formula contains division by zero: /0")

        # Check for division patterns that might cause errors
        div_patterns = [
            r"/\s*\(\s*\)",  # Division by empty parentheses
            r"/\s*\(\s*0\s*\)",  # Division by (0)
            r"/\s*\(\s*0\.0*\s*\)",  # Division by (0.0)
        ]
        for pattern in div_patterns:
            if re.search(pattern, formula):
                raise FormulaError("Formula contains division by zero or empty value")

        # Step 5: Validate cell references
        # Check for invalid cell references
        cell_pattern = r"\b([A-Z]{1,3}\d{1,7})\b"
        cell_refs = re.findall(cell_pattern, formula.upper())

        for cell_ref_check in cell_refs:
            # Validate column (A-XFD)
            col_match = re.match(r"^([A-Z]{1,3})(\d+)$", cell_ref_check)
            if col_match:
                col_letters, row_num = col_match.groups()
                row_num = int(row_num)

                # Excel has max 16384 columns (XFD) and 1048576 rows
                if row_num < 1 or row_num > 1048576:
                    raise FormulaError(
                        f"Invalid row number {row_num} in cell reference {cell_ref_check}. "
                        f"Excel supports rows 1-1048576."
                    )

                # Convert column letters to number
                col_num = 0
                for char in col_letters:
                    col_num = col_num * 26 + (ord(char) - ord("A") + 1)

                if col_num > 16384:
                    raise FormulaError(
                        f"Invalid column {col_letters} in cell reference {cell_ref_check}. "
                        f"Excel supports columns A-XFD (1-16384)."
                    )

        # Step 6: Try to evaluate the formula to catch runtime errors
        try:
            # Create an Excel model for evaluation
            xl_model = formulas.ExcelModel()  # type: ignore

            # Add the current sheet's data
            if sheet_name in sheets_data:
                for cell_addr, value in sheets_data[sheet_name].items():
                    xl_model.set_cell_value(f"{sheet_name}!{cell_addr}", value)  # type: ignore

            # Add other sheets' data with sheet prefix
            for other_sheet, sheet_data in sheets_data.items():
                if other_sheet != sheet_name:
                    for cell_addr, value in sheet_data.items():
                        xl_model.set_cell_value(f"{other_sheet}!{cell_addr}", value)  # type: ignore

            # Set the formula in the model
            full_cell_ref = f"{sheet_name}!{cell_ref}"
            xl_model.set_cell_value(full_cell_ref, formula)  # type: ignore

            # Try to calculate the formula
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # Ignore warnings during evaluation
                result = xl_model.calculate(outputs=[full_cell_ref])  # type: ignore

                # Check if the result is an error
                if full_cell_ref in result:  # type: ignore
                    cell_value = result[full_cell_ref]  # type: ignore

                # Check if the result is an error
                # type: ignore[operator]
                if full_cell_ref in result:
                    cell_value = result[full_cell_ref]  # type: ignore

                    # Check for Excel errors
                    if isinstance(cell_value, formulas.tokens.operand.XlError):
                        error_type = str(cell_value)  # type: ignore
                        if "#DIV/0!" in error_type:
                            raise FormulaError(
                                "Formula will result in #DIV/0! error. Check for division by zero or empty cells."
                            )
                        elif "#NAME?" in error_type:
                            raise FormulaError(
                                "Formula will result in #NAME? error. Check function names and defined names."
                            )
                        elif "#REF!" in error_type:
                            raise FormulaError(
                                "Formula will result in #REF! error. Check cell and sheet references."
                            )
                        elif "#VALUE!" in error_type:
                            raise FormulaError(
                                "Formula will result in #VALUE! error. Check data types and function arguments."
                            )
                        elif "#N/A" in error_type:
                            raise FormulaError(
                                "Formula will result in #N/A error. Check lookup functions and data availability."
                            )
                        elif "#NUM!" in error_type:
                            raise FormulaError(
                                "Formula will result in #NUM! error. "
                                "Check numeric calculations and function arguments."
                            )
                        elif "#NULL!" in error_type:
                            raise FormulaError(
                                "Formula will result in #NULL! error. Check range references and intersections."
                            )
                        else:
                            raise FormulaError(f"Formula will result in Excel error: {error_type}")

        except FormulaError:
            # Re-raise FormulaError as is
            raise
        except Exception as e:
            # Log evaluation errors but don't fail if it's just missing data
            error_str = str(e).lower()
            if "circular" in error_str:
                raise FormulaError(f"Formula contains circular reference: {e}")
            elif "not found" in error_str or "undefined" in error_str:
                # This might be due to missing data, which is okay
                pass
            elif "division" in error_str or "zero" in error_str:
                raise FormulaError(f"Formula may cause division by zero: {e}")
            else:
                # Other evaluation errors might be due to incomplete data, so we'll pass
                pass

    except FormulaError:
        raise
    except Exception as e:
        # Catch any other validation errors
        raise FormulaError(f"Formula validation failed: {e}")


def _write_formula(excel_path: str, sheet_name: str, cell_ref: str, formula: str) -> str:
    """
    Helper function to write a formula to a cell.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
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

        # Ensure formula starts with =
        if not formula.startswith("="):
            formula = "=" + formula

        wb = load_workbook(excel_path)

        if sheet_name not in wb.sheetnames:
            raise SheetNotFoundError(f"Sheet '{sheet_name}' not found")

        # Validate the formula before writing
        _validate_formula(excel_path, sheet_name, cell_ref, formula)

        ws = wb[sheet_name]
        ws[cell_ref] = formula
        wb.save(excel_path)

        return str(excel_file.absolute())

    except (FileNotFoundError, SheetNotFoundError, FormulaError):
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write formula: {e}")


# Date Functions
def write_date_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, function_args: list[Any] | None = None
) -> str:
    """
    Writes date functions to Excel cells.

    Supported functions: DATE, DAY, HOUR, MINUTE, MONTH, NOW, SECOND, TIME, TODAY, WEEKDAY, YEAR

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the date function
        function_args: Function arguments

     Returns:
        str: Excel file path

    Example:
        result = write_date_function("file.xlsx", "Sheet1", "A1", "TODAY")

    """
    try:
        function_name = function_name.upper()
        if function_args is None:
            function_args = []

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write date function: {e}")


# Financial Functions
def write_financial_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes financial functions to Excel cells.

    Supported functions: FV, IRR, NPV, PMT, PV

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the financial function
        function_args: Function arguments

     Returns:
        str: Excel file path

    Example:
        result = write_financial_function("file.xlsx", "Sheet1", "A1", "PV", [0.05, 10, -1000])

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write financial function: {e}")


# Logical Functions
def write_logical_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, conditions: list[Any] | None = None
) -> str:
    """
    Writes logical functions to Excel cells.

    Supported functions: AND, FALSE, IF, IFERROR, NOT, OR, TRUE

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the logical function
        conditions: Function conditions/arguments

     Returns:
        str: Excel file path

    Example:
        result = write_logical_function("file.xlsx", "Sheet1", "A1", "IF", ["B1>10", '"Yes"', '"No"'])

    """
    try:
        function_name = function_name.upper()
        if conditions is None:
            conditions = []

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write logical function: {e}")


# Lookup Functions
def write_lookup_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, function_args: list[Any] | None = None
) -> str:
    """
    Writes lookup functions to Excel cells.

    Supported functions: CHOOSE, COLUMN, COLUMNS, HLOOKUP, INDEX, INDIRECT,
                        MATCH, OFFSET, ROW, ROWS, VLOOKUP

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the lookup function
        function_args: Function arguments

     Returns:
        str: Excel file path

    Example:
        result = write_lookup_function("file.xlsx", "Sheet1", "A1", "VLOOKUP", ["B1", "D:E", 2, "FALSE"])

    """
    try:
        function_name = function_name.upper()
        if function_args is None:
            function_args = []

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write lookup function: {e}")


# Math Functions
def write_math_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, function_args: list[Any] | None = None
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
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the math function
        function_args: Function arguments

     Returns:
        str: Excel file path

    Example:
        result = write_math_function("file.xlsx", "Sheet1", "A1", "SUM", ["B1:B10"])

    """
    try:
        function_name = function_name.upper()
        if function_args is None:
            function_args = []

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write math function: {e}")


# Statistical Functions
def write_statistical_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes statistical functions to Excel cells.

    Supported functions: AVERAGE, AVERAGEIF, AVERAGEIFS, COUNT, COUNTA, COUNTBLANK,
                        LARGE, MEDIAN, MODE, PERCENTILE, QUARTILE, RANK, SMALL, STDEV, VAR

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the statistical function
        function_args: Function data/arguments

     Returns:
        str: Excel file path

    Example:
        result = write_statistical_function("file.xlsx", "Sheet1", "A1", "AVERAGE", ["B1:B10"])

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write statistical function: {e}")


# Text Functions
def write_text_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes text functions to Excel cells.

    Supported functions: CHAR, CLEAN, CODE, CONCATENATE, EXACT, FIND, LEFT, LEN,
                        LOWER, MID, PROPER, REPLACE, REPT, RIGHT, SEARCH, SUBSTITUTE,
                        TEXT, TRIM, UPPER, VALUE

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the text function
        function_args: Function text arguments

     Returns:
        str: Excel file path

    Example:
        result = write_text_function("file.xlsx", "Sheet1", "A1", "CONCATENATE", ["A1", "B1"])

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write text function: {e}")


# Info Functions
def write_info_function(
    excel_path: str, sheet_name: str, cell_ref: str, function_name: str, function_args: list[Any]
) -> str:
    """
    Writes info functions to Excel cells.

    Supported functions: ISBLANK, ISERROR, ISNUMBER, ISTEXT

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        function_name: Name of the info function
        function_args: Function arguments

     Returns:
        str: Excel file path

    Example:
        result = write_info_function("file.xlsx", "Sheet1", "A1", "ISBLANK", ["B1"])

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

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write info function: {e}")


# Arithmetic Operations
def write_arithmetic_operation(
    excel_path: str, sheet_name: str, cell_ref: str, operation: str, operands: list[str]
) -> str:
    """
    Writes arithmetic operations to Excel cells.

    Supported operations: ADD, SUBTRACT, MULTIPLY, DIVIDE, POWER

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        operation: Type of arithmetic operation
        operands: List of cell references, values, or nested expressions

     Returns:
        str: Excel file path

    Example:
        result = write_arithmetic_operation("file.xlsx", "Sheet1", "A1", "DIVIDE", ["B1", "C1"])

    """
    try:
        operation = operation.upper()
        valid_operations = {"ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "POWER"}

        if operation not in valid_operations:
            raise FormulaError(f"Invalid operation: {operation}. Valid operations: {sorted(valid_operations)}")

        if len(operands) < 2:
            raise FormulaError(f"Operation {operation} requires at least 2 operands")

        # Build formula based on operation
        formula = ""
        if operation == "ADD":
            formula = "+".join(operands)
        elif operation == "SUBTRACT":
            if len(operands) > 2:
                # For multiple operands: first - (second + third + ...)
                formula = f"{operands[0]}-({'+'.join(operands[1:])})"
            else:
                formula = "-".join(operands)
        elif operation == "MULTIPLY":
            formula = "*".join(operands)
        elif operation == "DIVIDE":
            if len(operands) > 2:
                # For multiple operands: first / (second * third * ...)
                formula = f"{operands[0]}/({('*'.join(operands[1:]))})"
            else:
                formula = "/".join(operands)
        elif operation == "POWER":
            if len(operands) != 2:
                raise FormulaError("POWER operation requires exactly 2 operands")
            formula = f"POWER({operands[0]},{operands[1]})"

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write arithmetic operation: {e}")


def write_comparison_operation(
    excel_path: str, sheet_name: str, cell_ref: str, left_operand: str, operator: str, right_operand: str
) -> str:
    """
    Writes comparison operations to Excel cells.

    Supported operators: =, <>, <, >, <=, >=

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        left_operand: Left side of comparison (cell reference, value, or expression)
        operator: Comparison operator
        right_operand: Right side of comparison (cell reference, value, or expression)

     Returns:
        str: Excel file path

    Example:
        result = write_comparison_operation("file.xlsx", "Sheet1", "A1", "B1", ">", "10")

    """
    try:
        valid_operators = {"=", "<>", "<", ">", "<=", ">="}

        if operator not in valid_operators:
            raise FormulaError(f"Invalid operator: {operator}. Valid operators: {sorted(valid_operators)}")

        formula = f"{left_operand}{operator}{right_operand}"
        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write comparison operation: {e}")


def write_nested_function(
    excel_path: str,
    sheet_name: str,
    cell_ref: str,
    outer_function: str,
    inner_functions: list[str],
    outer_args: list[str] | None = None,
) -> str:
    """
    Writes nested function calls to Excel cells.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        outer_function: Name of the outer function (e.g., "IF", "SUM")
        inner_functions: List of inner function expressions
        outer_args: Additional arguments for the outer function

     Returns:
        str: Excel file path

    Example:
        result = write_nested_function("file.xlsx", "Sheet1", "A1", "IF",
                            ["COUNTIFS(C:C,\"Pro\",E:E,\"<=2023-01-01\")=0"],
                            ["1/B3", "COUNTIFS(F:F,\"<=2023-12-31\")"])

    """
    try:
        outer_function = outer_function.upper()

        # Build the formula
        all_args = inner_functions.copy()
        if outer_args:
            all_args.extend(outer_args)

        args_str = ",".join(all_args)
        formula = f"{outer_function}({args_str})"

        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write nested function: {e}")


def write_conditional_formula(
    excel_path: str, sheet_name: str, cell_ref: str, condition: str, true_value: str, false_value: str
) -> str:
    """
    Writes IF conditional formulas to Excel cells.

    Args:
        excel_path: Path to the Excel file
        sheet_name: Name of the target sheet
        cell_ref: Cell reference (e.g., 'A1')
        condition: Condition to evaluate
        true_value: Value/expression when condition is true
        false_value: Value/expression when condition is false

     Returns:
        str: Excel file path

    Example:
        result = write_conditional_formula("file.xlsx", "Sheet1", "A1",
                                "COUNTIFS(C:C,\"Pro\")=0",
                                "1/B3",
                                "COUNTIFS(F:F,\"Churned\")/COUNTIFS(C:C,\"Pro\")")

    """
    try:
        formula = f"IF({condition},{true_value},{false_value})"
        return _write_formula(excel_path, sheet_name, cell_ref, formula)

    except FormulaError:
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to write conditional formula: {e}")


# Function Expression Builder
def build_countifs_expression(range_criteria_pairs: list[tuple[str, str]]) -> str:
    """
    Builds a COUNTIFS expression string.

    Args:
        range_criteria_pairs: List of (range, criteria) tuples

    Returns:
        str: COUNTIFS expression

    Example:
        build_countifs_expression([
            ("Raw_Subscriptions.C:C", "\"Pro\""),
            ("Raw_Subscriptions.E:E", "\"<=2023-01-01\"")
        ])
        # Returns: 'COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")'
    """
    if not range_criteria_pairs:
        raise FormulaError("COUNTIFS requires at least one range-criteria pair")

    args: list[str] = []
    for range_ref, criteria in range_criteria_pairs:
        args.extend([range_ref, criteria])

    args_str = ",".join(args)
    return f"COUNTIFS({args_str})"


def build_division_expression(numerator: str, denominator: str) -> str:
    """
    Builds a division expression string.

    Args:
        numerator: Numerator expression
        denominator: Denominator expression

    Returns:
        str: Division expression

    Example:
        build_division_expression("COUNTIFS(A:A,\"Yes\")", "COUNTIFS(B:B,\"Total\")")
        # Returns: 'COUNTIFS(A:A,"Yes")/COUNTIFS(B:B,"Total")'
    """
    return f"{numerator}/{denominator}"


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
        write_date_function(excel_path, "Sheet", "E1", "TODAY")
        write_date_function(excel_path, "Sheet", "E2", "YEAR", ["E1"])

        print("Formulas added to Excel file!")

    except FormulaError as e:
        print(f"Formula validation error: {e}")
    except Exception as e:
        print(f"Error: {e}")
