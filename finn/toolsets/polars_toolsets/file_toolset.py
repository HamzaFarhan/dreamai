from pathlib import Path
from typing import Any

import polars as pl
from loguru import logger
from pydantic_ai import ModelRetry, RunContext

from ...finn_deps import FinnDeps


async def _list_files(
    dir: Path,
    suffixes: str | list[str] = [".csv", ".parquet", ".xlsx", ".xls", ".xlsb"],
    exclude_in: list[str] | None = None,
) -> str:
    """
    Lists all available in the `dir`.
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
    Lists all available files in the `data_dir`.
    """
    return await _list_files(dir=Path(ctx.deps.dirs.data_dir))


async def list_result_files(ctx: RunContext[FinnDeps]) -> str:
    """
    Lists all the result files created so far in the `results_dir`.
    All excel files should be created in the `results_dir`.
    """
    return await _list_files(dir=Path(ctx.deps.dirs.results_dir))


def resolve_file_path(
    ctx: RunContext[FinnDeps],
    file_path: str | Path,
    suffixes: list[str] = [".xlsx", ".parquet", ".csv", ".xls", ".xlsb"],
) -> Path:
    if isinstance(file_path, str):
        file_path = Path(file_path)
    paths_to_try: list[Path] = []
    if file_path.suffix and file_path.suffix.lower() not in suffixes:
        suffixes.insert(0, file_path.suffix.lower())
    for suffix in suffixes:
        paths_to_try += [
            ctx.deps.dirs.results_dir / file_path.name,
            (ctx.deps.dirs.results_dir / file_path.stem).with_suffix(suffix),
            ctx.deps.dirs.data_dir / file_path.name,
            (ctx.deps.dirs.data_dir / file_path.stem).with_suffix(suffix),
        ]
    for path in paths_to_try:
        if path.exists():
            return path
    return (ctx.deps.dirs.results_dir / file_path.name).with_suffix(
        file_path.suffix if file_path.suffix else ".xlsx"
    )


def load_file(ctx: RunContext[FinnDeps], data: pl.DataFrame | str | Path) -> pl.DataFrame:
    if isinstance(data, pl.DataFrame):
        return data
    file_apth = resolve_file_path(ctx, data)
    suffix = file_apth.suffix.lower()
    if suffix == ".parquet":
        return pl.read_parquet(file_apth)
    elif suffix in [".xlsx", ".xls", ".xlsb"]:
        return pl.read_excel(file_apth)
    else:
        return pl.read_csv(file_apth)


def describe_file(ctx: RunContext[FinnDeps], file_path: str) -> dict[str, Any]:
    """
    Get the shape, schema, and description of a csv, excel, or parquet file at the given path.
    """
    try:
        df = load_file(ctx, file_path)
        res: dict[str, Any] = {"shape": {"rows": df.height, "columns": df.width}, "schema": str(df.schema)}
        try:
            res["description"] = df.describe().to_dicts()
        except Exception as e:
            logger.error(f"Error describing DataFrame: {e}")
        return res
    except Exception as e:
        raise ModelRetry(f"Error in describe_file: {e}")
