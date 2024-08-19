from pathlib import Path
from typing import Literal, cast

import instructor
import pandas as pd
from burr.core import Application, ApplicationBuilder, State, expr, when
from burr.core.action import action
from burr.tracking import LocalTrackingClient
from google.generativeai import GenerativeModel
from lancedb.db import DBConnection as LancedbDBConnection
from lancedb.rerankers import Reranker

from dreamai.ai import ModelName, assistant_message, user_message
from dreamai.dialog import Dialog
from dreamai.dialog_models import (
    SourcedRAGResponse,
    SourcedRAGSentence,
    StepBackQuestions,
    TableDescription,
)
from dreamai.rag import CHUNK_OVERLAP, CHUNK_SIZE, add_to_lance_table, pdf_to_md_docs
from dreamai.utils import resolve_data_path

ATTEMPTS = 4
DOCS_LIMIT = 3
TERMINATORS = ["exit", "quit", "q"]

ask_kid = instructor.from_gemini(
    client=GenerativeModel(model_name=ModelName.GEMINI_FLASH)
)


table_description_dialog = Dialog.load("dreamai/dialogs/table_description_dialog.json")
table_selection_dialog = Dialog.load("dreamai/dialogs/table_selection_dialog.json")
step_back_dialog = Dialog.load("dreamai/dialogs/step_back_dialog.json")
rag_dialog = Dialog.load("dreamai/dialogs/sourced_rag_dialog.json")


def get_user_query() -> str:
    query = ""
    while not query:
        query = input(f"({', '.join(TERMINATORS)} to exit) > ").strip()
    return query


