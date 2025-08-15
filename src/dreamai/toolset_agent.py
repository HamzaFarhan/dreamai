from __future__ import annotations

from pathlib import Path
from typing import Any

import logfire
from dotenv import load_dotenv
from pydantic_ai import ModelRetry
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.usage import UsageLimits

from .agent import AgentDeps, create_agent
from .finn_deps import DataDirs, FinnDeps
from .toolsets.arithmetic_toolset import (
    calculate_abs,
    calculate_average,
    calculate_cumprod,
    calculate_cumsum,
    calculate_exp,
    calculate_geometric_mean,
    calculate_harmonic_mean,
    calculate_ln,
    calculate_log,
    calculate_max,
    calculate_median,
    calculate_min,
    calculate_mod,
    calculate_mode,
    calculate_percentile,
    calculate_power,
    calculate_product,
    calculate_round,
    calculate_rounddown,
    calculate_roundup,
    calculate_sign,
    calculate_sqrt,
    calculate_sum,
    calculate_variance_weighted,
    calculate_weighted_average,
)
from .toolsets.conditional_toolset import (
    aggregate,
    averageif,
    averageifs,
    counta,
    countblank,
    countif,
    countifs,
    maxifs,
    minifs,
    subtotal,
    sumif,
    sumifs,
    sumproduct,
)
from .toolsets.date_and_time_toolset import (
    create_date,
    create_time,
    date_range,
    datedif,
    edate,
    eomonth,
    extract_day,
    extract_hour,
    extract_minute,
    extract_month,
    extract_second,
    extract_year,
    networkdays,
    now,
    quarter,
    today,
    weekday,
    workday,
    yearfrac,
)
from .toolsets.file_toolset import describe_df, list_analysis_files, list_data_files
from .toolsets.filtering_and_selection_toolset import (
    bottom_n,
    filter_by_date_range,
    filter_by_multiple_conditions,
    filter_by_value,
    sample_data,
    top_n,
)
from .toolsets.logical_and_errors_toolset import (
    is_blank,
    is_error,
    is_number,
    is_text,
    logical_and,
    logical_and_scalar,
    logical_if,
    logical_iferror,
    logical_ifna,
    logical_ifs,
    logical_not,
    logical_or,
    logical_or_scalar,
    logical_switch,
    logical_xor,
)
from .toolsets.lookup_and_reference_toolset import (
    address_cell,
    choose_value,
    column_number,
    columns_count,
    hlookup,
    index_lookup,
    indirect_reference,
    lookup_vector,
    match_lookup,
    offset_range,
    row_number,
    rows_count,
    vlookup,
    xlookup,
)
from .toolsets.transformation_and_pivoting_toolset import (
    concat_data,
    create_pivot_table,
    cross_tabulation,
    fill_forward,
    group_by,
    group_by_agg,
    interpolate_values,
    merge_data,
    stack_data,
    unpivot_data,
    unstack_data,
)

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


def get_weather(location: str) -> dict[str, Any]:
    """
    Get the current weather for a specific location.

    Args:
        location (str): The location to get the weather for.
    """
    weather_map: dict[str, dict[str, Any]] = {
        "New York": {"temperature": 72, "condition": "Sunny"},
        "Los Angeles": {"temperature": 75, "condition": "Sunny"},
        "Chicago": {"temperature": 68, "condition": "Cloudy"},
    }
    if location not in weather_map:
        raise ModelRetry(
            f"Weather data not found for location: {location}\nPossible locations are: {list(weather_map.keys())}"
        )
    return weather_map[location]


weather_toolset = FunctionToolset([get_weather], id="weather_toolset", max_retries=3)

conditional_toolset = FunctionToolset(
    tools=[
        sumif,
        sumifs,
        countif,
        countifs,
        averageif,
        averageifs,
        maxifs,
        minifs,
        sumproduct,
        aggregate,
        subtotal,
        countblank,
        counta,
    ],
    id="conditional_toolset",
    max_retries=3,
)

