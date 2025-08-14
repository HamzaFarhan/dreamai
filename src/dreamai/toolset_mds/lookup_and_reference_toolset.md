Lookup & Reference Functions
These are invaluable when you need to retrieve data from a table or array dynamically.

- **VLOOKUP**
  - Purpose: Search for a value in a vertical range
  - Input: lookup_value, table_array, col_index, range_lookup (optional)
  - Output: Single value from specified column
  - Example: =VLOOKUP(lookup_value, table_array, col_index, [range_lookup])
- **HLOOKUP**
  - Purpose: Search for a value in a horizontal range
  - Input: lookup_value, table_array, row_index, range_lookup (optional)
  - Output: Single value from specified row
  - Example: =HLOOKUP(lookup_value, table_array, row_index, [range_lookup])
- **INDEX**
  - Purpose: Return a value at a given position in an array
  - Input: array, row_num, column_num (optional)
  - Output: Single value at specified position
  - Example: =INDEX(return_range, row_num, [column_num])
- **MATCH**
  - Purpose: Find the relative position of an item in an array
  - Input: lookup_value, lookup_array, match_type
  - Output: Integer position
  - Example: =MATCH(lookup_value, lookup_range, 0)
- **XLOOKUP**
  - Purpose: Modern, flexible lookup function replacing VLOOKUP/HLOOKUP
  - Input: lookup_value, lookup_array, return_array, if_not_found (optional)
  - Output: Value from return array or if_not_found value
  - Example: =XLOOKUP(lookup_value, lookup_array, return_array, [if_not_found])
- **OFFSET**
  - Purpose: Create dynamic ranges based on reference point
  - Input: reference, rows, cols, height (optional), width (optional)
  - Output: Range reference
  - Example: =OFFSET(reference, rows, cols, [height], [width])
- **INDIRECT**
  - Purpose: Create references based on text strings
  - Input: ref_text, a1_style (optional)
  - Output: Range reference
  - Example: =INDIRECT(ref_text)
- **CHOOSE**
  - Purpose: Return a value from a list based on index number
  - Input: index_num, value1, value2, ...
  - Output: Selected value
  - Example: =CHOOSE(index_num, value1, value2, …)

- **LOOKUP**
  - Purpose: Simple lookup function (vector or array form)
  - Input: lookup_value, lookup_vector, result_vector
  - Output: Single value
  - Example: LOOKUP(lookup_value, lookup_vector, result_vector)

- **ADDRESS**
  - Purpose: Create cell address as text
  - Input: row_num, column_num, [abs_num], [a1], [极 sheet_text]
  - Output: Text string (cell address)
  - Example: ADDRESS(1, 1, 1, TRUE, "Sheet1")

- **ROW**
  - Purpose: Return row number of reference
  - Input: [reference]
  - Output: Integer or array of integers
  - Example: ROW(A5)

- **COLUMN**
  - Purpose: Return column number of reference
  - Input: [reference]
  - Output: Integer or array of integers
  - Example: COLUMN(B1)

- **ROWS**
  - Purpose: Return number of rows in reference
  - Input: array
  - Output: Integer
  - Example: ROWS(A1:A10)

- **COLUMNS**
  - Purpose: Return number of columns in reference
  - Input: array
  - Output: Integer
  - Example: COLUMNS(A1:E1)
