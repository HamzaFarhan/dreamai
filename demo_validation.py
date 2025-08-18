#!/usr/bin/env python3
"""
Demonstration of enhanced Excel formula validation.

This script shows how the enhanced formula toolset catches various
types of errors that would otherwise only show up when opening
the Excel file.
"""

import tempfile
from pathlib import Path

from openpyxl import Workbook

from src.dreamai.toolsets.excel_formula_toolset import (
    FormulaError,
    write_formula_to_cell,
    write_logical_function,
    write_math_function,
    write_multiple_formulas,
)


def create_test_file() -> str:
    """Create a temporary Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        wb = Workbook()
        wb.save(tmp.name)
        return tmp.name


def demonstrate_validation():
    """Demonstrate various validation scenarios."""
    file_path = create_test_file()

    print("📊 Excel Formula Validation Demo")
    print("=" * 50)

    # 1. Valid formulas
    print("\n✅ Testing valid formulas:")
    try:
        write_math_function(file_path, "Sheet", "A1", "SUM", ["B1:B10"])
        print("   ✓ SUM(B1:B10) - Valid")

        write_logical_function(file_path, "Sheet", "A2", "IF", ["B1>0", '"Positive"', '"Not Positive"'])
        print('   ✓ IF(B1>0,"Positive","Not Positive") - Valid')

        write_formula_to_cell(file_path, "Sheet", "A3", "=VLOOKUP(A1,D:E,2,FALSE)")
        print("   ✓ VLOOKUP(A1,D:E,2,FALSE) - Valid")

    except FormulaError as e:
        print(f"   ✗ Unexpected validation error: {e}")

    # 2. Invalid cell references
    print("\n❌ Testing invalid cell references:")
    try:
        write_formula_to_cell(file_path, "Sheet", "A", "=1+1")
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    try:
        write_formula_to_cell(file_path, "Sheet", "1A", "=1+1")
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    # 3. Invalid range references
    print("\n❌ Testing invalid range references:")
    try:
        write_math_function(file_path, "Sheet", "A4", "SUM", ["A1:Z"])
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    try:
        write_math_function(file_path, "Sheet", "A5", "AVERAGE", ["A:"])
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    # 4. Syntax errors
    print("\n❌ Testing formula syntax errors:")
    try:
        write_formula_to_cell(file_path, "Sheet", "A6", "=SUM(A1:A10")  # Missing closing paren
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    try:
        write_formula_to_cell(file_path, "Sheet", "A7", "=IF(A1>0,TRUE,")  # Incomplete formula
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    # 5. Function argument validation
    print("\n❌ Testing function argument validation:")
    try:
        write_logical_function(file_path, "Sheet", "A8", "IF", ["A1>0"])  # Missing arguments
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    try:
        write_logical_function(file_path, "Sheet", "A9", "TRUE", ["unnecessary_arg"])  # Too many args
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught: {e}")

    # 6. Batch validation
    print("\n📝 Testing batch formula validation:")
    try:
        formulas = {
            "B1": "=SUM(C1:C10)",
            "B2": "=AVERAGE(C1:C10)",
            "B3": '=IF(B1>B2,"Above Average","Below Average")',
            "B4": "=SUM(C1:C10",  # This one has syntax error
        }
        write_multiple_formulas(file_path, "Sheet", formulas)
        print("   ✗ Should have failed!")
    except FormulaError as e:
        print(f"   ✓ Caught batch validation error: {e}")

    # 7. Valid batch operation
    try:
        valid_formulas = {
            "B1": "=SUM(C1:C10)",
            "B2": "=AVERAGE(C1:C10)",
            "B3": '=IF(B1>B2,"Above Average","Below Average")',
        }
        write_multiple_formulas(file_path, "Sheet", valid_formulas)
        print("   ✓ Valid batch formulas succeeded")
    except FormulaError as e:
        print(f"   ✗ Unexpected error: {e}")

    print("\n" + "=" * 50)
    print("🎉 Validation demo completed!")
    print("\nBenefits of enhanced validation:")
    print("• Catches errors during Python execution, not when Excel opens")
    print("• Validates cell and range references")
    print("• Checks formula syntax (parentheses matching, etc.)")
    print("• Validates function arguments for common Excel functions")
    print("• Provides detailed error messages for debugging")

    # Cleanup
    Path(file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    demonstrate_validation()
