from pathlib import Path
from typing import cast

from burr.core import State, action
from lancedb.rerankers import Reranker
from loguru import logger

from dreamai.dialog import Dialog
from dreamai.dialog_models import StepBackQuestions
from dreamai.lance_utils import search_lancedb as _search_lancedb
from dreamai.md_utils import search_query_to_md
from dreamai.response_actions import _query_to_response
from dreamai.settings import DialogSettings, RAGSettings

rag_settings = RAGSettings()
dialog_settings = DialogSettings()

MAX_SEARCH_RESULTS = rag_settings.max_search_results
DIALOGS_FOLDER = dialog_settings.dialogs_folder


@action(reads=["query"], writes=["search_results"])
def search_web(state: State) -> tuple[dict[str, list[dict]], State]:
    try:
        results = search_query_to_md(
            query=state["query"], max_results=MAX_SEARCH_RESULTS, chunk_size=0
        )
        results = [result.model_dump(exclude={"chunks"}) for result in results]
    except Exception:
        logger.exception("Error in search_web")
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
    except Exception:
        logger.exception("Error in create_step_back_questions")
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
    except Exception:
        logger.exception("Error in search_lancedb")
        results = []
    return {"search_results": results}, state.update(search_results=results)
