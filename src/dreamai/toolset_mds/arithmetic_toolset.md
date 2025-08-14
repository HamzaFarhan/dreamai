Basic Arithmetic & Aggregation
These functions are the building blocks for financial summaries and aggregations.

- **SUM**
  - Purpose: Add up a range of numbers
  - Input: Array or range of numeric values
  - Output: Single numeric value (sum)
  - Example: =SUM(A1:A10)
- **AVERAGE**
  - Purpose: Calculate the mean of a dataset
  - Input: Array or range of numeric values
  - Output: Single numeric value极 (mean)
  - Example: =AVERAGE(B1:B10)
- **MIN**
  - Purpose: Identify the smallest number in a dataset
  - Input: Array or range of numeric values
  - Output: Single numeric value (minimum)
  - Example: =MIN(C1:C10)
- **MAX**
  - Purpose: Identify the largest number in a dataset
  - Input: Array or range of numeric values
  - Output: Single numeric value (maximum)
  - Example: =MAX(C1:C10)
- **PRODUCT**
  - Purpose: Multiply values together
  - Input: Array or range of numeric values
  - Output: Single numeric value (product)
  - Example: =PRODUCT(D1:D4)
- **MEDIAN**
  - Purpose: Calculate the middle value of a dataset
  - Input: Series/array of numbers
  - Output: Float
  - Example: =MEDIAN(A1:A10)
- **MODE**
  - Purpose: Find the most frequently occurring value
  - Input: Series/array of numbers
  - Output: Float or list of floats
  - Example: =MODE(A1:A10)
- **PERCENTILE/QUANTILE**
  - Purpose: Calculate specific percentiles (e.g., 25th, 75th percentile)
  - Input: Series/array of numbers, percentile value (0-1)
  - Output: Float
  - Example: =PERCENTILE(A1:A10, 0.75)

- **POWER**
  - Purpose: Raise number to a power
  - Input: number, power
  - Output: Float
  - Example: POWER(1.05, 10)

- **SQRT**
  - Purpose: Calculate square root
  - Input: number
  - Output: Float
  - Example: SQRT(25)

- **EXP**
  - Purpose: Calculate e^x
  - Input: number
  - Output: Float
  - Example: EXP(1)

- **LN**
  - Purpose: Calculate natural logarithm
  - Input: number
  - Output: Float
  - Example: LN(2.718)

- **LOG**
  - Purpose: Calculate logarithm with specified base
  - Input: number, [base]
  - Output: Float
  - Example: LOG(100, 10)

- **ABS**
  - Purpose: Calculate absolute value
  - Input: number
  - Output: Float
  - Example: ABS(-10)

- **SIGN**
  - Purpose: Return sign of number (-1, 0, or 1)
  - Input: number
  - Output: Integer
  - Example: SIGN(-15)

- **MOD**
  - Purpose: Calculate remainder after division
  - Input: number, divisor
  - Output: Float
  - Example: MOD(23, 5)

- **ROUND**
  - Purpose: Round number to specified digits
  - Input: number, num_digits
  - Output: Float
  - Example: ROUND(3.14159, 2)

- **ROUNDUP**
  - Purpose: Round number up
  - Input: number, num_digits
  - Output: Float
  - Example: ROUNDUP(3.14159, 2)

- **ROUNDDOWN**
  - Purpose: Round number down
  - Input: number, num_digits
  - Output: Float
  - Example: ROUNDDOWN(3.14159, 2)

- **WEIGHTED_AVERAGE**
  - Purpose: Calculate weighted average of values
  - Input: values (array), weights (array)
  - Output: Float
  - Example: WEIGHTED_AVERAGE([100, 200, 300], [0.2, 0.3, 0.5])

- **GEOMETRIC_MEAN**
  - Purpose: Calculate geometric mean (useful for growth rates)
  - Input: Series/array of positive numbers
  - Output: Float
  - Example: GEOMETRIC_MEAN([1.05, 1.08, 1.12, 1.03])

- **HARMONIC_MEAN**
  - Purpose: Calculate harmonic mean (useful for rates/ratios)
  - Input: Series/array of positive numbers
  - Output: Float
  - Example: HARMONIC_MEAN([2, 4, 8])

- **CUMSUM**
  - Purpose: Calculate cumulative sum
  - Input: Series/array of numbers
  - Output: Array of cumulative sums
  - Example: CUMSUM([10, 20, 30, 40])

- **CUMPROD**
  - Purpose: Calculate cumulative product
  - Input: Series/array of numbers
  - Output: Array of cumulative products
  - Example: CUMPROD([1.极05, 1.08, 1.12])

- **VARIANCE_WEIGHTED**
  - Purpose: Calculate weighted variance
  - Input: values (array), weights (array)
  - Output: Float
  - Example: VARIANCE_WEIGHTED([100, 200, 300], [0.2, 0.3, 0.5])