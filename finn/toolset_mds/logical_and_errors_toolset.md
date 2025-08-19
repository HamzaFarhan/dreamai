Logical & Error-Handling Functions
These functions help structure decision-making processes and manage errors gracefully.

- **IF**
  - Purpose: Return different values depending on whether a condition is met
  - Input: logical_test, value_if_true, value_if_false
  - Output: Value based on condition result
  - Example: =IF(A1 > 100, "Above Budget", "Within Budget")
- **IFERROR**
  - Purpose: Return a specified value if a formula results in an error
  - Input: value, value_if_error
  - Output: Original value or error replacement
  - Example: =IFERROR(formula, alternative_value)
- **IFNA**
  - Purpose: Return a specified value if a formula results in #N/A error
  - Input: value, value_if_na
  - Output: Original value or #N/A replacement
  - Example: =IFNA(formula, alternative_value)
- **IFS**
  - Purpose: Test multiple conditions without nesting several IF statements
  - Input: logical_test1, value_if_true1, logical_test2, value_if_true2, ...
  - Output: Value from first true condition
  - Example: =IFS(A1>100, "High", A1>50, "Medium", TRUE, "Low")
- **AND**
  - Purpose: Test if all conditions are true
  - Input: logical1, logical2, ...
  - Output: TRUE if all conditions are true, FALSE otherwise
  - Example: =AND(condition1, condition2)
- **OR**
  - Purpose: Test if any condition is true
  - Input: logical1, logical2, ...
  - Output: TRUE if any condition is true, FALSE otherwise
  - Example: =OR(condition1, condition2)
- **NOT**
  - Purpose: Reverse the logical value of a condition
  - Input: logical
  - Output: Opposite boolean value
  - Example: =NOT(condition)

- **SWITCH**
  - Purpose: Compare expression against list of values and return corresponding result
  - Input: expression, value1, result1, [value2, result2], ..., [default]
  - Output: Matched result or default
  - Example: SWITCH(A1, 1, "One", 2, "Two", "Other")

- **XOR**
  - Purpose: Exclusive OR - returns TRUE if odd number of arguments are TRUE
  - Input: logical1, logical2, ...
  - Output: Boolean
  - Example: XOR(TRUE, FALSE, TRUE)

- **ISBLANK**
  - Purpose: Test if cell is blank
  - Input: value
  - Output: Boolean
  - Example: ISBLANK(A1)

- **ISNUMBER**
  - Purpose: Test if value is a number
  - Input: value
  - Output: Boolean
  - Example: ISNUMBER(A1)

- **ISTEXT**
  - Purpose: Test if value is text
  - Input: value
  - Output: Boolean
  - Example: ISTEXT(A1)

- **ISERROR**
  - Purpose: Test if value is an error
  - Input: value
  - Output: Boolean
  - Example: ISERROR(A1/B1)
