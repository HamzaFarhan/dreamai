# Google Sheets Functions Supported by OpenPyXL

**Note**: This table shows Google Sheets functions that can be implemented using openpyxl. OpenPyXL can write formulas to Excel files, but cannot execute them - Excel will evaluate the formulas when the file is opened.

| Type  | Name    | Syntax | Description | OpenPyXL Support |
|-------|---------|--------|-------------|------------------|
| Date | `DATE` | `DATE(year, month, day)` | Converts a provided year, month, and day into a date. | ✅ Native Excel function |
| Date | `DAY` | `DAY(date)` | Returns the day of the month that a specific date falls on, in numeric format. | ✅ Native Excel function |
| Date | `HOUR` | `HOUR(time)` | Returns the hour component of a specific time, in numeric format. | ✅ Native Excel function |
| Date | `MINUTE` | `MINUTE(time)` | Returns the minute component of a specific time, in numeric format. | ✅ Native Excel function |
| Date | `MONTH` | `MONTH(date)` | Returns the month of the year a specific date falls in, in numeric format. | ✅ Native Excel function |
| Date | `NOW` | `NOW()` | Returns the current date and time as a date value. | ✅ Native Excel function |
| Date | `SECOND` | `SECOND(time)` | Returns the second component of a specific time, in numeric format. | ✅ Native Excel function |
| Date | `TIME` | `TIME(hour, minute, second)` | Converts a provided hour, minute, and second into a time. | ✅ Native Excel function |
| Date | `TODAY` | `TODAY()` | Returns the current date as a date value. | ✅ Native Excel function |
| Date | `WEEKDAY` | `WEEKDAY(date, [type])` | Returns a number representing the day of the week of the date provided. | ✅ Native Excel function |
| Date | `YEAR` | `YEAR(date)` | Returns the year specified by a given date. | ✅ Native Excel function |
| Financial | `FV` | `FV(rate, number_of_periods, payment_amount, [present_value], [end_or_beginning])` | Calculates the future value of an annuity investment. | ✅ Native Excel function |
| Financial | `IRR` | `IRR(cashflow_amounts, [rate_guess])` | Calculates the internal rate of return on an investment. | ✅ Native Excel function |
| Financial | `NPV` | `NPV(discount, cashflow1, [cashflow2, ...])` | Calculates the net present value of an investment. | ✅ Native Excel function |
| Financial | `PMT` | `PMT(rate, number_of_periods, present_value, [future_value], [end_or_beginning])` | Calculates the periodic payment for an annuity investment. | ✅ Native Excel function |
| Financial | `PV` | `PV(rate, number_of_periods, payment_amount, [future_value], [end_or_beginning])` | Calculates the present value of an annuity investment. | ✅ Native Excel function |
| Info | `ISBLANK` | `ISBLANK(value)` | Checks whether the referenced cell is empty. | ✅ Native Excel function |
| Info | `ISERROR` | `ISERROR(value)` | Checks whether a value is an error. | ✅ Native Excel function |
| Info | `ISNUMBER` | `ISNUMBER(value)` | Checks whether a value is a number. | ✅ Native Excel function |
| Info | `ISTEXT` | `ISTEXT(value)` | Checks whether a value is text. | ✅ Native Excel function |
| Logical | `AND` | `AND(logical_expression1, [logical_expression2, ...])` | Returns true if all arguments are logically true. | ✅ Native Excel function |
| Logical | `FALSE` | `FALSE()` | Returns the logical value `FALSE`. | ✅ Native Excel function |
| Logical | `IF` | `IF(logical_expression, value_if_true, value_if_false)` | Returns one value if TRUE and another if FALSE. | ✅ Native Excel function |
| Logical | `IFERROR` | `IFERROR(value, [value_if_error])` | Returns first argument if not error, otherwise second argument. | ✅ Native Excel function |
| Logical | `NOT` | `NOT(logical_expression)` | Returns the opposite of a logical value. | ✅ Native Excel function |
| Logical | `OR` | `OR(logical_expression1, [logical_expression2, ...])` | Returns true if any arguments are logically true. | ✅ Native Excel function |
| Logical | `TRUE` | `TRUE()` | Returns the logical value `TRUE`. | ✅ Native Excel function |
| Lookup | `CHOOSE` | `CHOOSE(index, choice1, [choice2, ...])` | Returns an element from a list based on index. | ✅ Native Excel function |
| Lookup | `COLUMN` | `COLUMN([cell_reference])` | Returns the column number of a specified cell. | ✅ Native Excel function |
| Lookup | `COLUMNS` | `COLUMNS(range)` | Returns the number of columns in a range. | ✅ Native Excel function |
| Lookup | `HLOOKUP` | `HLOOKUP(search_key, range, index, [is_sorted])` | Horizontal lookup function. | ✅ Native Excel function |
| Lookup | `INDEX` | `INDEX(reference, [row], [column])` | Returns content of a cell by row and column offset. | ✅ Native Excel function |
| Lookup | `INDIRECT` | `INDIRECT(cell_reference_as_string, [is_A1_notation])` | Returns a cell reference specified by string. | ✅ Native Excel function |
| Lookup | `MATCH` | `MATCH(search_key, range, [search_type])` | Returns relative position of an item in a range. | ✅ Native Excel function |
| Lookup | `OFFSET` | `OFFSET(cell_reference, offset_rows, offset_columns, [height], [width])` | Returns a range reference shifted by specified rows/columns. | ✅ Native Excel function |
| Lookup | `ROW` | `ROW([cell_reference])` | Returns the row number of a specified cell. | ✅ Native Excel function |
| Lookup | `ROWS` | `ROWS(range)` | Returns the number of rows in a range. | ✅ Native Excel function |
| Lookup | `VLOOKUP` | `VLOOKUP(search_key, range, index, [is_sorted])` | Vertical lookup function. | ✅ Native Excel function |
| Math | `ABS` | `ABS(value)` | Returns the absolute value of a number. | ✅ Native Excel function |
| Math | `ACOS` | `ACOS(value)` | Returns the inverse cosine of a value, in radians. | ✅ Native Excel function |
| Math | `ASIN` | `ASIN(value)` | Returns the inverse sine of a value, in radians. | ✅ Native Excel function |
| Math | `ATAN` | `ATAN(value)` | Returns the inverse tangent of a value, in radians. | ✅ Native Excel function |
| Math | `ATAN2` | `ATAN2(x, y)` | Returns the angle between x-axis and line segment. | ✅ Native Excel function |
| Math | `CEILING` | `CEILING(value, [factor])` | Rounds a number up to nearest integer multiple. | ✅ Native Excel function |
| Math | `COMBIN` | `COMBIN(n, k)` | Returns number of ways to choose objects from a pool. | ✅ Native Excel function |
| Math | `COS` | `COS(angle)` | Returns the cosine of an angle in radians. | ✅ Native Excel function |
| Math | `COUNTIF` | `COUNTIF(range, criterion)` | Returns a conditional count across a range. | ✅ Native Excel function |
| Math | `COUNTIFS` | `COUNTIFS(criteria_range1, criterion1, [...])` | Returns count based on multiple criteria. | ✅ Native Excel function |
| Math | `DEGREES` | `DEGREES(angle)` | Converts angle from radians to degrees. | ✅ Native Excel function |
| Math | `EVEN` | `EVEN(value)` | Rounds a number up to nearest even integer. | ✅ Native Excel function |
| Math | `EXP` | `EXP(exponent)` | Returns e raised to a power. | ✅ Native Excel function |
| Math | `FACT` | `FACT(value)` | Returns the factorial of a number. | ✅ Native Excel function |
| Math | `FLOOR` | `FLOOR(value, [factor])` | Rounds a number down to nearest integer multiple. | ✅ Native Excel function |
| Math | `INT` | `INT(value)` | Rounds a number down to nearest integer. | ✅ Native Excel function |
| Math | `LN` | `LN(value)` | Returns natural logarithm of a number. | ✅ Native Excel function |
| Math | `LOG` | `LOG(value, base)` | Returns logarithm of a number given a base. | ✅ Native Excel function |
| Math | `LOG10` | `LOG10(value)` | Returns base-10 logarithm of a number. | ✅ Native Excel function |
| Math | `MAX` | `MAX(value1, [value2, ...])` | Returns maximum value in a dataset. | ✅ Native Excel function |
| Math | `MIN` | `MIN(value1, [value2, ...])` | Returns minimum value in a dataset. | ✅ Native Excel function |
| Math | `MOD` | `MOD(dividend, divisor)` | Returns remainder after division. | ✅ Native Excel function |
| Math | `ODD` | `ODD(value)` | Rounds a number up to nearest odd integer. | ✅ Native Excel function |
| Math | `PI` | `PI()` | Returns the value of Pi. | ✅ Native Excel function |
| Math | `POWER` | `POWER(base, exponent)` | Returns a number raised to a power. | ✅ Native Excel function |
| Math | `PRODUCT` | `PRODUCT(factor1, [factor2, ...])` | Returns product of multiplying numbers together. | ✅ Native Excel function |
| Math | `RADIANS` | `RADIANS(angle)` | Converts angle from degrees to radians. | ✅ Native Excel function |
| Math | `RAND` | `RAND()` | Returns random number between 0 and 1. | ✅ Native Excel function |
| Math | `RANDBETWEEN` | `RANDBETWEEN(low, high)` | Returns random integer between two values. | ✅ Native Excel function |
| Math | `ROUND` | `ROUND(value, [places])` | Rounds a number to specified decimal places. | ✅ Native Excel function |
| Math | `ROUNDDOWN` | `ROUNDDOWN(value, [places])` | Rounds a number down to specified decimal places. | ✅ Native Excel function |
| Math | `ROUNDUP` | `ROUNDUP(value, [places])` | Rounds a number up to specified decimal places. | ✅ Native Excel function |
| Math | `SIGN` | `SIGN(value)` | Returns -1, 0, or 1 based on number's sign. | ✅ Native Excel function |
| Math | `SIN` | `SIN(angle)` | Returns sine of an angle in radians. | ✅ Native Excel function |
| Math | `SQRT` | `SQRT(value)` | Returns positive square root of a number. | ✅ Native Excel function |
| Math | `SUM` | `SUM(value1, [value2, ...])` | Returns sum of numbers and/or cells. | ✅ Native Excel function |
| Math | `SUMIF` | `SUMIF(range, criterion, [sum_range])` | Returns conditional sum across a range. | ✅ Native Excel function |
| Math | `SUMIFS` | `SUMIFS(sum_range, criteria_range1, criterion1, [...])` | Returns sum based on multiple criteria. | ✅ Native Excel function |
| Math | `SUMPRODUCT` | `SUMPRODUCT(array1, [array2, ...])` | Calculates sum of products of corresponding entries. | ✅ Native Excel function |
| Math | `TAN` | `TAN(angle)` | Returns tangent of an angle in radians. | ✅ Native Excel function |
| Math | `TRUNC` | `TRUNC(value, [places])` | Truncates a number to specified significant digits. | ✅ Native Excel function |
| Statistical | `AVERAGE` | `AVERAGE(value1, [value2, ...])` | Returns numerical average of a dataset. | ✅ Native Excel function |
| Statistical | `AVERAGEIF` | `AVERAGEIF(criteria_range, criterion, [average_range])` | Returns average based on criteria. | ✅ Native Excel function |
| Statistical | `AVERAGEIFS` | `AVERAGEIFS(average_range, criteria_range1, criterion1, [...])` | Returns average based on multiple criteria. | ✅ Native Excel function |
| Statistical | `COUNT` | `COUNT(value1, [value2, ...])` | Returns count of numeric values in dataset. | ✅ Native Excel function |
| Statistical | `COUNTA` | `COUNTA(value1, [value2, ...])` | Returns count of non-empty values in dataset. | ✅ Native Excel function |
| Statistical | `COUNTBLANK` | `COUNTBLANK(range)` | Returns number of empty cells in range. | ✅ Native Excel function |
| Statistical | `LARGE` | `LARGE(data, n)` | Returns nth largest element from dataset. | ✅ Native Excel function |
| Statistical | `MEDIAN` | `MEDIAN(value1, [value2, ...])` | Returns median value in dataset. | ✅ Native Excel function |
| Statistical | `MODE` | `MODE(value1, [value2, ...])` | Returns most common value in dataset. | ✅ Native Excel function |
| Statistical | `PERCENTILE` | `PERCENTILE(data, percentile)` | Returns value at given percentile. | ✅ Native Excel function |
| Statistical | `QUARTILE` | `QUARTILE(data, quartile_number)` | Returns value nearest to specified quartile. | ✅ Native Excel function |
| Statistical | `RANK` | `RANK(value, data, [is_ascending])` | Returns rank of value in dataset. | ✅ Native Excel function |
| Statistical | `SMALL` | `SMALL(data, n)` | Returns nth smallest element from dataset. | ✅ Native Excel function |
| Statistical | `STDEV` | `STDEV(value1, [value2, ...])` | Calculates standard deviation based on sample. | ✅ Native Excel function |
| Statistical | `VAR` | `VAR(value1, [value2, ...])` | Calculates variance based on sample. | ✅ Native Excel function |
| Text | `CHAR` | `CHAR(table_number)` | Convert number to character. | ✅ Native Excel function |
| Text | `CLEAN` | `CLEAN(text)` | Removes non-printable characters. | ✅ Native Excel function |
| Text | `CODE` | `CODE(string)` | Returns Unicode value of first character. | ✅ Native Excel function |
| Text | `CONCATENATE` | `CONCATENATE(string1, [string2, ...])` | Appends strings together. | ✅ Native Excel function |
| Text | `EXACT` | `EXACT(string1, string2)` | Tests if two strings are identical. | ✅ Native Excel function |
| Text | `FIND` | `FIND(search_for, text_to_search, [starting_at])` | Returns position where string is found. | ✅ Native Excel function |
| Text | `LEFT` | `LEFT(string, [number_of_characters])` | Returns substring from beginning. | ✅ Native Excel function |
| Text | `LEN` | `LEN(text)` | Returns length of string. | ✅ Native Excel function |
| Text | `LOWER` | `LOWER(text)` | Converts string to lowercase. | ✅ Native Excel function |
| Text | `MID` | `MID(string, starting_at, extract_length)` | Returns segment of string. | ✅ Native Excel function |
| Text | `PROPER` | `PROPER(text_to_capitalize)` | Capitalizes each word. | ✅ Native Excel function |
| Text | `REPLACE` | `REPLACE(text, position, length, new_text)` | Replaces part of text string. | ✅ Native Excel function |
| Text | `REPT` | `REPT(text_to_repeat, number_of_repetitions)` | Repeats text specified number of times. | ✅ Native Excel function |
| Text | `RIGHT` | `RIGHT(string, [number_of_characters])` | Returns substring from end. | ✅ Native Excel function |
| Text | `SEARCH` | `SEARCH(search_for, text_to_search, [starting_at])` | Returns position where string is found (case-insensitive). | ✅ Native Excel function |
| Text | `SUBSTITUTE` | `SUBSTITUTE(text_to_search, search_for, replace_with, [occurrence_number])` | Replaces existing text with new text. | ✅ Native Excel function |
| Text | `TEXT` | `TEXT(number, format)` | Converts number to text with specified format. | ✅ Native Excel function |
| Text | `TRIM` | `TRIM(text)` | Removes leading and trailing spaces. | ✅ Native Excel function |
| Text | `UPPER` | `UPPER(text)` | Converts string to uppercase. | ✅ Native Excel function |
| Text | `VALUE` | `VALUE(text)` | Converts text to number. | ✅ Native Excel function |

