#!/usr/bin/env python3

"""
Test chart sizing with explicit dimensions to verify the fix.
"""

from pathlib import Path

import pandas as pd

from finn.toolsets.excel_toolsets.excel_charts_toolset import create_chart


def test_chart_dimensions():
    """Test charts with specific dimensions."""

    # Simple test data
    data = {"Month": ["Jan", "Feb", "Mar", "Apr", "May"], "Sales": [100, 120, 90, 150, 130]}

    df = pd.DataFrame(data)
    excel_path = Path("/Users/hamza/dev/dreamai/dimension_test.xlsx")

    # Write data to Excel
    df.to_excel(excel_path, index=False, sheet_name="Data")

    # Test 1: Small chart (5 columns x 4 rows)
    create_chart(
        excel_path=str(excel_path),
        data_range="Data!A1:B6",
        chart_type="column",
        title="Small Chart (5x4)",
        position="D2",
        width=5,  # 5 columns wide
        height=4,  # 4 rows tall
    )

    # Test 2: Medium chart (8 columns x 6 rows)
    create_chart(
        excel_path=str(excel_path),
        data_range="Data!A1:B6",
        chart_type="line",
        title="Medium Chart (8x6)",
        position="J2",
        width=8,  # 8 columns wide
        height=6,  # 6 rows tall
    )

    # Test 3: Large chart (12 columns x 10 rows)
    create_chart(
        excel_path=str(excel_path),
        data_range="Data!A1:B6",
        chart_type="area",
        title="Large Chart (12x10)",
        position="D10",
        width=12,  # 12 columns wide
        height=10,  # 10 rows tall
    )

    print(f"✅ Created dimension test file: {excel_path}")
    print("Charts created with different sizes:")
    print("  - Small: 5 columns × 4 rows (position D2)")
    print("  - Medium: 8 columns × 6 rows (position J2)")
    print("  - Large: 12 columns × 10 rows (position D10)")
    print("\nOpen the file to verify the charts are sized correctly!")

    return str(excel_path)


if __name__ == "__main__":
    test_file = test_chart_dimensions()
    print(f"\n📊 Dimension test completed: {test_file}")