def add_data(
    lance_db: LancedbDBConnection,
    data_path: list[str | Path] | str | Path,
    table_descriptions: list[TableDescription] = [],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[TableDescription]:
    for file in resolve_data_path(data_path=data_path):
        table_name = Path(file).stem
        md_data = pdf_to_md_docs(
            file_path=file, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        table_description: TableDescription = ask_kid.create(
            response_model=TableDescription,
            **table_description_dialog.gemini_kwargs(
                template_data={
                    "database_name": table_name,
                    "sample_text": md_data.markdown,
                }
            ),  # type: ignore
            validation_context={"names": [t.name for t in table_descriptions]},
        )
        table_descriptions.append(table_description)
        _ = add_to_lance_table(
            db=lance_db, table_name=table_description.name, data=md_data.chunks
        )
    return table_descriptions


@action(reads=["db"], writes=["query", "route"])
def router(
    state: State,
    query: str,
    table_descriptions: list[TableDescription] = [],
    attempts: int = ATTEMPTS,
) -> tuple[dict[str, str], State]:
    if query.lower() in TERMINATORS:
        route = "Terminate"
        return {"route": route}, state.update(query=query, route=route)
    db: LancedbDBConnection = state["db"]
    table_names = db.table_names()
    routes = Literal[*table_names, "Assistant"]  # type: ignore
    try:
        route: str = ask_kid.create(
            response_model=routes,
            **table_selection_dialog.gemini_kwargs(
                template_data={
                    "query": query,
                    "database_list": [
                        table_description.model_dump_json(indent=2)
                        for table_description in table_descriptions
                    ],
                }
            ),  # type: ignore
            max_retries=attempts,
        )
    except Exception as e:
        print(f"Error in router: {e}")
        route = "Assistant"
    return {"route": route}, state.update(query=query, route=route)


@action(reads=["query"], writes=["step_back_questions"])
def create_step_back_questions(
    state: State, attempts: int = ATTEMPTS
) -> tuple[dict[str, list[str]], State]:
    query: str = state["query"]
    try:
        step_back_questions = cast(
            StepBackQuestions,
            ask_kid.create(
                response_model=StepBackQuestions,
                **step_back_dialog.gemini_kwargs(user=query),  # type: ignore
                max_retries=attempts,
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
    writes=["lancedb_results"],
)
def search_lancedb(
    state: State, reranker: Reranker, docs_limit: int = DOCS_LIMIT
) -> tuple[dict[str, list[str]], State]:
    db: LancedbDBConnection = state["db"]
    table = db.open_table(name=state["route"])
    try:
        res = (
            pd.concat(
                [
                    table.search(
                        query=question,
                        query_type="hybrid",
                    )
                    .rerank(reranker=reranker)  # type: ignore
                    .limit(docs_limit)
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
        res = []

    return {"lancedb_results": res}, state.update(lancedb_results=res)


@action(
    reads=["query", "lancedb_results", "chat_history"],
    writes=["chat_history", "lancedb_results"],
)
def create_rag_response(state: State, attempts: int = 3) -> tuple[dict, State]:
    query = state["query"]
    documents = state["lancedb_results"]
    rag_dialog.chat_history += state.get("chat_history", [])
    try:
        response = ask_kid.create(
            response_model=SourcedRAGResponse,
            **rag_dialog.gemini_kwargs(
                template_data={"documents": documents, "user_query": query}
            ),  # type: ignore
            validation_context={"num_documents": len(documents)},
            max_retries=attempts,
        )
    except Exception as e:
        print(f"Error in create_rag_response: {e}")
        response = SourcedRAGResponse(
            sentences=[
                SourcedRAGSentence(
                    sentence="Sorry, I couldn't find an answer to your question. Please try again."
                )
            ]
        )
    return {"assistant_response": str(response)}, state.append(
        chat_history=user_message(content=query)
    ).append(chat_history=assistant_message(content=str(response))).update(
        lancedb_results=[]
    )


@action(reads=["query", "chat_history"], writes=["chat_history"])
def ask_assistant(state: State) -> tuple[dict, State]:
    query = state["query"]
    assistant_dialog = Dialog(chat_history=state.get("chat_history", []))
    try:
        response = ask_kid.create(
            response_model=str,
            **assistant_dialog.gemini_kwargs(user=query),  # type: ignore
        )
    except Exception as e:
        print(f"Error in ask_assistant: {e}")
        response = "I'm sorry, but I encountered an error while processing your request. Could you please try again?"
    return {"assistant_response": response}, state.append(
        chat_history=user_message(content=query)
    ).append(chat_history=assistant_message(content=response))


@action(reads=["chat_history"], writes=[])
def terminate(state: State) -> tuple[dict[str, list[dict[str, str]]], State]:
    return {"chat_history": state["chat_history"]}, state


def application(
    db: LancedbDBConnection,
    reranker: Reranker,
    table_descriptions: list[TableDescription] = [],
    app_id: str | None = None,
    username: str | None = None,
    project: str = "DreamAIRAG",
) -> Application:
    tracker = LocalTrackingClient(project=project)
    builder = (
        ApplicationBuilder()
        .with_actions(
            router.bind(table_descriptions=table_descriptions, attempts=ATTEMPTS),
            create_step_back_questions.bind(attempts=ATTEMPTS),
            search_lancedb.bind(reranker=reranker, docs_limit=DOCS_LIMIT),
            create_rag_response.bind(attempts=ATTEMPTS),
            ask_assistant.bind(attempts=ATTEMPTS),
            terminate,
        )
        .with_transitions(
            ("router", "terminate", when(route="Terminate")),  # type: ignore
            ("router", "ask_assistant", when(route="Assistant")),  # type: ignore
            ("router", "create_step_back_questions"),
            ("create_step_back_questions", "search_lancedb"),
            ("search_lancedb", "ask_assistant", expr("len(lancedb_results) == 0")),  # type: ignore
            ("search_lancedb", "create_rag_response"),
            ("create_rag_response", "router"),
            ("ask_assistant", "router"),
        )
        .with_tracker("local", project=project)
        .with_identifiers(app_id=app_id, partition_key=username)  # type: ignore
        .initialize_from(
            tracker,
            resume_at_next_action=True,
            default_entrypoint="router",
            default_state=dict(db=db, chat_history=[]),
        )
    )
    return builder.build()
