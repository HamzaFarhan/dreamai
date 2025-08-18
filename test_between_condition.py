#!/usr/bin/env python3
"""
Test script for the BETWEEN condition in openpyxl_formatting.py
"""

import tempfile
from pathlib import Path

from openpyxl import Workbook

from excel_formatting_toolset import apply_conditional_formatting


def test_between_condition():
    """Test the BETWEEN conditional formatting."""
    print("Testing BETWEEN conditional formatting...")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        test_file = tmp.name

    try:
        # Create test workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "TestSheet"

        # Add some sample data
        data = [
            ["Value"],
            [10],
            [25],
            [50],
            [75],
            [90],
        ]

        for row_idx, row_data in enumerate(data, 1):
            for col_idx, value in enumerate(row_data, 1):
                ws.cell(row=row_idx, column=col_idx, value=value)

        wb.save(test_file)

        # Test BETWEEN with list format
        condition = {"type": "BETWEEN", "values": [{"userEnteredValue": "20"}, {"userEnteredValue": "80"}]}

        format_style = {"backgroundColor": {"red": 0.8, "green": 1.0, "blue": 0.8}, "textFormat": {"bold": True}}

        result = apply_conditional_formatting(test_file, "A2:A6", condition, format_style)
        print(f"✓ BETWEEN conditional formatting applied to: {result}")

        # Test BETWEEN with tuple format
        condition2 = {
            "type": "BETWEEN",
            "value": [30, 70],  # This should work with direct list
        }

        result2 = apply_conditional_formatting(test_file, "A2:A6", condition2, format_style)
        print(f"✓ BETWEEN with direct values applied to: {result2}")

    finally:
        Path(test_file).unlink(missing_ok=True)


if __name__ == "__main__":
    test_between_condition()
    print("✅ BETWEEN condition test completed!")
