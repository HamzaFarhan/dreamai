from pathlib import Path
from typing import cast

from burr.core import State, action
from lancedb.rerankers import Reranker
from loguru import logger

from dreamai.dialog import BadExample, Dialog
from dreamai.dialog_models import StepBackQuestions
from dreamai.lance_utils import search_lancedb as _search_lancedb
from dreamai.md_utils import search_query_to_md
from dreamai.response_actions import _query_to_response
from dreamai.settings import DialogSettings, RAGSettings

rag_settings = RAGSettings()
dialog_settings = DialogSettings()

MAX_SEARCH_RESULTS = rag_settings.max_search_results
DIALOGS_FOLDER = dialog_settings.dialogs_folder


@action(reads=["query"], writes=["search_results", "bad_interaction"])
def search_web(state: State) -> tuple[dict[str, list[dict] | BadExample | None], State]:
    try:
        results = search_query_to_md(
            query=state["query"], max_search_results=MAX_SEARCH_RESULTS, chunk_size=0
        )
        results = [result.model_dump(exclude={"chunks"}) for result in results]
    except Exception:
        logger.exception("Error in search_web")
        results = []
    bad_interaction = None
    if len(results) == 0:
        bad_interaction = BadExample(
            user=f"<task>Please search the web for the most up-to-date information to answer the user query.</task>\n\n<user_query>{state['query'].strip()}</user_query>",
            assistant="I've attempted to search the web for information related to your query, but no relevant results were found. Would you like me to provide an answer based on my existing knowledge, with the caveat that it may not reflect the most current information?",
            feedback="Yes, please answer using your existing knowledge. Begin your response with '[Answering from internal knowledge due to lack of web results]' to help us track these instances. Also, suggest some alternative search terms or approaches that might yield better web results for this query.",
        )
    return {"search_results": results, "bad_interaction": bad_interaction}, state.update(
        search_results=results, bad_interaction=bad_interaction
    )


@action(reads=["model", "query", "chat_history"], writes=["step_back_questions"])
def create_step_back_questions(state: State) -> tuple[dict[str, list[str]], State]:
    try:
        step_back_questions = cast(
            StepBackQuestions,
            _query_to_response(
                model=state["model"],
                dialog=Dialog.load(path=str(Path(DIALOGS_FOLDER) / "step_back_dialog.json")),
                response_model=StepBackQuestions,
                template_data={"question": state["query"].replace(":", "")},
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
    reads=["db", "table_name", "query", "steps", "step_back_questions"],
    writes=["search_results", "bad_interaction"],
)
def search_lancedb(
    state: State, reranker: Reranker, max_search_results: int = MAX_SEARCH_RESULTS
) -> tuple[dict[str, list[dict] | BadExample | None], State]:
    try:
        results = _search_lancedb(
            db=state["db"],
            # table_name=state["steps"][-1].step,
            table_name=state["table_name"],
            query=state["query"],
            reranker=reranker,
            max_search_results=max_search_results,
        )
    except Exception:
        logger.exception("Error in search_lancedb")
        results = []
    bad_interaction = None
    if len(results) == 0:
        bad_interaction = BadExample(
            user=f"<task>Please search the database for the most up-to-date information to answer the user query.</task>\n\n<user_query>{state['query'].strip()}</user_query>",
            assistant="I've searched the database, but no relevant documents were found for your query. Would you like me to answer based on my general knowledge instead?",
            feedback="Yes, please answer using your general knowledge. Start your response with '[Answering from general knowledge due to lack of database results]' to help us track these instances.",
        )
    return {"search_results": results, "bad_interaction": bad_interaction}, state.update(
        search_results=results, bad_interaction=bad_interaction
    )
