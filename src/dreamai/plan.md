## SEQUENTIAL STEPS FOR CUSTOMER LTV ANALYSIS

### Step 1: Data Preparation and Initial Analysis - COMPLETED ✓
- Load and examine all relevant data files (customers.csv, subscriptions.csv, orders.csv, marketing_spend.csv)
- Filter data to focus on 2023 period (Jan 2023 - Dec 2023)
- Identify customers who were active in Jan 2023
- **Toolsets**: filtering_and_selection_toolset, date_and_time_toolset

### Step 2: Create Customer Base Segmentation
- Identify each customer's initial subscription and plan type (earliest subscription record)
- Map customers to their acquisition channels and industry segments
- Create customer segments by: subscription type (monthly/annual), plan type (basic/pro/enterprise), industry, and channel
- **Toolsets**: filtering_and_selection_toolset, lookup_and_reference_toolset

### Step 3: Calculate Revenue and Profit Metrics
- Calculate total profit per customer for Jan 2023 - Dec 2023 period
- Calculate average revenue per user (ARPU) by each segment
- Filter to only include profit from customers who ordered during 2023
- **Toolsets**: arithmetic_toolset, conditional_toolset

### Step 4: Calculate Churn Rates
- Identify customers active at beginning of Jan 2023
- Identify customers who churned during 2023 (were active in Jan 2023 and churned during the year)
- Calculate churn rates by segment using formula: (# churned customers / # customers at beginning)
- Apply 5-year assumption (20% annual churn rate) for segments with 0% churn
- **Toolsets**: conditional_toolset, arithmetic_toolset, logical_and_errors_toolset

### Step 5: Calculate LTV by Segments
- Apply LTV formula: (Average Revenue per User / Churn Rate) × Profit Margin
- Calculate for each segment: total, by plan type, by industry, by acquisition channel
- Handle edge cases where churn rate is 0%
- **Toolsets**: arithmetic_toolset, conditional_toolset

### Step 6: Calculate CAC by Channel
- Sum total marketing spend by channel for 2023
- Count customers acquired by each channel in 2023
- Calculate CAC = Total Spend / Number of Customers Acquired
- **Toolsets**: arithmetic_toolset, conditional_toolset

### Step 7: Create LTV Analysis Tables
- Generate four separate markdown tables:
  1. Total Customer LTV by subscription type
  2. Customer LTV by plan type
  3. Customer LTV by industry
  4. Customer LTV by acquisition channel
- **Toolsets**: No specific toolsets needed (manual formatting)

### Step 8: Create CAC to LTV Analysis
- Create comparative analysis table showing LTV vs CAC by acquisition channel
- Calculate LTV/CAC ratios for each channel
- **Toolsets**: arithmetic_toolset