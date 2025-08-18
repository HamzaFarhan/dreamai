"""Test script to verify the csv_to_excel_sheet fix."""

import csv
import tempfile
from pathlib import Path

from src.dreamai.toolsets.excel_structure_toolset import csv_to_excel_sheet


def test_csv_with_different_delimiters():
    """Test CSV files with different delimiters."""

    # Test data
    test_data = [["Name", "Age", "Score"], ["Alice", "25", "95.5"], ["Bob", "30", "87"], ["Charlie", "22", "92.3"]]

    delimiters = [",", ";", "\t", "|"]

    for delimiter in delimiters:
        print(f"Testing delimiter: '{delimiter}'")

        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as csv_file:
            writer = csv.writer(csv_file, delimiter=delimiter)
            writer.writerows(test_data)
            csv_path = csv_file.name

        # Create temporary Excel file path
        excel_path = csv_path.replace(".csv", ".xlsx")

        try:
            # Test the function
            result = csv_to_excel_sheet(
                csv_path=csv_path, excel_path=excel_path, sheet_name=f"test_{delimiter.replace(chr(9), 'tab')}"
            )
            print(f"✓ Success with delimiter '{delimiter}': {result}")

        except Exception as e:
            print(f"✗ Failed with delimiter '{delimiter}': {e}")

        finally:
            # Cleanup
            Path(csv_path).unlink(missing_ok=True)
            Path(excel_path).unlink(missing_ok=True)


def test_problematic_csv():
    """Test CSV that might cause delimiter detection issues."""

    # Create a CSV that might be problematic for the sniffer
    problematic_data = [
        "ProductName,Category,Price",
        "Item with, comma,Electronics,99.99",
        "Simple Item,Books,15.50",
        "Another, tricky item,Home,25.00",
    ]

    # Create temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as csv_file:
        csv_file.write("\n".join(problematic_data))
        csv_path = csv_file.name

    excel_path = csv_path.replace(".csv", ".xlsx")

    try:
        result = csv_to_excel_sheet(csv_path=csv_path, excel_path=excel_path, sheet_name="problematic_data")
        print(f"✓ Success with problematic CSV: {result}")

    except Exception as e:
        print(f"✗ Failed with problematic CSV: {e}")

    finally:
        # Cleanup
        Path(csv_path).unlink(missing_ok=True)
        Path(excel_path).unlink(missing_ok=True)


if __name__ == "__main__":
    print("Testing csv_to_excel_sheet function with delimiter detection fix...")
    print("=" * 60)

    test_csv_with_different_delimiters()
    print()
    test_problematic_csv()

    print("\nTest complete!")
