from pathlib import Path

from lancedb.db import DBConnection as LanceDBConnection

from dreamai.ai import ModelName
from dreamai.dialog import Dialog
from dreamai.dialog_models import TableDescription
from dreamai.lance_utils import add_to_lance_table
from dreamai.md_utils import data_to_md
from dreamai.response_actions import _query_to_response
from dreamai.settings import DialogSettings, RAGAppSettings, RAGSettings

rag_settings = RAGSettings()
rag_app_settings = RAGAppSettings()
dialog_settings = DialogSettings()

MAX_SEARCH_RESULTS = rag_settings.max_search_results
DIALOGS_FOLDER = dialog_settings.dialogs_folder
CHUNK_SIZE = rag_settings.chunk_size
CHUNK_OVERLAP = rag_settings.chunk_overlap
SAMPLE_TEXT_LIMIT = rag_settings.sample_text_limit
TERMINATORS = rag_app_settings.terminators


def get_user_query() -> str:
    query = ""
    while not query:
        query = input(f"({', '.join(TERMINATORS)} to exit) > ").strip()
    return query


def add_data_with_descriptions(
    model: ModelName,
    lance_db: LanceDBConnection,
    data: list[str | Path] | str | Path | None = None,
    search_queries: list[str] | str | None = None,
    max_results: int = MAX_SEARCH_RESULTS,
    table_descriptions: list[TableDescription] | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[TableDescription]:
    assert data or search_queries, "Either data or search_queries must be provided"
    table_descriptions = table_descriptions or []
    table_descriptions_dict = {td.name: td for td in table_descriptions}
    md_data_list = data_to_md(
        data=data,
        search_queries=search_queries,
        max_results=max_results,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    for md_data in md_data_list:
        table_name = md_data.name
        table_description: TableDescription = _query_to_response(
            model=model,
            dialog=Dialog.load(
                path=str(Path(DIALOGS_FOLDER) / "table_description_dialog.json")
            ),
            response_model=TableDescription,
            template_data={
                "database_name": table_name,
                "sample_text": md_data.markdown[:SAMPLE_TEXT_LIMIT],
                "current_databases": [
                    td.model_dump_json(indent=2) for td in table_descriptions_dict.values()
                ],
            },
        )
        table_description = table_descriptions_dict.get(
            table_description.name, table_description
        )
        table_descriptions_dict[table_description.name] = table_description
        add_to_lance_table(db=lance_db, table_name=table_description.name, data=md_data.chunks)

    return list(table_descriptions_dict.values())