## Functions NOT Supported by OpenPyXL

The following Google Sheets functions are **NOT** available in Excel and therefore cannot be used with OpenPyXL:

- **Array Functions**: `ARRAY_CONSTRAIN`, `BYCOL`, `BYROW`, `CHOOSECOLS`, `CHOOSEROWS`, `FLATTEN`, `HSTACK`, `VSTACK`, `MAKEARRAY`, `MAP`, `REDUCE`, `SCAN`, `TOCOL`, `TOROW`, `WRAPCOLS`, `WRAPROWS`
- **Filter Functions**: `FILTER`, `SORT`, `SORTN`, `UNIQUE`
- **Google-specific Functions**: `ARRAYFORMULA`, `DETECTLANGUAGE`, `IMAGE`, `SPARKLINE`
- **Web Functions**: `IMPORTDATA`, `IMPORTFEED`, `IMPORTHTML`, `IMPORTRANGE`, `IMPORTXML`
- **Advanced Logical**: `LAMBDA`, `LET`, `IFS`, `SWITCH`
- **Advanced Lookup**: `XLOOKUP` (available in newer Excel versions only)
- **Advanced Date**: `EPOCHTODATE`, `DATEDIF`
- **Google-specific Text**: `REGEXEXTRACT`, `REGEXMATCH`, `REGEXREPLACE`, `SPLIT`, `JOIN`, `TEXTJOIN`
- **Parser Functions**: `CONVERT`, `TO_DATE`, `TO_DOLLARS`, `TO_PERCENT`, `TO_PURE_NUMBER`, `TO_TEXT`
- **Math Functions**: `COUNTUNIQUE`, `SEQUENCE`, `RANDARRAY`, `MUNIT`

