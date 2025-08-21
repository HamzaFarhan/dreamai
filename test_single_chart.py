#!/usr/bin/env python3

"""
Quick test to verify chart sizing is working correctly.
"""

from pathlib import Path

import pandas as pd

from finn.toolsets.excel_toolsets.excel_charts_toolset import create_chart


def test_single_chart():
    """Test a single chart with known good dimensions."""

    # Simple test data
    data = {"Category": ["A", "B", "C", "D"], "Values": [10, 25, 15, 30]}

    df = pd.DataFrame(data)
    excel_path = Path("/Users/hamza/dev/dreamai/test_chart_size.xlsx")

    # Write data to Excel
    df.to_excel(excel_path, index=False, sheet_name="TestData")

    # Create a reasonably sized chart
    result = create_chart(
        excel_path=str(excel_path),
        data_range="TestData!A1:B5",
        chart_type="column",
        title="Test Chart - Should be Normal Size",
        position="D2",
        width=12,  # 12 * 20 = 240 points (~3.3 inches) - reasonable
        height=8,  # 8 * 20 = 160 points (~2.2 inches) - reasonable
    )

    print(f"✅ Test chart created: {result}")
    print("Chart should be approximately 3.3 x 2.2 inches (normal size)")
    print("If it's huge or tiny, the sizing is still wrong!")

    return str(excel_path)


if __name__ == "__main__":
    test_file = test_single_chart()
    print(f"\n📊 Open {test_file} to check the chart size")
