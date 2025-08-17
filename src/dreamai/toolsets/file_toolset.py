from pathlib import Path
from typing import Any

import polars as pl
from loguru import logger
from pydantic_ai import ModelRetry, RunContext

from ..finn_deps import FinnDeps


async def _list_files(
    dir: Path, suffixes: str | list[str] = [".csv", ".parquet", ".xlsx"], exclude_in: list[str] | None = None
) -> str:
    """
    Lists all available in the `dir` and their summaries.
    """
    dir_name = dir.name
    files = [file.expanduser().resolve() for file in Path(dir).glob("*")]
    res = f"\n<available_{dir_name}_files>\n"
    suffixes = [suffixes] if isinstance(suffixes, str) else suffixes
    exclude_in = exclude_in or []
    for file in files:
        if any(exclude in file.name for exclude in exclude_in) or Path(file.name).suffix not in suffixes:
            continue

        res += file.name + "\n"
    return res.strip() + f"\n</available_{dir_name}_files>\n"


async def list_data_files(ctx: RunContext[FinnDeps]) -> str:
    """
    Lists all available csv files in the `data_dir`.
    """
    return await _list_files(dir=Path(ctx.deps.dirs.data_dir))


async def list_analysis_files(ctx: RunContext[FinnDeps]) -> str:
    """
    Lists all the analysis csv files created so far in the `analysis_dir`.
    """
    return await _list_files(dir=Path(ctx.deps.dirs.analysis_dir))


def resolve_data_path(
    ctx: RunContext[FinnDeps], df_path: str | Path, suffixes: str | list[str] = [".parquet", ".csv", ".xlsx"]
) -> Path:
    if isinstance(df_path, str):
        df_path = Path(df_path)
    paths_to_try: list[Path] = []
    for suffix in suffixes:
        paths_to_try += [
            ctx.deps.dirs.analysis_dir / df_path.name,
            (ctx.deps.dirs.analysis_dir / df_path.stem).with_suffix(suffix),
            ctx.deps.dirs.data_dir / df_path.name,
            (ctx.deps.dirs.data_dir / df_path.stem).with_suffix(suffix),
        ]
    for path in paths_to_try:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"DataFrame file not found in expected locations: {paths_to_try}\n\n{list_analysis_files(ctx)}\n{list_data_files(ctx)}"
    )


def load_df(ctx: RunContext[FinnDeps], data: pl.DataFrame | str | Path) -> pl.DataFrame:
    if isinstance(data, pl.DataFrame):
        return data
    df_path = resolve_data_path(ctx, data)
    return pl.read_parquet(df_path) if df_path.suffix.lower() == ".parquet" else pl.read_csv(df_path)


def load_file(ctx: RunContext[FinnDeps], file_path: str) -> pl.DataFrame:
    df_path = resolve_data_path(ctx, file_path)
    if df_path.parent != ctx.deps.dirs.analysis_dir:
        raise ModelRetry(
            "Can only load files from the analysis dir. Which are made by most tools after computation."
        )
    return pl.read_parquet(df_path) if df_path.suffix.lower() == ".parquet" else pl.read_csv(df_path)


def df_path_to_analysis_df_path(ctx: RunContext[FinnDeps], df_path: str | Path) -> Path:
    df_path = Path(df_path)
    analysis_path = ctx.deps.dirs.analysis_dir / df_path.name
    if analysis_path.suffix.lower() not in [".parquet", ".csv"]:
        analysis_path = (ctx.deps.dirs.analysis_dir / df_path.stem).with_suffix(".parquet")
    return analysis_path


def save_df_to_analysis_dir(ctx: RunContext[FinnDeps], df: pl.DataFrame, analysis_result_file_name: str) -> str:
    output_path = df_path_to_analysis_df_path(ctx, analysis_result_file_name)
    if output_path.suffix.lower() == ".parquet":
        df.write_parquet(output_path)
    else:
        df.write_csv(output_path)
    return str(output_path)


def describe_df(ctx: RunContext[FinnDeps], df_path: str | Path) -> dict[str, Any]:
    """
    Get the shape, schema, and description of the DataFrame at the given path.
    """
    try:
        df = load_df(ctx, df_path)
        res: dict[str, Any] = {"shape": {"rows": df.height, "columns": df.width}, "schema": str(df.schema)}
        try:
            res["description"] = df.describe().to_dicts()
        except Exception as e:
            logger.error(f"Error describing DataFrame: {e}")
        return res
    except Exception as e:
        raise ModelRetry(f"Error in describe df: {e}")


# if __name__ == "__main__":
#     workspace_dir = Path("../../../workspaces/session/")
#     ctx = RunContext(
#         deps=FinnDeps(
#             dirs=DataDirs(
#                 workspace_dir=workspace_dir,
#                 thread_dir=workspace_dir / "threads/1",
#             )
#         )
#     )

#     pprint(describe_df(ctx, "orders.csv"), indent=2, sort_dicts=False)
