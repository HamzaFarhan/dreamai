#!/usr/bin/env python3

"""
Create a dummy Excel file with sample data and various charts for testing.
"""

from pathlib import Path

import pandas as pd

from finn.toolsets.excel_toolsets.excel_charts_toolset import create_chart


def create_sample_excel_with_charts():
    """Create an Excel file with sample data and multiple charts."""

    # Create sample data
    monthly_data = {
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Sales": [12000, 14500, 13200, 16800, 15200, 17500, 19200, 18100, 16900, 15600, 14800, 16200],
        "Expenses": [8000, 8500, 8200, 9200, 8800, 9500, 10200, 9800, 9300, 8900, 8600, 9100],
        "Profit": [4000, 6000, 5000, 7600, 6400, 8000, 9000, 8300, 7600, 6700, 6200, 7100],
    }

    quarterly_data = {
        "Quarter": ["Q1", "Q2", "Q3", "Q4"],
        "Revenue": [45000, 52000, 58000, 48000],
        "Market_Share": [15.5, 17.2, 19.1, 16.8],
    }

    product_data = {
        "Product": ["Product A", "Product B", "Product C", "Product D", "Product E"],
        "Units_Sold": [1200, 980, 1450, 760, 890],
        "Revenue": [24000, 19600, 29000, 15200, 17800],
    }

    # Create Excel file path
    excel_path = Path("/Users/hamza/dev/dreamai/sample_charts.xlsx")

    # Create DataFrames
    monthly_df = pd.DataFrame(monthly_data)
    quarterly_df = pd.DataFrame(quarterly_data)
    product_df = pd.DataFrame(product_data)

    # Write data to Excel with multiple sheets
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        monthly_df.to_excel(writer, sheet_name="Monthly_Data", index=False)
        quarterly_df.to_excel(writer, sheet_name="Quarterly_Data", index=False)
        product_df.to_excel(writer, sheet_name="Product_Data", index=False)

    print(f"📊 Created Excel file: {excel_path}")

    # Create various charts
    charts_created = []

    try:
        # 1. Column chart for monthly sales
        result = create_chart(
            excel_path=str(excel_path),
            data_range="Monthly_Data!A1:B13",
            chart_type="column",
            title="Monthly Sales Performance",
            position="E2",
            width=15,  # 15 * 20 = 300 points (about 4 inches)
            height=10,  # 10 * 20 = 200 points (about 3 inches)
        )
        charts_created.append("Column Chart - Monthly Sales")

        # 2. Line chart for profit trend
        result = create_chart(
            excel_path=str(excel_path),
            data_range="Monthly_Data!A1:D13",
            chart_type="line",
            title="Monthly Profit Trend",
            position="E20",  # More spacing - moved from E16 to E20
            width=15,
            height=10,
        )
        charts_created.append("Line Chart - Profit Trend")

        # 3. Bar chart for quarterly revenue
        result = create_chart(
            excel_path=str(excel_path),
            data_range="Quarterly_Data!A1:B5",
            chart_type="bar",
            title="Quarterly Revenue",
            chart_sheet="Quarterly_Data",
            position="D2",
            width=14,
            height=8,
        )
        charts_created.append("Bar Chart - Quarterly Revenue")

        # 4. Pie chart for product revenue distribution
        result = create_chart(
            excel_path=str(excel_path),
            data_range="Product_Data!A1:C6",
            chart_type="pie",
            title="Product Revenue Distribution",
            chart_sheet="Product_Data",
            position="E2",
            width=12,
            height=12,
        )
        charts_created.append("Pie Chart - Product Revenue")

        # 5. Area chart for expenses vs sales
        result = create_chart(
            excel_path=str(excel_path),
            data_range="Monthly_Data!A1:C13",
            chart_type="area",
            title="Sales vs Expenses Over Time",
            position="E38",  # More spacing - moved from E30 to E38
            width=16,
            height=10,
        )
        charts_created.append("Area Chart - Sales vs Expenses")

        print("\n✅ Successfully created charts:")
        for i, chart in enumerate(charts_created, 1):
            print(f"   {i}. {chart}")

        print(f"\n📂 Excel file saved to: {excel_path}")
        print("🔍 Open the file to inspect the charts and their sizes!")

        return str(excel_path)

    except Exception as e:
        print(f"❌ Error creating charts: {e}")
        return None


if __name__ == "__main__":
    excel_file = create_sample_excel_with_charts()
    if excel_file:
        print(f"\n🎉 All done! Check out your charts in: {excel_file}")
    else:
        print("❌ Failed to create charts")
