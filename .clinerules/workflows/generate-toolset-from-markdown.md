<explicit_instructions type="generate-toolset-from-markdown.md">
<task name="Generate Toolset from Markdown">

<task_objective>
Generate a complete Python toolset implementation from a markdown specification file. Takes a toolset_mds/*_toolset.md file as input and creates a corresponding *_toolset.py file with all functions implemented using polars, following the established pattern from arithmetic_toolset.py and lookup_and_reference_toolset.py.
</task_objective>

<detailed_sequence_steps>
# Generate Toolset from Markdown - Detailed Sequence of Steps

## 1. Parse Markdown Toolset Specification

1. Use the `read_file` tool to read the provided toolset_mds/*_toolset.md file.

2. Parse the markdown content to extract:
   - Tool category name and description
   - Individual function specifications including:
     - Function name
     - Purpose/description
     - Input parameters and types
     - Output type and description
     - Example usage

3. Create a structured list of all functions that need to be implemented.

## 2. Get Polars Documentation

1. Use the `use_mcp_tool` with context7 to resolve the polars library ID:
   ```
   server_name: github.com/upstash/context7-mcp
   tool_name: resolve-library-id
   arguments: {"libraryName": "polars"}
   ```

2. Use the `use_mcp_tool` with context7 to get relevant polars documentation:
   ```
   server_name: github.com/upstash/context7-mcp
   tool_name: get-library-docs
   arguments: {
     "context7CompatibleLibraryID": "[polars library ID from step 1]",
     "topic": "dataframe operations aggregations expressions",
     "tokens": 15000
   }
   ```

## 3. Analyze Existing Pattern

1. Use the `read_file` tool to read `arithmetic_toolset.py` to understand the existing implementation pattern.

2. Use the `read_file` tool to read `lookup_and_reference_toolset.py` for lookup function patterns.

3. Use the `read_file` tool to read `file_toolset.py` to understand the `load_df` and `save_df_to_analysis_dir` utility functions.

4. Identify the consistent patterns:
   - Import structure with Decimal and precision setting
   - Function signature pattern with `RunContext[FinnDeps]`
   - Data parameter handling (file_path: str only, not DataFrame | str)
   - Error handling with `ModelRetry`
   - Documentation format
   - Return type handling with Decimal for numeric precision

## 4. Generate Function Implementations

1. For each function identified in step 1, generate a complete implementation following the pattern:
   - **Parameter Types**: Use `file_path: str` for data input (never `data: pl.DataFrame | str`)
   - **Data Loading**: Always use `load_df(ctx, file_path)` to load DataFrame from file
   - **Numeric Precision**: Use `Decimal` for all numeric results and calculations where precision matters
   - **Return Types**: 
     - For scalar numeric results: `Decimal` (not `int` or `float`)
     - For string results: `str`
     - For array/list results where numeric: `list[Decimal]` or `list[Any]`
     - For file-based results: `str` (file path)
   - **Error Handling**: Include proper error handling with `ModelRetry`
   - **Docstrings**: Add comprehensive docstrings with examples (do not include ctx in examples)
   - **Imports**: Include `from decimal import Decimal, getcontext` and set `getcontext().prec = 28`

2. After implementing every 5 functions, use the `smol` tool to compress the task context window.

3. Handle different function categories:
   - **Scalar operations** (sum, average, min, max, etc.): Return `Decimal` directly
   - **Mathematical operations** (power, sqrt, log, etc.): Save to file using `save_df_to_analysis_dir` and return file path
   - **Statistical operations** (median, mode, percentile, etc.): Return `Decimal` or `list[Decimal]`
   - **Array operations** (cumsum, cumprod, etc.): Save to file and return file path
   - **Lookup operations**: Use appropriate return types (`str | Decimal | None`, etc.)

4. Handle large artifacts efficiently:
   - For functions that create artifacts that may be as large as the original DataFrame, do not return the artifacts directly (inefficient)
   - Instead, add an `analysis_result_file_name: str` parameter to the function signature
   - Create a new DataFrame with the results and save it using `save_df_to_analysis_dir` from `file_toolset.py`
   - Return the file path (`str`) instead of the raw data
   - Examples: transformations, calculations that return arrays/series, cumulative operations, etc.

5. Distinguish between scalar and array-returning functions:
   - **Scalar functions** (sum, average, min, max, etc.): Return the computed value directly (`Decimal`)
   - **Array/DataFrame functions** (power, sqrt, cumsum, transformations, etc.): Save to file and return file path (`str`)

6. **Decimal Usage Patterns**:
   - Convert polars results to Decimal: `Decimal(str(result))`
   - For lists: `[Decimal(str(x)) for x in values if x is not None]`
   - Use Decimal for intermediate calculations when precision matters
   - Set precision with `getcontext().prec = 28` at module level

7. **Return Type Consistency**:
   - Remove `int` and `float` from return type annotations when all numeric results are converted to `Decimal`
   - Use `str | Decimal | None` instead of `str | int | float | Decimal | None`
   - For mixed types: `str | Decimal | list[Any] | None` etc.

## 5. Create Complete Python Toolset File

1. Use the `write_to_file` tool to create `{toolset_name}_toolset.py` with:
   - **Required imports**:
     ```python
     from decimal import Decimal, getcontext
     import polars as pl
     from pydantic_ai import ModelRetry, RunContext
     from ..finn_deps import FinnDeps
     from .file_toolset import load_df, save_df_to_analysis_dir
     
     getcontext().prec = 28
     ```
   - All function implementations following the established patterns
   - Consistent formatting and style

2. Ensure the file follows the exact same structure as `arithmetic_toolset.py` and `lookup_and_reference_toolset.py`.

## 6. Validate Implementation

1. Use the `read_file` tool to review the generated toolset file for:
   - Consistent parameter naming (`file_path: str` not `data`)
   - Proper Decimal usage for numeric results
   - Correct return type annotations (no `int`/`float` when converted to `Decimal`)
   - Proper error handling with `ModelRetry`
   - Complete docstrings without ctx references
   - Correct function signatures with `RunContext[FinnDeps]`

2. Ensure all functions from the markdown specification have been implemented.

3. Verify that precision-sensitive operations use Decimal throughout the calculation chain.

</detailed_sequence_steps>

</task>
</explicit_instructions>
