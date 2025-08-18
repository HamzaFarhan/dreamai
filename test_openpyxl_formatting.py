#!/usr/bin/env python3
"""
Test script for openpyxl_formatting.py

Creates a test Excel file and demonstrates the formatting functions.
"""

import tempfile
from pathlib import Path

from openpyxl import Workbook

# Import our formatting functions
from excel_formatting_toolset import (
    apply_cell_formatting,
    apply_conditional_formatting,
    apply_preset_formatting,
    clear_formatting,
    create_formatting_preset,
    load_formatting_preset,
)


def create_test_workbook(file_path: str) -> str:
    """Create a test workbook with some sample data."""
    wb = Workbook()
    ws = wb.active
    ws.title = "TestSheet"

    # Add some sample data
    data = [
        ["Name", "Score", "Grade"],
        ["Alice", 95, "A"],
        ["Bob", 87, "B"],
        ["Charlie", 72, "C"],
        ["Diana", 89, "B"],
        ["Eve", 96, "A"],
    ]

    for row_idx, row_data in enumerate(data, 1):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    wb.save(file_path)
    return file_path


def test_basic_formatting():
    """Test basic cell formatting."""
    print("Testing basic cell formatting...")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        test_file = tmp.name

    try:
        # Create test workbook
        create_test_workbook(test_file)

        # Apply header formatting
        header_format = {
            "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.8},
            "textFormat": {
                "bold": True,
                "fontSize": 12,
                "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
            },
        }

        result = apply_cell_formatting(test_file, "A1:C1", header_format)
        print(f"✓ Header formatting applied to: {result}")

        # Apply data formatting
        data_format = {"textFormat": {"fontSize": 10}}

        result = apply_cell_formatting(test_file, "A2:C6", data_format)
        print(f"✓ Data formatting applied to: {result}")

    finally:
        Path(test_file).unlink(missing_ok=True)


def test_conditional_formatting():
    """Test conditional formatting."""
    print("\nTesting conditional formatting...")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        test_file = tmp.name

    try:
        # Create test workbook
        create_test_workbook(test_file)

        # Apply conditional formatting for high scores
        condition = {"type": "GREATER_THAN", "values": [{"userEnteredValue": "90"}]}

        format_style = {"backgroundColor": {"red": 0.8, "green": 1.0, "blue": 0.8}, "textFormat": {"bold": True}}

        result = apply_conditional_formatting(test_file, "B2:B6", condition, format_style)
        print(f"✓ Conditional formatting applied to: {result}")

    finally:
        Path(test_file).unlink(missing_ok=True)


def test_presets():
    """Test formatting presets."""
    print("\nTesting formatting presets...")

    # Create a preset
    preset_format = {
        "backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.6},
        "textFormat": {"bold": True, "italic": True, "fontSize": 11},
    }

    preset_file = create_formatting_preset("warning_style", preset_format)
    print(f"✓ Preset created and saved to: {preset_file}")

    # Load the preset
    loaded_format = load_formatting_preset("warning_style")
    print(f"✓ Preset loaded: {loaded_format}")

    # Apply preset to a file
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        test_file = tmp.name

    try:
        create_test_workbook(test_file)
        result = apply_preset_formatting(test_file, "A1:C1", "warning_style")
        print(f"✓ Preset formatting applied to: {result}")

    finally:
        Path(test_file).unlink(missing_ok=True)


def test_clear_formatting():
    """Test clearing formatting."""
    print("\nTesting clear formatting...")

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        test_file = tmp.name

    try:
        # Create test workbook
        create_test_workbook(test_file)

        # Apply some formatting first
        format_data = {
            "backgroundColor": {"red": 0.9, "green": 0.5, "blue": 0.5},
            "textFormat": {"bold": True, "fontSize": 14},
        }

        apply_cell_formatting(test_file, "A1:C6", format_data)
        print("✓ Applied formatting to test range")

        # Clear formatting
        result = clear_formatting(test_file, "A1:C6")
        print(f"✓ Formatting cleared from: {result}")

    finally:
        Path(test_file).unlink(missing_ok=True)


if __name__ == "__main__":
    print("Running openpyxl_formatting tests...\n")

    try:
        test_basic_formatting()
        test_conditional_formatting()
        test_presets()
        test_clear_formatting()

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise
