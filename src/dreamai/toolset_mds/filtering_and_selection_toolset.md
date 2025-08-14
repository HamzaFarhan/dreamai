Data Filtering & Selection
Functions for filtering and selecting data subsets.

- **FILTER_BY_DATE_RANGE**
  - Purpose: Filter DataFrame by date range
  - Input: DataFrame, date_column, start_date, end_date
  - Output: Filtered DataFrame
  - Example: FILTER_BY_DATE_RANGE(df, 'transaction_date', '2024-01-01', '2024-12-31')

- **FILTER_BY_VALUE**
  - Purpose: Filter DataFrame by column values
  - Input: DataFrame, column, operator, value
  - Output: Filtered DataFrame
  - Example: FILTER_BY_VALUE(sales_df, 'amount', '>', 1000)

- **FILTER_BY_MULTIPLE_CONDITIONS**
  - Purpose: Filter DataFrame by multiple conditions
  - Input: DataFrame, conditions_dict
  - Output: Filtered DataFrame
  - Example: FILTER_BY_MULTIPLE_CONDITIONS(df, {'region': 'North', 'sales': '>1000'})

- **TOP_N**
  - Purpose: Select top N records by value
  - Input: DataFrame, column, n, ascending
  - Output: DataFrame with top N records
  - Example: TOP_N(customers_df, 'revenue', 10, False)

- **BOTTOM_N**
  - Purpose: Select bottom N records by value
  - Input: DataFrame, column, n
  - Output: DataFrame with bottom N records
  - Example: BOTTOM_N(products_df, 'profit_margin', 5)

- **SAMPLE_DATA**
  - Purpose: Sample random records from DataFrame
  - Input: DataFrame, n_samples, random_state
  - Output: DataFrame with sampled records
  - Example: SAMPLE_DATA(large_dataset_df, 1000, 42)