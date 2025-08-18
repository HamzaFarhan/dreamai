#!/usr/bin/env python3
"""Test enhanced validation with the problematic formula."""

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


def test_enhanced_validation():
    """Test the enhanced validation with problematic scenarios."""
    file_path = create_test_file()

    print("🔬 Testing Enhanced Formula Validation")
    print("=" * 50)

    # Test cases that might cause Excel parse errors
    test_cases = [
        {
            "name": "Original complex formula",
            "formula": '=IF(COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")=0,1/Assumptions.B3,COUNTIFS(Raw_Subscriptions.F:F,"<=2023-12-31",Raw_Subscriptions.F:F,">=2023-01-01",Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.G:G,"Churned")/COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01"))',
            "should_pass": True,
        },
        {"name": "Formula with invalid worksheet name", "formula": "=SUM(CON.A:A)", "should_pass": False},
        {"name": "Formula with unmatched quotes", "formula": '=IF(A1="test,B1,"error")', "should_pass": False},
        {
            "name": "Formula with line breaks in string",
            "formula": '=CONCATENATE("Line 1\n", "Line 2")',
            "should_pass": False,
        },
        {"name": "Formula with invalid date", "formula": '=COUNTIFS(A:A,"<=2023-13-01")', "should_pass": False},
        {
            "name": "Formula with too long string",
            "formula": f'=CONCATENATE("{("x" * 300)}")',
            "should_pass": False,
        },
        {
            "name": "Very long formula",
            "formula": "=" + "+".join([f"A{i}" for i in range(1, 2000)]),
            "should_pass": False,
        },
        {"name": "Valid complex VLOOKUP", "formula": "=VLOOKUP(A1,Data.B:F,3,FALSE)", "should_pass": True},
        {
            "name": "Valid nested functions",
            "formula": '=IF(ISBLANK(A1),"",INDEX(Data.B:B,MATCH(A1,Data.A:A,0)))',
            "should_pass": True,
        },
    ]

    passed = 0
    total = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Expected: {'✅ Pass' if test_case['should_pass'] else '❌ Fail'}")

        try:
            write_formula_to_cell(file_path, "Sheet", f"A{i}", test_case["formula"])
            result = "✅ Passed validation"
            correct = test_case["should_pass"]
        except FormulaError as e:
            result = f"❌ Failed validation: {e}"
            correct = not test_case["should_pass"]
        except Exception as e:
            result = f"🔥 Unexpected error: {e}"
            correct = False

        print(f"   Result: {result}")
        print(f"   Status: {'✅ Correct' if correct else '❌ Incorrect'}")

        if correct:
            passed += 1

    print("\n" + "=" * 50)
    print(f"🎯 Results: {passed}/{total} tests correct")

    if passed == total:
        print("🎉 All validation tests passed!")
    else:
        print("⚠️  Some tests failed - validation may need improvement")

    # Cleanup
    Path(file_path).unlink(missing_ok=True)


def test_specific_problematic_patterns():
    """Test specific patterns that commonly cause Excel parse errors."""
    file_path = create_test_file()

    print("\n🎯 Testing Specific Problematic Patterns")
    print("=" * 50)

    patterns = [
        {
            "name": "Table references with spaces",
            "formula": '=COUNTIFS(Table Name.Column:Column,"value")',
            "description": "Worksheet names with spaces need brackets",
        },
        {
            "name": "Mixed comparison operators",
            "formula": '=COUNTIFS(A:A,">="&B1,A:A,"<="&C1)',
            "description": "Dynamic date comparisons",
        },
        {
            "name": "Complex nested conditions",
            "formula": '=IF(AND(COUNTIFS(A:A,"condition1")>0,COUNTIFS(B:B,"condition2")=0),"result1","result2")',
            "description": "Multiple COUNTIFS in logical functions",
        },
        {
            "name": "External reference pattern",
            "formula": "=COUNTIFS('[Workbook.xlsx]Sheet'!A:A,\"value\")",
            "description": "External workbook references",
        },
    ]

    for pattern in patterns:
        print(f"\n🔍 {pattern['name']}")
        print(f"   Description: {pattern['description']}")
        print(f"   Formula: {pattern['formula']}")

        try:
            write_formula_to_cell(file_path, "Sheet", "A1", pattern["formula"])
            print("   Result: ✅ Validation passed")
        except FormulaError as e:
            print(f"   Result: ❌ Validation failed: {e}")
        except Exception as e:
            print(f"   Result: 🔥 Unexpected error: {e}")

    # Cleanup
    Path(file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_enhanced_validation()
    test_specific_problematic_patterns()
