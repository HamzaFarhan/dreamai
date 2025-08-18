## Data Sources
Using existing CSV files in `workspaces/session/data/`

## Output Location
Create Excel analysis file: `results/ltv_analysis.xlsx`

## Data Setup
**Sheet name:** `analysis`
**File path:** `results/ltv_analysis.xlsx`
**Target sheet:** `analysis`

do all calculations from jan 2023 to dec 2023

### Formula 1: Basic - Average Revenue Per User (ARPU)
Calculate average monthly revenue for all customers
**Tool:** `write_math_function`

### Formula 2: Intermediate - Churn Rate Calculation  
Calculate churn rate (churned customers / total active customers at start)
**Tool:** `write_arithmetic_operation` 

### Formula 3: Complex - LTV Calculation with Conditional Logic
Calculate LTV with assumption that 0% churn = 60 months (5 years)
**Tool:** `write_conditional_formula` 

## Expected Test Results
Based on the CSV data structure:
- Formula 1 (ARPU): Should return average of monthly subscription prices
- Formula 2 (Churn Rate): Should return percentage of customers who churned in 2023
- Formula 3 (LTV): Should return LTV value, handling division by zero case


## Success Criteria
- All 3 formulas write successfully without parse errors
- Formulas calculate correctly when opened in Excel/Google Sheets  
- No #DIV/0!, #NAME?, or #REF! errors
- Results reflect actual customer data from your CSV files
- File saved to `results/ltv_analysis.xlsx`
