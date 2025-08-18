"""
Test to verify that the building blocks can recreate complex formulas correctly.
"""

from src.dreamai.toolsets.excel_formula_toolset import (
    build_countifs_expression,
    build_division_expression,
)


def test_building_blocks():
    """Test that building blocks produce the expected formulas."""

    print("=== Testing Building Blocks ===\n")

    # Test COUNTIFS builder
    print("1. Testing build_countifs_expression:")
    countifs_result = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )
    expected_countifs = 'COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")'

    print(f"   Result: {countifs_result}")
    print(f"   Expected: {expected_countifs}")
    print(f"   ✓ Match: {countifs_result == expected_countifs}\n")

    # Test division builder
    print("2. Testing build_division_expression:")
    division_result = build_division_expression("SUM(A1:A10)", "COUNT(B1:B10)")
    expected_division = "SUM(A1:A10)/COUNT(B1:B10)"

    print(f"   Result: {division_result}")
    print(f"   Expected: {expected_division}")
    print(f"   ✓ Match: {division_result == expected_division}\n")

    # Test complex formula reconstruction
    print("3. Testing complex formula reconstruction:")

    # Build the condition
    condition_expr = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )
    condition = f"{condition_expr}=0"

    # Build the numerator and denominator for false value
    numerator = build_countifs_expression(
        [
            ("Raw_Subscriptions.F:F", '"<=2023-12-31"'),
            ("Raw_Subscriptions.F:F", '">=2023-01-01"'),
            ("Raw_Subscriptions.C:C", '"Pro"'),
            ("Raw_Subscriptions.G:G", '"Churned"'),
        ]
    )

    denominator = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )

    false_value = build_division_expression(numerator, denominator)

    # Build complete formula
    reconstructed = f"IF({condition},1/Assumptions.B3,{false_value})"

    # Expected original formula (without the = prefix)
    original = 'IF(COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")=0,1/Assumptions.B3,COUNTIFS(Raw_Subscriptions.F:F,"<=2023-12-31",Raw_Subscriptions.F:F,">=2023-01-01",Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.G:G,"Churned")/COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01"))'

    print(f"   Reconstructed: {reconstructed}")
    print(f"   Original:      {original}")
    print(f"   ✓ Match: {reconstructed == original}\n")

    if reconstructed == original:
        print("🎉 SUCCESS: Building blocks can recreate the complex formula exactly!")
    else:
        print("❌ MISMATCH: Need to adjust building blocks")

        # Show differences for debugging
        print("\nDetailed comparison:")
        print(f"Length - Reconstructed: {len(reconstructed)}, Original: {len(original)}")

        min_len = min(len(reconstructed), len(original))
        for i in range(min_len):
            if reconstructed[i] != original[i]:
                print(f"First difference at position {i}:")
                print(f"  Reconstructed: '{reconstructed[max(0, i - 10) : i + 10]}'")
                print(f"  Original:      '{original[max(0, i - 10) : i + 10]}'")
                break


if __name__ == "__main__":
    test_building_blocks()
