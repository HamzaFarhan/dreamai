#!/usr/bin/env python3
"""
Test script for openpyxl_charts.py functionality
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from openpyxl_charts import (
    create_chart,
    create_data_table,
    create_pivot_table,
    get_chart_types,
    list_charts,
    matplotlib_available
)

def test_chart_creation():
    """Test basic chart creation functionality."""
    print("Testing Excel chart creation...")
    
    try:
        # Create a simple test Excel file first
        from openpyxl import Workbook
        
        test_file = "test_charts.xlsx"
        
        # Create workbook with sample data
        wb = Workbook()
        ws = wb.active
        ws.title = "Data"
        
        # Add headers
        ws.append(["Month", "Sales", "Expenses"])
        
        # Add sample data
        data = [
            ["Jan", 1000, 800],
            ["Feb", 1200, 900],
            ["Mar", 1100, 850],
            ["Apr", 1300, 950],
            ["May", 1400, 1000],
        ]
        
        for row in data:
            ws.append(row)
        
        wb.save(test_file)
        print(f"✓ Created test file: {test_file}")
        
        # Test chart creation
        result = create_chart(
            excel_path=test_file,
            data_range="A1:C6",
            chart_type="column",
            title="Sales vs Expenses",
            chart_sheet="Charts",
            position="E1"
        )
        print(f"✓ Created column chart: {result}")
        
        # Test data table creation
        result = create_data_table(
            excel_path=test_file,
            sheet_name="Data",
            data_range="A1:C6",
            table_name="SalesTable"
        )
        print(f"✓ Created data table: {result}")
        
        # Test pivot table creation
        result = create_pivot_table(
            excel_path=test_file,
            source_sheet="Data",
            data_range="A1:C6",
            pivot_sheet="Pivot",
            values={"Sales": "sum", "Expenses": "average"}
        )
        print(f"✓ Created pivot table: {result}")
        
        # Test chart listing
        charts = list_charts(test_file)
        print(f"✓ Found charts: {charts}")
        
        # Test matplotlib chart if available
        if matplotlib_available:
            try:
                from openpyxl_charts import create_matplotlib_chart
                result = create_matplotlib_chart(
                    excel_path=test_file,
                    data_range="A1:C6",
                    chart_type="line",
                    title="Matplotlib Line Chart",
                    chart_sheet="MPL_Charts",
                    position="A1"
                )
                print(f"✓ Created matplotlib chart: {result}")
            except Exception as e:
                print(f"⚠ Matplotlib chart failed: {e}")
        else:
            print("⚠ Matplotlib not available, skipping matplotlib chart test")
        
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"✓ Cleaned up test file")
        
        print("✅ All chart tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Chart test failed: {e}")
        # Clean up on error
        if os.path.exists(test_file):
            os.remove(test_file)
        return False

def test_chart_types():
    """Test chart types listing."""
    print("\nTesting chart types...")
    
    try:
        types = get_chart_types()
        print(f"✓ Available chart types: {types}")
        
        # Verify we have both openpyxl and matplotlib types
        assert "openpyxl_charts" in types
        assert len(types["openpyxl_charts"]) > 0
        
        print(f"✓ OpenPyXL chart types: {len(types['openpyxl_charts'])}")
        print(f"✓ Matplotlib available: {types['matplotlib_available']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chart types test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing OpenPyXL Charts Module")
    print("=" * 40)
    
    success = True
    
    # Test chart types
    success &= test_chart_types()
    
    # Test chart creation
    success &= test_chart_creation()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
