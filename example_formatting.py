"""
Example usage of openpyxl_formatting functions

This demonstrates how to use the local Excel formatting functions
instead of Google Sheets APIs.
"""

from excel_formatting_toolset import (
    apply_cell_formatting,
    apply_conditional_formatting,
    apply_preset_formatting,
    create_formatting_preset,
)
from openpyxl_utils import create_excel_file, write_data_to_sheet


def create_formatted_report(excel_path: str) -> str:
    """
    Create a formatted Excel report demonstrating various formatting options.

    Args:
        excel_path: Path where the Excel file will be created

    Returns:
        Path to the created Excel file
    """
    # Create Excel file
    create_excel_file(excel_path)

    # Add sample data
    data = [
        ["Product", "Q1 Sales", "Q2 Sales", "Q3 Sales", "Q4 Sales", "Total"],
        ["Widget A", 15000, 18000, 22000, 19000, "=SUM(B2:E2)"],
        ["Widget B", 12000, 14000, 16000, 18000, "=SUM(B3:E3)"],
        ["Widget C", 8000, 9500, 11000, 13000, "=SUM(B4:E4)"],
        ["Widget D", 20000, 22000, 25000, 28000, "=SUM(B5:E5)"],
        ["TOTAL", "=SUM(B2:B5)", "=SUM(C2:C5)", "=SUM(D2:D5)", "=SUM(E2:E5)", "=SUM(F2:F5)"],
    ]

    write_data_to_sheet(excel_path, "Sheet", data)

    # Format header row
    header_format = {
        "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8},
        "textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
    }
    apply_cell_formatting(excel_path, "A1:F1", header_format)

    # Format total row
    total_format = {
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
        "textFormat": {"bold": True, "fontSize": 11},
    }
    apply_cell_formatting(excel_path, "A6:F6", total_format)

    # Apply conditional formatting for high sales (> 20000)
    high_sales_condition = {"type": "GREATER_THAN", "values": [{"userEnteredValue": "20000"}]}

    high_sales_format = {"backgroundColor": {"red": 0.8, "green": 1.0, "blue": 0.8}, "textFormat": {"bold": True}}

    # Apply to quarterly sales columns
    for col in ["B", "C", "D", "E"]:
        apply_conditional_formatting(excel_path, f"{col}2:{col}5", high_sales_condition, high_sales_format)

    # Create and apply a custom preset for total column
    total_preset = {
        "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.7},
        "textFormat": {"bold": True, "fontSize": 11, "foregroundColor": {"red": 0.2, "green": 0.2, "blue": 0.8}},
    }

    create_formatting_preset("total_column", total_preset)
    apply_preset_formatting(excel_path, "F2:F5", "total_column")

    return excel_path


if __name__ == "__main__":
    # Create example report
    output_path = "/Users/hamza/dev/dreamai/sample_formatted_report.xlsx"

    try:
        result_path = create_formatted_report(output_path)
        print(f"✅ Formatted report created at: {result_path}")
        print("\nThe report includes:")
        print("• Blue header row with white text")
        print("• Gray total row with bold text")
        print("• Green highlighting for sales > 20,000")
        print("• Yellow total column with custom preset")
        print("\nOpen the file in Excel to see the formatting!")

    except Exception as e:
        print(f"❌ Error creating report: {e}")