date_and_time_toolset = FunctionToolset(
    tools=[
        today,
        now,
        create_date,
        extract_year,
        extract_month,
        extract_day,
        edate,
        eomonth,
        datedif,
        yearfrac,
        weekday,
        quarter,
        create_time,
        extract_hour,
        extract_minute,
        extract_second,
        date_range,
        workday,
        networkdays,
    ],
    id="date_and_time_toolset",
    max_retries=3,
)

logical_and_errors_toolset = FunctionToolset(
    tools=[
        logical_if,
        logical_iferror,
        logical_ifna,
        logical_ifs,
        logical_and,
        logical_or,
        logical_not,
        logical_switch,
        logical_xor,
        is_blank,
        is_number,
        is_text,
        is_error,
        logical_and_scalar,
        logical_or_scalar,
    ],
    id="logical_and_errors_toolset",
    max_retries=3,
)

lookup_and_reference_toolset = FunctionToolset(
    tools=[
        vlookup,
        hlookup,
        index_lookup,
        match_lookup,
        xlookup,
        offset_range,
        indirect_reference,
        choose_value,
        lookup_vector,
        address_cell,
        row_number,
        column_number,
        rows_count,
        columns_count,
    ],
    id="lookup_and_reference_toolset",
    max_retries=3,
)

arithmetic_toolset = FunctionToolset(
    [
        calculate_sum,
        calculate_average,
        calculate_min,
        calculate_max,
        calculate_product,
        calculate_median,
        calculate_mode,
        calculate_percentile,
        calculate_power,
        calculate_sqrt,
        calculate_exp,
        calculate_ln,
        calculate_log,
        calculate_abs,
        calculate_sign,
        calculate_mod,
        calculate_round,
        calculate_roundup,
        calculate_rounddown,
        calculate_weighted_average,
        calculate_geometric_mean,
        calculate_harmonic_mean,
        calculate_cumsum,
        calculate_cumprod,
        calculate_variance_weighted,
    ],
    id="arithmetic_toolset",
    max_retries=3,
)

file_toolset = FunctionToolset[AgentDeps](
    [describe_df, list_data_files, list_analysis_files], id="file_toolset", max_retries=3
)

filtering_and_selection_toolset = FunctionToolset(
    [filter_by_date_range, filter_by_value, filter_by_multiple_conditions, top_n, bottom_n, sample_data],
    id="filtering_and_selection_toolset",
    max_retries=3,
)

transformation_and_pivoting_toolset = FunctionToolset(
    tools=[
        create_pivot_table,
        unpivot_data,
        group_by,
        cross_tabulation,
        group_by_agg,
        stack_data,
        unstack_data,
        merge_data,
        concat_data,
        fill_forward,
        interpolate_values,
    ],
    id="transformation_and_pivoting_toolset",
    max_retries=3,
)

agent = create_agent()


if __name__ == "__main__":
    workspace_dir = Path("/Users/hamza/dev/dreamai/workspaces/session")
    agent_deps = FinnDeps(
        dirs=DataDirs(workspace_dir=workspace_dir, thread_dir=workspace_dir / "threads/1"),
        toolsets={
            "arithmetic_toolset": arithmetic_toolset,
            "conditional_toolset": conditional_toolset,
            "date_and_time_toolset": date_and_time_toolset,
            "logical_and_errors_toolset": logical_and_errors_toolset,
            "lookup_and_reference_toolset": lookup_and_reference_toolset,
            "filtering_and_selection_toolset": filtering_and_selection_toolset,
            "transformation_and_pivoting_toolset": transformation_and_pivoting_toolset,
        },
    )
    while True:
        user_prompt = input("\n> ")
        if user_prompt.lower() in ["exit", "quit", "q"]:
            break
        try:
            user_prompt = Path(user_prompt.strip()).read_text()
        except Exception:
            pass
        res = agent.run_sync(
            user_prompt,
            deps=agent_deps,
            usage_limits=UsageLimits(request_limit=200),
            message_history=ModelMessagesTypeAdapter.validate_json(Path("message_history.json").read_bytes())
            if Path("message_history.json").exists()
            else None,
            toolsets=[file_toolset],
        )
        Path("message_history.json").write_bytes(res.all_messages_json())
        print("\n-------------\n", res.output, "\n-------------\n")
