Data Transformation & Pivoting

- **PIVOT_TABLE**
  - Purpose: Create pivot tables with aggregations by groups
  - Input: DataFrame path, index columns, value columns, aggregation functions
  - Output: DataFrame path
  - Example: PIVOT_TABLE(sales_df, ['region'], ['revenue'], 'sum')
- **UNPIVOT/MELT**
  - Purpose: Transform wide data to long format
  - Input: DataFrame path, identifier columns, value columns
  - Output: DataFrame path
  - Example: UNPIVOT(df, ['customer_id'], ['Q1', 'Q2', 'Q3', 'Q4'])
- **GROUP_BY**
  - Purpose: Group data and apply aggregation functions
  - Input: DataFrame path, grouping columns, aggregation functions
  - Output: DataFrame path
  - Example: GROUP_BY(sales_df, ['category'], 'sum')
- **CROSS_TAB**
  - Purpose: Create cross-tabulation tables
  - Input: DataFrame path, row variables, column variables, values
  - Output: DataFrame path
  - Example: CROSS_TAB(df, ['region'], ['product'], ['sales'])
- **GROUP_BY_AGG**
  - Purpose: Group a DataFrame by one or more columns and then apply one or more aggregation functions (like sum, mean, count) to specified columns. This is more versatile than a simple GROUP_BY
  - Input: DataFrame path, group_by_cols (list of str), agg_dict (dict, e.g., {'revenue': 'sum', 'users': 'count'})
  - Output: DataFrame path
  - Example: GROUP_BY_AGG(df, ['region'], {'revenue': 'sum', 'customers': 'count'})

- **STACK**
  - Purpose: Stack multiple columns into single column
  - Input: DataFrame path, columns_to_stack
  - Output: DataFrame path
  - Example: STACK(df, ['Q1', 'Q2', 'Q3', 'Q4'])

- **UNSTACK**
  - Purpose: Unstack index level to columns
  - Input: DataFrame path, level_to_unstack
  - Output: DataFrame path
  - Example: UNSTACK(stacked_df, 'quarter')

- **MERGE**
  - Purpose: Merge/join two DataFrames
  - Input: left_df path, right_df path, join_keys, join_type
  - Output: DataFrame path
  - Example: MERGE(sales_df, customer_df, 'customer_id', 'left')

- **CONCAT**
  - Purpose: Concatenate DataFrames
  - Input: list_of_dataframe paths, axis
  - Output: DataFrame path
  - Example: CONCAT([df1, df2, df3], axis=0)

- **FILL_FORWARD**
  - Purpose: Forward fill missing values
  - Input: DataFrame path or list
  - Output: DataFrame path or list with filled values
  - Example: FILL_FORWARD(revenue_series)

- **INTERPOLATE**
  - Purpose: Interpolate missing values
  - Input: DataFrame path or list, method
  - Output: DataFrame path or list with interpolated values
  - Example: INTERPOLATE(data_series, 'linear')