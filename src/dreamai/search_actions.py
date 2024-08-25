from pathlib import Path
from typing import cast

from burr.core import State, action
from lancedb.db import DBConnection as LancedbDBConnection
from lancedb.rerankers import Reranker

from dreamai.ai import ModelName
from dreamai.dialog import Dialog
from dreamai.dialog_models import StepBackQuestions, TableDescription
from dreamai.lance_utils import add_to_lance_table
from dreamai.lance_utils import search_lancedb as _search_lancedb
from dreamai.md_utils import data_to_md, search_query_to_md
from dreamai.routing_actions import _query_to_response
from dreamai.settings import DialogSettings, RAGSettings

rag_settings = RAGSettings()
dialog_settings = DialogSettings()

TEXT_FIELD_NAME = rag_settings.text_field_name
MAX_SEARCH_RESULTS = rag_settings.max_search_results
DIALOGS_FOLDER = dialog_settings.dialogs_folder
CHUNK_SIZE = rag_settings.chunk_size
CHUNK_OVERLAP = rag_settings.chunk_overlap
SAMPLE_TEXT_LIMIT = rag_settings.sample_text_limit


def add_data_with_descriptions(
    model: ModelName,
    lance_db: LancedbDBConnection,
    data: list[str | Path] | str | Path | None = None,
    search_query: str = "",
    max_results: int = MAX_SEARCH_RESULTS,
    table_descriptions: list[TableDescription] | None = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[TableDescription]:
    assert data or search_query, "Either data or search_query must be provided"
    table_descriptions = table_descriptions or []
    table_descriptions_dict = {td.name: td for td in table_descriptions}

    md_data_list = data_to_md(
        data=data,
        search_query=search_query,
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


@action(reads=["query"], writes=["search_results"])
def search_web(state: State) -> tuple[dict[str, list[dict]], State]:
    try:
        results = search_query_to_md(
            query=state["query"], max_results=MAX_SEARCH_RESULTS, chunk_size=0
        )
        results = [result.model_dump(exclude={"chunks"}) for result in results]
    except Exception as e:
        print(f"Error in search_web: {e}")
        results = []
    return {"search_results": results}, state.update(search_results=results)


@action(reads=["model", "query", "chat_history"], writes=["step_back_questions"])
def create_step_back_questions(state: State) -> tuple[dict[str, list[str]], State]:
    try:
        step_back_questions = cast(
            StepBackQuestions,
            _query_to_response(
                model=state["model"],
                dialog=Dialog.load(path=str(Path(DIALOGS_FOLDER) / "step_back_dialog.json")),
                response_model=StepBackQuestions,
                template_data={"question": state["query"]},
                chat_history=state.get("chat_history", None),
            ),
        ).questions
    except Exception as e:
        print(f"Error in create_step_back_questions: {e}")
        step_back_questions = []
    return {"step_back_questions": step_back_questions}, state.update(
        step_back_questions=step_back_questions
    )


@action(
    reads=["db", "query", "steps", "step_back_questions"],
    writes=["search_results"],
)
def search_lancedb(state: State, reranker: Reranker) -> tuple[dict[str, list[dict]], State]:
    try:
        results = _search_lancedb(
            db=state["db"],
            table_name=state["steps"][-1].step,
            query=state["query"],
            reranker=reranker,
            max_results=MAX_SEARCH_RESULTS,
        )
    except Exception as e:
        print(f"Error in search_lancedb: {e}")
        results = []
    return {"search_results": results}, state.update(search_results=results)
