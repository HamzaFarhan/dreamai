Conditional Aggregation & Counting
These functions allow you to work with data subsets based on specific criteria.

- **SUMIF**
  - Purpose: Sum numbers that meet one condition
  - Input: Range to evaluate, criteria, sum range (optional)
  - Output: Single numeric value
  - Example: =SUMIF(A1:A10, ">100", B1:B10)
- **SUMIFS**
  - Purpose: Sum numbers that meet multiple conditions
  - Input: Sum range, criteria ranges, criteria values
  - Output: Single numeric value
  - Example: =SUMIFS(C1:C10, A1:A10, ">100", B1:B10, "Sales")
- **COUNTIF**
  - Purpose: Count cells that meet one condition
  - Input: Range to evaluate, criteria
  - Output: Integer count
  - Example: =COUNTIF(A1:A10, ">100")
- **COUNTIFS**
  - Purpose: Count cells that meet multiple conditions
  - Input: Criteria ranges and criteria values (pairs)
  - Output: Integer count
  - Example: =COUNTIFS(A1:A10, ">100", B1:B10, "Sales")
- **AVERAGEIF**
  - Purpose: Calculate average of cells that meet one condition
  - Input: Range to evaluate, criteria, average range (optional)
  - Output: Single numeric value
  - Example: =AVERAGEIF(A1:A10, ">100", B1:B10)
- **AVERAGEIFS**
  - Purpose: Calculate average of cells that meet multiple conditions
  - Input: Average range, criteria ranges, criteria values
  - Output: Single numeric value
  - Example: =AVERAGEIFS(C1:C10, A1:A10, ">100", B1:B10, "Sales")
- **MAXIFS**
  - Purpose: Find maximum value based on multiple criteria
  - Input: Max range, criteria ranges, criteria values
  - Output: Single numeric value
  - Example: =MAXIFS(C1:C10, A1:A10, ">100", B1:B10, "Sales")
- **MINIFS**
  - Purpose: Find minimum value based on multiple criteria
  - Input: Min range, criteria ranges, criteria values
  - Output: Single numeric value
  - Example: =MINIFS(C1:C10, A1:A10, ">100", B1:B10, "Sales")

- **SUMPRODUCT**
  - Purpose: Sum the products of corresponding ranges
  - Input: range1, range2, [range3, ...]
  - Output: Single numeric value
  - Example: SUMPRODUCT(A1:A10, B1:B10)

- **AGGREGATE**
  - Purpose: Perform various aggregations with error handling and filtering
  - Input: function_num (int), options (int), array, [k]
  - Output: Single numeric value
  - Example: AGGREGATE(1, 5, A1:A10) # Sum ignoring errors

- **SUBTOTAL**
  - Purpose: Calculate subtotals with filtering capability
  - Input: function_num (int), ref1, [ref2, ...]
  - Output: Single numeric value
  - Example: SUBTOTAL(109, A1:A10) # Sum of visible cells

- **COUNTBLANK**
  - Purpose: Count blank/empty cells in a range
  - Input: Range to evaluate
  - Output: Integer count
  - Example: COUNTBLANK(A1:A10)

- **COUNTA**
  - Purpose: Count non-empty cells in a range
  - Input: Range to evaluate
  - Output: Integer count
  - Example: COUNTA(A1:A10)
