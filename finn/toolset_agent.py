from __future__ import annotations

from pathlib import Path

import logfire
from dotenv import load_dotenv
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.toolsets import FunctionToolset
from pydantic_ai.usage import UsageLimits
from tenacity import retry, stop_after_attempt, wait_random

from dreamai.agent import AgentDeps, AgentToolset, PlanCreated, create_agent

from .finn_deps import DataDirs, FinnDeps
from .toolsets.excel_toolsets.excel_charts_toolset import (
    apply_chart_preset,
    create_chart,
    create_chart_preset,
    create_matplotlib_chart,
    delete_chart,
    get_chart_types,
    list_charts,
    update_chart_data,
)
from .toolsets.excel_toolsets.excel_formatting_toolset import (
    apply_cell_formatting,
    apply_conditional_formatting,
    apply_preset_formatting,
    clear_formatting,
    create_formatting_preset,
    list_formatting_presets,
    load_formatting_preset,
)
from .toolsets.excel_toolsets.excel_formula_toolset import (
    build_countifs_expression,
    build_division_expression,
    write_arithmetic_operation,
    write_comparison_operation,
    write_conditional_formula,
    write_date_function,
    write_financial_function,
    write_info_function,
    write_logical_function,
    write_lookup_function,
    write_math_function,
    write_nested_function,
    write_statistical_function,
    write_text_function,
)
from .toolsets.excel_toolsets.excel_structure_toolset import (
    add_sheet,
    add_subtotals,
    clear_sheet,
    copy_sheet,
    create_autofilter,
    create_data_table,
    create_excel_file,
    create_pivot_table,
    csv_to_excel_sheet,
    csvs_to_excel,
    delete_sheet,
    duplicate_sheet_to_file,
    extract_sheet_to_csv,
    get_cell_value,
    get_sheet_info,
    get_sheet_names,
    get_spreadsheet_metadata,
    merge_excel_files,
    rename_sheet,
    update_sheet_dimensions,
    update_sheet_properties,
    write_values_to_cells,
)
from .toolsets.polars_toolsets.file_toolset import (
    describe_file,
    list_data_files,
    list_result_files,
    resolve_file_path,
)

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


excel_structure_toolset = AgentToolset(
    tools=[
        create_excel_file,
        csv_to_excel_sheet,
        csvs_to_excel,
        add_sheet,
        get_sheet_names,
        delete_sheet,
        rename_sheet,
        copy_sheet,
        update_sheet_properties,
        merge_excel_files,
        extract_sheet_to_csv,
        update_sheet_dimensions,
        get_spreadsheet_metadata,
        duplicate_sheet_to_file,
        get_sheet_info,
        create_pivot_table,
        write_values_to_cells,
        get_cell_value,
        clear_sheet,
        create_autofilter,
        add_subtotals,
        create_data_table,
    ],
    id="excel_structure_toolset",
    max_retries=3,
    file_path_resolver=resolve_file_path,
)


excel_formula_toolset = AgentToolset(
    tools=[
        write_date_function,
        write_financial_function,
        write_logical_function,
        write_lookup_function,
        write_math_function,
        write_statistical_function,
        write_text_function,
        write_info_function,
        write_arithmetic_operation,
        write_comparison_operation,
        write_nested_function,
        write_conditional_formula,
        build_countifs_expression,
        build_division_expression,
    ],
    id="excel_formula_toolset",
    max_retries=3,
    file_path_resolver=resolve_file_path,
)


excel_formatting_toolset = AgentToolset(
    tools=[
        apply_cell_formatting,
        apply_conditional_formatting,
        create_formatting_preset,
        load_formatting_preset,
        list_formatting_presets,
        apply_preset_formatting,
        clear_formatting,
    ],
    id="excel_formatting_toolset",
    max_retries=3,
    file_path_resolver=resolve_file_path,
)


excel_charts_toolset = AgentToolset(
    tools=[
        create_chart,
        create_matplotlib_chart,
        list_charts,
        delete_chart,
        update_chart_data,
        get_chart_types,
        create_chart_preset,
        apply_chart_preset,
    ],
    id="excel_charts_toolset",
    max_retries=3,
    file_path_resolver=resolve_file_path,
)


file_toolset = FunctionToolset[AgentDeps](
    [describe_file, list_data_files, list_result_files], id="file_toolset", max_retries=3
)


@retry(stop=stop_after_attempt(3), wait=wait_random(min=1, max=3))
async def run_agent(user_prompt: str, agent_deps: FinnDeps) -> str | PlanCreated:
    agent = create_agent()
    res = await agent.run(
        user_prompt,
        deps=agent_deps,
        usage_limits=UsageLimits(request_limit=500),
        message_history=ModelMessagesTypeAdapter.validate_json(agent_deps.dirs.message_history_path.read_bytes())
        if agent_deps.dirs.message_history_path.exists()
        else None,
        toolsets=[file_toolset],
    )
    agent_deps.dirs.message_history_path.write_bytes(res.all_messages_json())
    output = res.output
    if isinstance(output, str):
        return output
    if isinstance(output, PlanCreated):
        return output
    return output.message


if __name__ == "__main__":
    import asyncio

    workspace_dir = Path("/Users/hamza/dev/dreamai/workspaces/session")
    thread_id = "1"
    agent_deps = FinnDeps(
        dirs=DataDirs(workspace_dir=workspace_dir, thread_dir=workspace_dir / f"threads/{thread_id}"),
        toolsets={
            "excel_structure_toolset": excel_structure_toolset,
            "excel_formula_toolset": excel_formula_toolset,
            "excel_charts_toolset": excel_charts_toolset,
            "excel_formatting_toolset": excel_formatting_toolset,
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
        res = asyncio.run(run_agent(user_prompt, agent_deps))
        print("\n-------------\n", res, "\n-------------\n")
