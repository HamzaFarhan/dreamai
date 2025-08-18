#!/usr/bin/env python3
"""Test the specific complex formula that caused parse errors."""

import tempfile
from pathlib import Path

from openpyxl import Workbook

from src.dreamai.toolsets.excel_formula_toolset import (
    FormulaError,
    write_formula_to_cell,
)


def create_test_file() -> str:
    """Create a temporary Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        wb = Workbook()
        wb.save(tmp.name)
        return tmp.name


def test_complex_formula():
    """Test the complex formula that was causing parse errors."""
    file_path = create_test_file()

    # The formula that was causing issues
    complex_formula = """=IF(COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")=0,1/Assumptions.B3,COUNTIFS(Raw_Subscriptions.F:F,"<=2023-12-31",Raw_Subscriptions.F:F,">=2023-01-01",Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.G:G,"Churned")/COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01"))"""

    print("Testing complex formula that previously caused parse errors:")
    print(f"Formula: {complex_formula}")
    print()

    try:
        result = write_formula_to_cell(file_path, "Sheet", "A1", complex_formula)
        print("✅ Formula validation passed!")
        print(f"Formula written to: {result}")

        # Let's also test some variations that might be problematic
        print("\nTesting variations...")

        # Test with worksheet references without proper escaping
        problematic_formula1 = '=COUNTIFS(Sheet.A:A,"value")'
        try:
            write_formula_to_cell(file_path, "Sheet", "A2", problematic_formula1)
            print("✅ Worksheet reference formula passed")
        except FormulaError as e:
            print(f"❌ Worksheet reference failed: {e}")

        # Test with date comparisons
        date_formula = '=COUNTIFS(A:A,"<=2023-12-31",B:B,">="&DATE(2023,1,1))'
        try:
            write_formula_to_cell(file_path, "Sheet", "A3", date_formula)
            print("✅ Date comparison formula passed")
        except FormulaError as e:
            print(f"❌ Date comparison failed: {e}")

    except FormulaError as e:
        print(f"❌ Formula validation failed: {e}")
        print("\nThis suggests the issue might be:")
        if "parentheses" in str(e).lower():
            print("- Mismatched parentheses")
        elif "reference" in str(e).lower():
            print("- Invalid cell/range references")
        elif "syntax" in str(e).lower():
            print("- General syntax issues")
        else:
            print("- Other validation issue")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        Path(file_path).unlink(missing_ok=True)


def analyze_formula_structure():
    """Analyze the structure of the problematic formula."""
    formula = """IF(COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")=0,1/Assumptions.B3,COUNTIFS(Raw_Subscriptions.F:F,"<=2023-12-31",Raw_Subscriptions.F:F,">=2023-01-01",Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.G:G,"Churned")/COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01"))"""

    print("🔍 Analyzing formula structure:")
    print(f"Formula: {formula}")
    print()

    # Count parentheses
    open_parens = formula.count("(")
    close_parens = formula.count(")")
    print(f"Open parentheses: {open_parens}")
    print(f"Close parentheses: {close_parens}")
    print(f"Balanced: {'✅ Yes' if open_parens == close_parens else '❌ No'}")
    print()

    # Look for potential issues
    issues = []

    # Check for worksheet references with dots
    if "." in formula and any(c.isalpha() for c in formula.split(".")[0][-10:]):
        issues.append("Contains worksheet references (e.g., 'Raw_Subscriptions.C:C')")

    # Check for comparison operators in strings
    if any(op in formula for op in ["<=", ">=", "<>", "="]):
        issues.append("Contains comparison operators that might confuse parsing")

    # Check for date-like strings
    if "2023" in formula:
        issues.append("Contains date strings that might need special handling")

    if issues:
        print("⚠️  Potential issues identified:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("✅ No obvious structural issues found")


if __name__ == "__main__":
    print("🧪 Complex Formula Parse Error Analysis")
    print("=" * 50)

    analyze_formula_structure()
    print("\n" + "=" * 50)
    test_complex_formula()
