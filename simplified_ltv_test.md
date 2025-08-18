# Simplified LTV/CAC Test Scenario

## Goal
Test Excel formula toolset with a basic LTV calculation using 3 formulas of increasing complexity.

## Data Sources
Using existing CSV files in `workspaces/session/data/`:
- **customers.csv** - CustomerID, Geography, IndustrySegment, AcquisitionChannel, etc.
- **subscriptions.csv** - SubscriptionID, CustomerID, PlanName, SubscriptionType, StartDate, EndDate, Status, MonthlyPrice
- **orders.csv** - OrderID, CustomerID, OrderDate, PlanName, Amount, Profit

## Output Location
Create Excel analysis file: `results/ltv_analysis.xlsx`

## Data Setup
First, we'll need to create an Excel file with processed data from the CSVs. For this test, assume we have a simplified Excel sheet with these calculated columns:

**Sheet name:** `analysis`
**Columns:**
- A: Customer_ID 
- B: Plan_Type (Basic, Pro, Enterprise)
- C: Monthly_Revenue (from subscriptions.MonthlyPrice)
- D: Active_Jan_2023 (1 if active in Jan 2023, 0 if not)
- E: Churned_2023 (1 if churned in 2023, 0 if still active)
- F: Total_Profit_2023 (sum of profit from orders in 2023)

## Test Implementation
Using your Excel formula toolset, write these formulas to the results file:

**File path:** `results/ltv_analysis.xlsx`
**Target sheet:** `analysis`

### Formula 1: Basic - Average Revenue Per User (ARPU)
**Target cell H1:** Calculate average monthly revenue for all customers
**Tool:** `write_math_function` with AVERAGE function and range C:C

### Formula 2: Intermediate - Churn Rate Calculation  
**Target cell H2:** Calculate churn rate (churned customers / total active customers at start)
**Tool:** `write_arithmetic_operation` with DIVIDE operation using SUMIF functions

### Formula 3: Complex - LTV Calculation with Conditional Logic
**Target cell H3:** Calculate LTV with assumption that 0% churn = 60 months (5 years)
**Tool:** `write_conditional_formula` with IF logic for zero churn handling

## Expected Test Results
Based on the CSV data structure:
- Formula 1 (ARPU): Should return average of monthly subscription prices
- Formula 2 (Churn Rate): Should return percentage of customers who churned in 2023
- Formula 3 (LTV): Should return LTV value, handling division by zero case

## Sample Data Processing
From your CSV files, the test data would look like:
```
Customer_ID | Plan_Type | Monthly_Revenue | Active_Jan_2023 | Churned_2023 | Total_Profit_2023
ab3be78d... | Basic     | 50             | 1              | 1            | 240
fd1bbe00... | Pro       | 120            | 0              | 1            | 0
dd47c3db... | Pro       | 135            | 0              | 1            | 540
```

## Success Criteria
- All 3 formulas write successfully without parse errors
- Formulas calculate correctly when opened in Excel/Google Sheets  
- No #DIV/0!, #NAME?, or #REF! errors
- Results reflect actual customer data from your CSV files
- File saved to `results/ltv_analysis.xlsx`
