"""
Demo showing how to build complex formulas using building blocks
without actually writing to Excel files.
"""

from src.dreamai.toolsets.excel_formula_toolset import (
    build_countifs_expression,
    build_division_expression,
)


def demo_complex_formula_building():
    """
    Demonstrates building the complex formula using building blocks.
    """

    print("=== Building Complex Formula Using Building Blocks ===\n")

    print("Original complex formula:")
    original = '=IF(COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")=0,1/Assumptions.B3,COUNTIFS(Raw_Subscriptions.F:F,"<=2023-12-31",Raw_Subscriptions.F:F,">=2023-01-01",Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.G:G,"Churned")/COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01"))'
    print(f"{original}\n")

    print("Step 1: Build condition - Count Pro subscriptions before 2023")
    condition_countifs = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )
    condition = f"{condition_countifs}=0"
    print(f"Condition: {condition}\n")

    print("Step 2: True value - Fallback calculation")
    true_value = "1/Assumptions.B3"
    print(f"True value: {true_value}\n")

    print("Step 3: False value - Actual churn rate calculation")

    print("  3a: Numerator - Churned Pro subscriptions in 2023")
    numerator = build_countifs_expression(
        [
            ("Raw_Subscriptions.F:F", '"<=2023-12-31"'),
            ("Raw_Subscriptions.F:F", '">=2023-01-01"'),
            ("Raw_Subscriptions.C:C", '"Pro"'),
            ("Raw_Subscriptions.G:G", '"Churned"'),
        ]
    )
    print(f"  Numerator: {numerator}")

    print("  3b: Denominator - Total Pro subscriptions before 2023")
    denominator = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )
    print(f"  Denominator: {denominator}")

    print("  3c: Division expression")
    false_value = build_division_expression(numerator, denominator)
    print(f"  False value: {false_value}\n")

    print("Step 4: Complete IF formula")
    complete_formula = f"IF({condition},{true_value},{false_value})"
    print(f"Complete formula: ={complete_formula}\n")

    print("=== Benefits of Building Block Approach ===")
    print("✓ Each component is validated separately")
    print("✓ AI agent can't inject arbitrary code")
    print("✓ Formula structure is controlled and predictable")
    print("✓ Easy to debug and modify individual components")
    print("✓ Reusable components across different formulas")
    print("✓ Type-safe function parameters")


def demo_available_building_blocks():
    """
    Shows all available building blocks for AI agents.
    """

    print("\n=== Available Building Blocks for AI Agents ===\n")

    building_blocks = {
        "Mathematical Functions": [
            "write_math_function() - SUM, COUNTIFS, MAX, MIN, etc.",
            "write_arithmetic_operation() - ADD, SUBTRACT, MULTIPLY, DIVIDE, POWER",
        ],
        "Logical Functions": [
            "write_logical_function() - IF, AND, OR, NOT",
            "write_conditional_formula() - Simplified IF statements",
            "write_comparison_operation() - =, <>, <, >, <=, >=",
        ],
        "Specialized Functions": [
            "write_date_function() - DATE, TODAY, YEAR, MONTH, etc.",
            "write_financial_function() - PV, FV, NPV, PMT, IRR",
            "write_statistical_function() - AVERAGE, MEDIAN, STDEV, etc.",
            "write_text_function() - CONCATENATE, LEFT, RIGHT, etc.",
            "write_lookup_function() - VLOOKUP, INDEX, MATCH, etc.",
            "write_info_function() - ISBLANK, ISERROR, ISNUMBER, etc.",
        ],
        "Helper Functions": [
            "build_countifs_expression() - Constructs COUNTIFS formulas",
            "build_division_expression() - Constructs division expressions",
            "write_nested_function() - For complex function nesting",
        ],
    }

    for category, functions in building_blocks.items():
        print(f"{category}:")
        for func in functions:
            print(f"  • {func}")
        print()


def demo_step_by_step_approach():
    """
    Shows alternative step-by-step approach for transparency.
    """

    print("=== Alternative: Step-by-Step Approach ===\n")
    print("Instead of one complex formula, break it into multiple cells:")
    print()

    # Step 1: Count Pro subscriptions before 2023
    step1 = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )
    print(f"A1 (Pro subs before 2023): {step1}")

    # Step 2: Count churned Pro subscriptions in 2023
    step2 = build_countifs_expression(
        [
            ("Raw_Subscriptions.F:F", '"<=2023-12-31"'),
            ("Raw_Subscriptions.F:F", '">=2023-01-01"'),
            ("Raw_Subscriptions.C:C", '"Pro"'),
            ("Raw_Subscriptions.G:G", '"Churned"'),
        ]
    )
    print(f"A2 (Churned Pro in 2023): {step2}")

    # Step 3: Calculate churn rate
    step3 = build_division_expression("A2", "A1")
    print(f"A3 (Churn rate): {step3}")

    # Step 4: Final conditional formula
    step4 = "IF(A1=0,1/Assumptions.B3,A3)"
    print(f"A4 (Final result): {step4}")

    print("\nBenefits of step-by-step approach:")
    print("✓ Each step can be tested individually")
    print("✓ Easier debugging and validation")
    print("✓ More transparent for users")
    print("✓ Can reuse intermediate calculations")


if __name__ == "__main__":
    demo_complex_formula_building()
    demo_available_building_blocks()
    demo_step_by_step_approach()
