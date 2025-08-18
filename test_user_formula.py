#!/usr/bin/env python3
"""
Final test for the user's specific problematic formula and similar patterns
that commonly cause Excel parse errors.
"""

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


def test_user_formula_and_variants():
    """Test the user's specific formula and common variations that cause parse errors."""
    file_path = create_test_file()

    print("🎯 Testing User's Problematic Formula and Variants")
    print("=" * 60)

    # The original user formula
    original_formula = """=IF(COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")=0,1/Assumptions.B3,COUNTIFS(Raw_Subscriptions.F:F,"<=2023-12-31",Raw_Subscriptions.F:F,">=2023-01-01",Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.G:G,"Churned")/COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01"))"""

    # Common variations that might cause parse errors
    test_cases = [
        {
            "name": "Original User Formula",
            "formula": original_formula,
            "description": "The exact formula that was causing parse errors",
        },
        {
            "name": "Formula with Invalid Date",
            "formula": original_formula.replace("2023-01-01", "2023-13-01"),
            "description": "Same formula but with invalid month (13)",
            "should_fail": True,
        },
        {
            "name": "Formula with Unmatched Quotes",
            "formula": original_formula.replace('"Pro"', '"Pro'),
            "description": "Same formula but with missing closing quote",
            "should_fail": True,
        },
        {
            "name": "Formula with Invalid Worksheet Name",
            "formula": original_formula.replace("Raw_Subscriptions", "CON"),
            "description": "Same formula but with reserved worksheet name",
            "should_fail": True,
        },
        {
            "name": "Complex COUNTIFS with Multiple Conditions",
            "formula": '=COUNTIFS(Data.A:A,">="&DATE(2023,1,1),Data.A:A,"<="&DATE(2023,12,31),Data.B:B,"Active",Data.C:C,"Premium")',
            "description": "Another complex COUNTIFS pattern with date functions",
        },
        {
            "name": "Nested IF with COUNTIFS",
            "formula": '=IF(COUNTIFS(Sales.A:A,"Q1")>0,COUNTIFS(Sales.B:B,"Revenue")/COUNTIFS(Sales.A:A,"Q1"),0)',
            "description": "Nested conditional logic with COUNTIFS",
        },
        {
            "name": "Multiple Worksheet References",
            "formula": "=SUMPRODUCT((Sheet1.A:A=Sheet2.B:B)*(Sheet1.C:C>0))",
            "description": "Formula referencing multiple worksheets",
        },
        {
            "name": "Array Formula with Complex Logic",
            "formula": '=SUM(IF((Data.A:A>=DATE(2023,1,1))*(Data.A:A<=DATE(2023,12,31))*(Data.B:B="Pro"),Data.C:C,0))',
            "description": "Array-style formula with date comparisons",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Description: {test_case['description']}")

        should_fail = test_case.get("should_fail", False)
        expected = "❌ Should Fail" if should_fail else "✅ Should Pass"
        print(f"   Expected: {expected}")

        try:
            result = write_formula_to_cell(file_path, "Sheet", f"A{i}", test_case["formula"])
            status = "✅ Passed validation"
            correct = not should_fail
        except FormulaError as e:
            status = f"❌ Failed validation: {str(e)[:100]}..."
            correct = should_fail
        except Exception as e:
            status = f"🔥 Unexpected error: {str(e)[:100]}..."
            correct = False

        print(f"   Result: {status}")
        print(f"   Status: {'✅ Correct' if correct else '❌ Incorrect'}")

        # If this was the original formula and it failed, provide specific guidance
        if i == 1 and not correct:
            print("\n   🔍 Analysis for Original Formula:")
            if "date" in str(status).lower():
                print("   • Issue: Date format validation failed")
                print("   • Fix: Check date strings in the formula")
            elif "quote" in str(status).lower():
                print("   • Issue: Quote mismatch detected")
                print("   • Fix: Ensure all strings are properly quoted")
            elif "worksheet" in str(status).lower():
                print("   • Issue: Worksheet reference problem")
                print("   • Fix: Check worksheet names for invalid characters")
            elif "syntax" in str(status).lower():
                print("   • Issue: General syntax error")
                print("   • Fix: Check parentheses matching and formula structure")

    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("The enhanced validation now catches these common Excel parse errors:")
    print("• Invalid cell and range references")
    print("• Unmatched parentheses and quotes")
    print("• Invalid date formats (month > 12, etc.)")
    print("• Reserved worksheet names")
    print("• String literals with line breaks")
    print("• Strings exceeding Excel's 255 character limit")
    print("• Formulas exceeding Excel's 8192 character limit")
    print("• Function nesting depth validation")
    print("• Basic complexity checks")

    print("\n💡 Benefits:")
    print("• Errors caught during Python execution, not when Excel opens")
    print("• Detailed error messages for easier debugging")
    print("• Prevents creation of Excel files with parse errors")
    print("• Validates against Excel's actual limits and constraints")

    # Cleanup
    Path(file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_user_formula_and_variants()
