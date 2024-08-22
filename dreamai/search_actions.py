from pathlib import Path
from typing import cast

import pandas as pd
from burr.core import State, action
from lancedb.db import DBConnection as LancedbDBConnection
from lancedb.rerankers import Reranker

from dreamai.ai import ModelName
from dreamai.dialog import Dialog
from dreamai.dialog_models import StepBackQuestions, TableDescription
from dreamai.rag_utils import add_to_lance_table, pdf_to_md_docs, search_and_scrape
from dreamai.routing_actions import _query_to_response
from dreamai.settings import DialogSettings, RAGSettings
from dreamai.utils import resolve_data_path

rag_settings = RAGSettings()
dialog_settings = DialogSettings()

MAX_SEARCH_RESULTS = rag_settings.max_search_results
DIALOGS_FOLDER = dialog_settings.dialogs_folder
CHUNK_SIZE = rag_settings.chunk_size
CHUNK_OVERLAP = rag_settings.chunk_overlap


def add_data_with_descriptions(
    model: ModelName,
    lance_db: LancedbDBConnection,
    data_path: list[str | Path] | str | Path,
    table_descriptions: list[TableDescription] = [],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[TableDescription]:
    table_descriptions_dict = {td.name: td for td in table_descriptions}
    for file in resolve_data_path(data_path=data_path):
        table_name = Path(file).stem
        md_data = pdf_to_md_docs(
            file_path=file, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        table_description: TableDescription = _query_to_response(
            model=model,
            dialog=Dialog.load(f"{DIALOGS_FOLDER}/table_description_dialog.json"),
            response_model=TableDescription,
            template_data={
                "database_name": table_name,
                "sample_text": md_data.markdown,
                "current_databases": [
                    td.model_dump_json(indent=2) for td in table_descriptions
                ],
            },
        )
        table_description = table_descriptions_dict.get(
            table_description.name, table_description
        )
        table_descriptions_dict[table_description.name] = table_description
        add_to_lance_table(
            db=lance_db, table_name=table_description.name, data=md_data.chunks
        )
    return list(table_descriptions_dict.values())


@action(reads=["query"], writes=["search_results"])
def search_web(state: State) -> tuple[dict[str, list[str]], State]:
    try:
        results = search_and_scrape(
            query=state["query"], max_results=MAX_SEARCH_RESULTS
        )
        results = [result["markdown"] for result in results]
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
                dialog=Dialog.load(f"{DIALOGS_FOLDER}/step_back_dialog.json"),
                response_model=StepBackQuestions,
                template_data={"original_question": state["query"]},
                chat_history=state.get("chat_history", []),
            ),
        ).questions
    except Exception as e:
        print(f"Error in create_step_back_questions: {e}")
        step_back_questions = []
    return {"step_back_questions": step_back_questions}, state.update(
        step_back_questions=step_back_questions
    )


@action(
    reads=["query", "route", "step_back_questions", "db"],
    writes=["search_results"],
)
def search_lancedb(
    state: State, reranker: Reranker
) -> tuple[dict[str, list[str]], State]:
    db: LancedbDBConnection = state["db"]
    table = db.open_table(name=state["route"])
    try:
        results = (
            pd.concat(
                [
                    table.search(query=question, query_type="hybrid")
                    .rerank(reranker=reranker)  # type: ignore
                    .limit(MAX_SEARCH_RESULTS)
                    .to_pandas()
                    for question in state.get("step_back_questions", [])
                    + [state["query"]]
                ]
            )
            .drop_duplicates("text")
            .sort_values("_relevance_score", ascending=False)
            .reset_index(drop=True)
        )["text"].tolist()
    except Exception as e:
        print(f"Error in search_and_rerank: {e}")
        results = []
    return {"search_results": results}, state.update(search_results=results)
