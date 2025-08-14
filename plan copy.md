## CUSTOMER LTV ANALYSIS PLAN (Jan 2023 - Dec 2023)

### SEQUENTIAL STEPS

1. **Data Preparation and Filtering**
   - Filter customers who had active subscriptions in Jan 2023
   - Filter orders from Jan 2023 to Dec 2023 
   - Identify initial subscription and plan types for each customer
   - Merge customer, subscription, and order data
   - **Toolsets:** filtering_and_selection_toolset, transformation_and_pivoting_toolset

2. **Revenue and Profit Calculation**
   - Calculate total revenue per user for 2023
   - Calculate total profit per user for 2023
   - Calculate average revenue per user (ARPU) by subscription type, plan type, industry, and channel
   - **Toolsets:** arithmetic_toolset, transformation_and_pivoting_toolset

3. **Churn Rate Analysis**
   - Identify customers active at start of Jan 2023
   - Identify customers who churned during 2023 (were active in Jan 2023 but churned during the year)
   - Calculate churn rates by subscription type, plan type, industry, and channel
   - Apply 5-year assumption for 0% churn scenarios
   - **Toolsets:** filtering_and_selection_toolset, conditional_toolset, arithmetic_toolset

4. **LTV Calculation**
   - Apply LTV formula: (ARPU / Churn Rate) × Profit Margin
   - Calculate LTV for total, by subscription type (monthly/annual), by plan type (basic/pro/enterprise), by industry, and by channel
   - **Toolsets:** arithmetic_toolset, transformation_and_pivoting_toolset

5. **CAC Analysis**
   - Calculate Customer Acquisition Cost (CAC) by channel from marketing spend data
   - Calculate CAC to LTV ratio by acquisition channel
   - **Toolsets:** arithmetic_toolset, transformation_and_pivoting_toolset

6. **Results Compilation**
   - Create four markdown tables:
     - Total Customer LTV by subscription type
     - Customer LTV by plan type
     - Customer LTV by industry
     - Customer LTV by acquisition channel
   - Create CAC to LTV analysis table
   - **Toolsets:** No specific toolset needed for markdown formatting

### KEY ASSUMPTIONS
- Customers with 0% churn rate will be assumed to remain for 5 years (adjustable driver)
- Initial subscription and plan types are used throughout (no changes considered)
- Only profit from Jan 2023 - Dec 2023 from customers who ordered during this period
- Churn rate calculated only for customers active in Jan 2023