#!/usr/bin/env python3
"""
Test script for enhanced openpyxl_utils functions
"""

from pathlib import Path

from openpyxl_utils import (
    add_sheet,
    create_excel_file,
    duplicate_sheet_to_file,
    get_sheet_info,
    get_spreadsheet_metadata,
    update_sheet_dimensions,
    update_sheet_properties,
)


def test_enhanced_functions():
    """Test the new enhanced functions"""
    try:
        # Create test file
        test_file = "test_enhanced.xlsx"
        print("Creating test Excel file...")
        file_path = create_excel_file(test_file)
        print(f"✅ Created: {file_path}")

        # Add additional sheets
        print("\nAdding sheets...")
        add_sheet(test_file, "Data")
        add_sheet(test_file, "Analysis")
        print("✅ Added sheets: Data, Analysis")

        # Test get_spreadsheet_metadata
        print("\nTesting get_spreadsheet_metadata...")
        metadata = get_spreadsheet_metadata(test_file)
        print(f"✅ Metadata: {metadata['sheet_count']} sheets found")
        print(f"   Sheets: {metadata['sheet_names']}")

        # Test update_sheet_dimensions
        print("\nTesting update_sheet_dimensions...")
        update_sheet_dimensions(test_file, "Data", row_count=500, column_count=20)
        print("✅ Updated sheet dimensions")

        # Test update_sheet_properties
        print("\nTesting update_sheet_properties...")
        update_sheet_properties(test_file, "Analysis", new_title="Advanced_Analysis")
        print("✅ Renamed sheet Analysis to Advanced_Analysis")

        # Test get_sheet_info
        print("\nTesting get_sheet_info...")
        sheet_info = get_sheet_info(test_file, "Data")
        print(f"✅ Sheet info: {sheet_info['max_row']} rows, {sheet_info['max_column']} columns")

        # Test duplicate_sheet_to_file
        print("\nTesting duplicate_sheet_to_file...")
        target_file = "test_target.xlsx"
        duplicate_sheet_to_file(test_file, "Data", target_file, "Copied_Data")
        print(f"✅ Duplicated sheet to {target_file}")

        # Final metadata check
        print("\nFinal metadata check...")
        final_metadata = get_spreadsheet_metadata(test_file)
        print(f"✅ Final state: {final_metadata['sheet_names']}")

        # Clean up
        Path(test_file).unlink(missing_ok=True)
        Path(target_file).unlink(missing_ok=True)
        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        # Clean up on error
        Path("test_enhanced.xlsx").unlink(missing_ok=True)
        Path("test_target.xlsx").unlink(missing_ok=True)


if __name__ == "__main__":
    test_enhanced_functions()
