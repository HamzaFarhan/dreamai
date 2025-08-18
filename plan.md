## SEQUENTIAL STEPS

- [X] Explore and understand data structure from all relevant CSV files (customers, subscriptions, orders, marketing_spend)
**Toolsets**: 

- [X] Create Excel workbook with initial structure and assumptions sheet with 5-year churn assumption toggle
**Toolsets**: excel_structure_toolset

- [X] Process customer data to identify initial subscription and plan types for each customer (first subscription record)
**Toolsets**: excel_structure_toolset, excel_formula_toolset

- [ ] Calculate customers active on Jan 1, 2023 by subscription type, plan type, industry, and channel
**Toolsets**: excel_structure_toolset, excel_formula_toolset

- [ ] Identify churned customers during 2023 (status changed to cancelled/churned or EndDate in 2023) from Jan 1, 2023 active base
**Toolsets**: excel_structure_toolset, excel_formula_toolset

- [ ] Calculate churn rates by subscription type, plan type, industry, and channel using formula (churned customers / customers at beginning)
**Toolsets**: excel_formula_toolset

- [ ] Calculate revenue and profit per user for 2023 orders by customer segments
**Toolsets**: excel_structure_toolset, excel_formula_toolset

- [ ] Calculate profit margins by segment (Total Profit / Total Revenue)
**Toolsets**: excel_formula_toolset

- [ ] Calculate LTV using formula: (Average Revenue per User / Churn Rate) × Profit Margin for each segment
**Toolsets**: excel_formula_toolset

- [ ] Create "Total Customer LTV" tab with overall LTV by subscription types (monthly, annual, total combined)
**Toolsets**: excel_structure_toolset, excel_formula_toolset, excel_formatting_toolset

- [ ] Create "LTV by Plan" tab with LTV breakdown by plan types (Basic, Pro, Enterprise)
**Toolsets**: excel_structure_toolset, excel_formula_toolset, excel_formatting_toolset

- [ ] Create "LTV by Industry" tab with LTV breakdown by customer industry segments
**Toolsets**: excel_structure_toolset, excel_formula_toolset, excel_formatting_toolset

- [ ] Create "LTV by Channel" tab with LTV breakdown by acquisition channels
**Toolsets**: excel_structure_toolset, excel_formula_toolset, excel_formatting_toolset

- [ ] Calculate CAC by channel using marketing spend data (Total Spend / New Customers Acquired in 2023)
**Toolsets**: excel_structure_toolset, excel_formula_toolset

- [ ] Create "CAC to LTV Analysis" tab comparing LTV to CAC ratios by acquisition channel
**Toolsets**: excel_structure_toolset, excel_formula_toolset, excel_formatting_toolset

- [ ] Apply professional formatting and conditional formatting to all tabs for better readability
**Toolsets**: excel_formatting_toolset

- [ ] Add summary dashboard or key metrics overview if beneficial
**Toolsets**: excel_structure_toolset, excel_formula_toolset, excel_formatting_toolset, excel_charts_toolset