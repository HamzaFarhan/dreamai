#!/usr/bin/env python3
"""Test script to verify formula validation works."""

import tempfile
from pathlib import Path

from openpyxl import Workbook

from src.dreamai.toolsets.excel_formula_toolset import (
    FormulaError,
    write_formula_to_cell,
    write_logical_function,
    write_math_function,
)


def create_test_file() -> str:
    """Create a temporary Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        wb = Workbook()
        wb.save(tmp.name)
        return tmp.name


def test_valid_formulas():
    """Test that valid formulas work."""
    print("Testing valid formulas...")
    file_path = create_test_file()

    try:
        # Valid formulas should work
        write_math_function(file_path, "Sheet", "A1", "SUM", ["B1:B10"])
        write_logical_function(file_path, "Sheet", "A2", "IF", ["B1>0", '"Yes"', '"No"'])
        write_formula_to_cell(file_path, "Sheet", "A3", "=A1+A2")
        print("✅ Valid formulas passed")
    except Exception as e:
        print(f"❌ Valid formulas failed: {e}")
    finally:
        Path(file_path).unlink(missing_ok=True)


def test_invalid_cell_references():
    """Test that invalid cell references are caught."""
    print("Testing invalid cell references...")
    file_path = create_test_file()

    try:
        # Invalid cell reference should fail
        write_formula_to_cell(file_path, "Sheet", "A", "=1+1")
        print("❌ Should have caught invalid cell reference")
    except FormulaError as e:
        print(f"✅ Caught invalid cell reference: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        Path(file_path).unlink(missing_ok=True)


def test_invalid_range_references():
    """Test that invalid range references are caught."""
    print("Testing invalid range references...")
    file_path = create_test_file()

    try:
        # Invalid range reference should fail
        write_math_function(file_path, "Sheet", "A1", "SUM", ["A1:Z"])
        print("❌ Should have caught invalid range reference")
    except FormulaError as e:
        print(f"✅ Caught invalid range reference: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        Path(file_path).unlink(missing_ok=True)


def test_formula_syntax_errors():
    """Test that formula syntax errors are caught."""
    print("Testing formula syntax errors...")
    file_path = create_test_file()

    try:
        # Mismatched parentheses should fail
        write_formula_to_cell(file_path, "Sheet", "A1", "=SUM(B1:B10")
        print("❌ Should have caught syntax error")
    except FormulaError as e:
        print(f"✅ Caught syntax error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        Path(file_path).unlink(missing_ok=True)


def test_function_argument_validation():
    """Test that function argument validation works."""
    print("Testing function argument validation...")
    file_path = create_test_file()

    try:
        # IF function with too few arguments should fail
        write_logical_function(file_path, "Sheet", "A1", "IF", ["B1>0"])
        print("❌ Should have caught insufficient arguments")
    except FormulaError as e:
        print(f"✅ Caught argument validation error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        Path(file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print("Running formula validation tests...\n")

    test_valid_formulas()
    test_invalid_cell_references()
    test_invalid_range_references()
    test_formula_syntax_errors()
    test_function_argument_validation()

    print("\nTests completed!")
