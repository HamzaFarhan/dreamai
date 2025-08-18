"""
Example showing how to build complex formulas using building blocks
instead of raw formula input.

This demonstrates building the complex formula:
=IF(COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01")=0,1/Assumptions.B3,COUNTIFS(Raw_Subscriptions.F:F,"<=2023-12-31",Raw_Subscriptions.F:F,">=2023-01-01",Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.G:G,"Churned")/COUNTIFS(Raw_Subscriptions.C:C,"Pro",Raw_Subscriptions.E:E,"<=2023-01-01"))
"""

from src.dreamai.toolsets.excel_formula_toolset import (
    build_countifs_expression,
    build_division_expression,
    write_conditional_formula,
)


def build_complex_churn_formula(excel_path: str, sheet_name: str, cell_ref: str) -> str:
    """
    Build the complex churn rate formula using building blocks.

    This is an AI agent-friendly approach that breaks down the complex formula
    into controlled, validated building blocks.
    """

    # Step 1: Build the condition - check if there are any Pro subscriptions before 2023
    condition_countifs = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )
    condition = f"{condition_countifs}=0"

    # Step 2: Build the true value - if no Pro subs before 2023, use 1/Assumptions.B3
    true_value = "1/Assumptions.B3"

    # Step 3: Build the false value - calculate actual churn rate
    # Numerator: Churned Pro subscriptions in 2023
    numerator_countifs = build_countifs_expression(
        [
            ("Raw_Subscriptions.F:F", '"<=2023-12-31"'),
            ("Raw_Subscriptions.F:F", '">=2023-01-01"'),
            ("Raw_Subscriptions.C:C", '"Pro"'),
            ("Raw_Subscriptions.G:G", '"Churned"'),
        ]
    )

    # Denominator: Total Pro subscriptions before 2023
    denominator_countifs = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )

    # Build division expression
    false_value = build_division_expression(numerator_countifs, denominator_countifs)

    # Step 4: Combine everything into an IF statement
    return write_conditional_formula(
        excel_path=excel_path,
        sheet_name=sheet_name,
        cell_ref=cell_ref,
        condition=condition,
        true_value=true_value,
        false_value=false_value,
    )


def alternative_step_by_step_approach() -> dict[str, str]:
    """
    Alternative approach: Build the formula step by step in separate cells.
    This provides more transparency and debuggability for AI agents.
    """

    formulas: dict[str, str] = {}

    # Step 1: Count Pro subscriptions before 2023
    formulas["A1"] = build_countifs_expression(
        [("Raw_Subscriptions.C:C", '"Pro"'), ("Raw_Subscriptions.E:E", '"<=2023-01-01"')]
    )

    # Step 2: Count churned Pro subscriptions in 2023
    formulas["A2"] = build_countifs_expression(
        [
            ("Raw_Subscriptions.F:F", '"<=2023-12-31"'),
            ("Raw_Subscriptions.F:F", '">=2023-01-01"'),
            ("Raw_Subscriptions.C:C", '"Pro"'),
            ("Raw_Subscriptions.G:G", '"Churned"'),
        ]
    )

    # Step 3: Calculate churn rate
    formulas["A3"] = build_division_expression("A2", "A1")

    # Step 4: Final conditional formula
    formulas["A4"] = "IF(A1=0,1/Assumptions.B3,A3)"

    return formulas


def demonstrate_ai_agent_workflow():
    """
    Demonstrates how an AI agent would use these building blocks.

    The agent gets tool functions and can compose them safely without
    allowing arbitrary formula injection.
    """

    # Available tools for the AI agent:
    available_tools = [
        "write_math_function",  # For COUNTIFS, SUM, etc.
        "write_logical_function",  # For IF, AND, OR
        "write_arithmetic_operation",  # For +, -, *, /, ^
        "write_comparison_operation",  # For =, <>, <, >, <=, >=
        "write_conditional_formula",  # For IF statements
        "build_countifs_expression",  # Helper for COUNTIFS
        "build_division_expression",  # Helper for division
        "write_nested_function",  # For complex nesting
    ]

    # The agent can combine these tools to build complex formulas
    # without being able to inject arbitrary Excel code

    print("Available building blocks for AI agent:")
    for tool in available_tools:
        print(f"  - {tool}")

    print("\nExample workflow:")
    print("1. Agent identifies need for COUNTIFS operation")
    print("2. Agent calls build_countifs_expression() with validated parameters")
    print("3. Agent identifies need for division")
    print("4. Agent calls build_division_expression() with numerator and denominator")
    print("5. Agent combines into conditional with write_conditional_formula()")
    print("6. All formulas are validated before being written to Excel")


if __name__ == "__main__":
    demonstrate_ai_agent_workflow()

    # Example usage
    excel_path = "churn_analysis.xlsx"
    sheet_name = "Calculations"

    # Build complex formula using building blocks
    result = build_complex_churn_formula(excel_path, sheet_name, "B5")
    print(f"\nBuilt complex formula and saved to {result}")

    # Alternative step-by-step approach
    formulas = alternative_step_by_step_approach()
    print("\nStep-by-step formulas:")
    for cell, formula in formulas.items():
        print(f"  {cell}: {formula}")