## Usage with OpenPyXL

To use these functions with OpenPyXL:

```python
import openpyxl

# Create workbook and worksheet
wb = openpyxl.Workbook()
ws = wb.active

# Write formulas (Excel will evaluate them when file is opened)
ws['A1'] = '=SUM(B1:B10)'
ws['A2'] = '=AVERAGE(B1:B10)'
ws['A3'] = '=IF(B1>0,"Positive","Not Positive")'
ws['A4'] = '=VLOOKUP(D1,F:G,2,FALSE)'

# Save the file
wb.save('example.xlsx')
```

The formulas will be evaluated by Excel when the file is opened, not by OpenPyXL itself.

## Advanced Data Analysis Features in OpenPyXL

### Pivot Tables (Excel's GroupBy Equivalent)
OpenPyXL provides comprehensive pivot table support for data aggregation:

**Supported Aggregation Types:**
- SUM, COUNT, AVERAGE, MAX, MIN
- PRODUCT, STDEV, STDEVP, VAR, VARP
- Custom subtotals and grand totals

**Pivot Table Capabilities:**
- Multi-level row/column grouping
- Data filtering and conditional formatting
- Hierarchical data organization
- Custom field calculations

**Example:**
```python
from openpyxl.pivot.table import TableDefinition, DataField
from openpyxl.pivot.cache import CacheDefinition

# Create pivot table with SUM aggregation
data_field = DataField(fld=0, subtotal='sum', name='Sales Total')
pivot_table = TableDefinition(name='SalesAnalysis', dataFields=[data_field])
