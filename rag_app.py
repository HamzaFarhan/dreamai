from datetime import datetime
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

from dreamai.ai import ModelName
from dreamai.dialog import Dialog, assistant_message, user_message
from dreamai.dialog_models import (
    SourcedResponse,
    SourcedSentence,
    StepBackQuestions,
    TableDescription,
    create_response_with_confidence_model,
)
from dreamai.rag_utils import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    add_to_lance_table,
    pdf_to_md_docs,
    search_and_scrape,
)
from dreamai.utils import resolve_data_path

ROUTER = "Router"
ASSISTANT = "Assistant"
WEB_OR_NOT = "WebOrNot"
WEB = "Web"
TERMINATE = "Terminate"
ROUTE_CONFIDENCE_THRESHOLD = 0.6
ASSISTANT_CONFIDENCE_THRESHOLD = 0.4
ATTEMPTS = 4
DOCS_LIMIT = 3
CHAT_HISTORY_LIMIT = 10
TERMINATORS = ["exit", "quit", "q"]

ask_kid = instructor.from_gemini(client=GenerativeModel(model_name=ModelName.GEMINI_FLASH))

is_followup_dialog = Dialog(task="dreamai/dialogs/is_followup_task.txt")
assistant_dialog = Dialog(task="dreamai/dialogs/chatbot_task.txt")
table_description_dialog = Dialog.load("dreamai/dialogs/table_description_dialog.json")
table_selection_dialog = Dialog.load("dreamai/dialogs/table_selection_dialog.json")
web_or_not_dialog = Dialog.load("dreamai/dialogs/web_or_not_dialog.json")
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
    table_descriptions_dict = {td.name: td for td in table_descriptions}
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
                    "current_databases": [
                        td.model_dump_json(indent=2) for td in table_descriptions
                    ],
                }
            ),  # type: ignore
        )
        table_description = table_descriptions_dict.get(
            table_description.name, table_description
        )
        table_descriptions_dict[table_description.name] = table_description
        add_to_lance_table(db=lance_db, table_name=table_description.name, data=md_data.chunks)
    return list(table_descriptions_dict.values())


@action(reads=[], writes=["query", "route"])
def get_query(state: State, query: str) -> tuple[dict[str, str], State]:
    route = "IsFollowup"
    if query.lower() in TERMINATORS:
        route = TERMINATE
    if "@web" in query.lower():
        route = WEB
        query = query.replace("@web", "")
    return {"query": query, "route": route}, state.update(query=query, route=route)


@action(reads=["query", "chat_history"], writes=["route", "confidence"])
def check_is_followup(
    state: State, chat_history_limit: int = CHAT_HISTORY_LIMIT
) -> tuple[dict[str, str | float], State]:
    query = state["query"]
    chat_history = state.get("chat_history", [])
    confidence = 1.0
    if len(chat_history) == 0:
        return {"route": ROUTER, "confidence": confidence}, state.update(
            route=ROUTER, confidence=confidence
        )
    is_followup_dialog.chat_history = chat_history
    try:
        is_followup = ask_kid.create(
            response_model=bool,  # type: ignore
            **is_followup_dialog.gemini_kwargs(
                user=query, chat_history_limit=chat_history_limit
            ),  # type: ignore
        )
    except Exception as e:
        print(f"Error in check_is_followup: {e}")
        is_followup = False
    route = ASSISTANT if is_followup else ROUTER
    return {"route": route, "confidence": confidence}, state.update(
        route=route, confidence=confidence
    )


@action(
    reads=["query", "db", "chat_history", "has_web"],
    writes=["route", "confidence", "table_names"],
)
def router(
    state: State,
    table_descriptions: list[TableDescription] = [],
    chat_history_limit: int = CHAT_HISTORY_LIMIT,
    attempts: int = ATTEMPTS,
) -> tuple[dict[str, str | float | list[str]], State]:
    query = state["query"]
    db: LancedbDBConnection = state["db"]
    table_names = list(db.table_names())
    response_with_confidence_model = create_response_with_confidence_model(
        response_type=table_names
    )
    table_selection_dialog.chat_history = state.get("chat_history", [])
    try:
        response = ask_kid.create(
            response_model=response_with_confidence_model,
            **table_selection_dialog.gemini_kwargs(
                template_data={
                    "query": query,
                    "database_list": [
                        table_description.model_dump_json(indent=2)
                        for table_description in table_descriptions
                    ],
                },
                chat_history_limit=chat_history_limit,
            ),  # type: ignore
            max_retries=attempts,
        )
        route = response.response  # type: ignore
        confidence = response.confidence  # type: ignore
    except Exception as e:
        print(f"Error in router: {e}")
        route = ASSISTANT
        confidence = 1.0
    if confidence <= ASSISTANT_CONFIDENCE_THRESHOLD:
        route = ASSISTANT
        confidence = 1.0
    if route == ASSISTANT and state["has_web"]:
        route = WEB_OR_NOT
        confidence = 1.0
    return {
        "route": route,
        "confidence": confidence,
        "table_names": table_names,
    }, state.update(route=route, confidence=confidence, table_names=table_names)


@action(reads=["route", "confidence", "has_web", "table_names"], writes=["route"])
def low_confidence_route(state: State) -> tuple[dict[str, str], State]:
    current_route = state["route"]
    confidence = state["confidence"]
    options = ["a", "b"]
    routes_dict = {"a": current_route, "b": ASSISTANT}
    table_names_menu_str = ""
    table_number = 1
    for table_name in state["table_names"]:
        if table_name != current_route:
            options.append(str(table_number))
            table_names_menu_str += f"{table_number}. {table_name}\n"
            routes_dict[str(table_number)] = table_name
            table_number += 1
    message = f"I've selected the table '{current_route}' for your query, but I'm not entirely confident about this choice (confidence: {confidence:.2f}).\n\n"
    message += "What should I do?\na. Proceed with the current table selection.\nb. Respond directly without using any table.\n"
    next_option = "c"
    if table_names_menu_str:
        message += f"{next_option}. Use one of the following tables instead:\n    {table_names_menu_str}\n"
        next_option = "d"
    if state["has_web"]:
        message += f"{next_option}. Perform a web search instead.\n"
        options.append(next_option)
        routes_dict[next_option] = WEB
    print(message)
    for t in TERMINATORS:
        routes_dict[t] = TERMINATE
    while True:
        user_choice = (
            input(f"Your choice ({', '.join(options+TERMINATORS)}) > ").strip().lower()
        )
        if user_choice in routes_dict:
            route = routes_dict[user_choice]
            return {"route": route}, state.update(route=route)
        print("Invalid choice. Please try again.")


@action(reads=["query", "chat_history"], writes=["route"])
def web_or_not(
    state: State, chat_history_limit: int = CHAT_HISTORY_LIMIT, attempts: int = ATTEMPTS
) -> tuple[dict[str, str], State]:
    web_or_not_dialog.chat_history = state.get("chat_history", [])
    try:
        route: str = ask_kid.create(
            response_model=Literal[ASSISTANT, WEB],  # type: ignore
            **web_or_not_dialog.gemini_kwargs(
                template_data={
                    "current_date": datetime.now().strftime("%Y-%m-%d"),
                    "user_query": state["query"],
                },
                chat_history_limit=chat_history_limit,
            ),  # type: ignore
            max_retries=attempts,
        )
    except Exception as e:
        print(f"Error in web_or_not: {e}")
        route = ASSISTANT
    return {"route": route}, state.update(route=route)


@action(reads=["query"], writes=["search_results"])
def search_web(
    state: State, docs_limit: int = DOCS_LIMIT
) -> tuple[dict[str, list[str]], State]:
    try:
        results = search_and_scrape(query=state["query"], max_results=docs_limit)
        results = [result["markdown"] for result in results]
    except Exception as e:
        print(f"Error in search_web: {e}")
        results = []
    return {"search_results": results}, state.update(search_results=results)


@action(reads=["query", "chat_history"], writes=["step_back_questions"])
def create_step_back_questions(
    state: State, chat_history_limit: int = CHAT_HISTORY_LIMIT, attempts: int = ATTEMPTS
) -> tuple[dict[str, list[str]], State]:
    step_back_dialog.chat_history = state.get("chat_history", [])
    try:
        step_back_questions = cast(
            StepBackQuestions,
            ask_kid.create(
                response_model=StepBackQuestions,
                **step_back_dialog.gemini_kwargs(
                    user=state["query"], chat_history_limit=chat_history_limit
                ),  # type: ignore
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
    writes=["search_results"],
)
def search_lancedb(
    state: State, reranker: Reranker, docs_limit: int = DOCS_LIMIT
) -> tuple[dict[str, list[str]], State]:
    db: LancedbDBConnection = state["db"]
    table = db.open_table(name=state["route"])
    try:
        results = (
            pd.concat(
                [
                    table.search(query=question, query_type="hybrid")
                    .rerank(reranker=reranker)  # type: ignore
                    .limit(docs_limit)
                    .to_pandas()
                    for question in state.get("step_back_questions", []) + [state["query"]]
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


@action(reads=["query", "chat_history", "search_results"], writes=["chat_history"])
def create_search_response(
    state: State, chat_history_limit: int = CHAT_HISTORY_LIMIT, attempts: int = ATTEMPTS
) -> tuple[dict, State]:
    query = state["query"]
    documents = state["search_results"]
    rag_dialog.chat_history = state.get("chat_history", [])
    user = rag_dialog.template.format(documents=documents, user_query=query)
    try:
        response = ask_kid.create(
            response_model=SourcedResponse,
            **rag_dialog.gemini_kwargs(user=user, chat_history_limit=chat_history_limit),  # type: ignore
            validation_context={"num_documents": len(documents)},
            max_retries=attempts,
        )
    except Exception as e:
        print(f"Error in create_search_response: {e}")
        response = SourcedResponse(
            sentences=[
                SourcedSentence(
                    sentence="Sorry, I couldn't find an answer to your question. Please try again."
                )
            ]
        )
    return {"assistant_response": str(response)}, state.append(
        chat_history=user_message(content=user)
    ).append(chat_history=assistant_message(content=str(response)))


@action(reads=["query", "chat_history"], writes=["chat_history"])
def ask_assistant(
    state: State, chat_history_limit: int = CHAT_HISTORY_LIMIT, attempts: int = ATTEMPTS
) -> tuple[dict, State]:
    query = state["query"]
    assistant_dialog.chat_history = state.get("chat_history", [])
    try:
        response = ask_kid.create(
            response_model=str,
            **assistant_dialog.gemini_kwargs(
                user=query, chat_history_limit=chat_history_limit
            ),  # type: ignore
            max_retries=attempts,
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
    has_web: bool = False,
    app_id: str | None = None,
    username: str | None = None,
    project: str = "DreamAIRAG",
) -> Application:
    tracker = LocalTrackingClient(project=project)
    builder = (
        ApplicationBuilder()
        .with_actions(
            get_query,
            check_is_followup,
            router.bind(table_descriptions=table_descriptions),
            low_confidence_route,
            web_or_not,
            search_web,
            create_step_back_questions,
            search_lancedb.bind(reranker=reranker),
            create_search_response,
            ask_assistant,
            terminate,
        )
        .with_transitions(
            (["get_query", "low_confidence_route"], "terminate", when(route=TERMINATE)),  # type: ignore
            (["get_query", "low_confidence_route"], "search_web", when(route=WEB)),  # type: ignore
            ("get_query", "check_is_followup"),
            (
                ["check_is_followup", "router", "low_confidence_route", "web_or_not"],
                "ask_assistant",
                when(route=ASSISTANT),  # type: ignore
            ),
            ("check_is_followup", "router"),
            (
                "router",
                "low_confidence_route",
                expr(f"confidence <= {ROUTE_CONFIDENCE_THRESHOLD}"),  # type: ignore
            ),
            ("router", "web_or_not", when(route=WEB_OR_NOT)),  # type: ignore
            (["router", "low_confidence_route"], "create_step_back_questions"),
            ("web_or_not", "search_web"),
            (
                ["search_web", "search_lancedb"],
                "ask_assistant",
                expr("len(search_results) == 0"),  # type: ignore
            ),
            ("create_step_back_questions", "search_lancedb"),
            (["search_web", "search_lancedb"], "create_search_response"),
            (["create_search_response", "ask_assistant"], "get_query"),
        )
        .with_tracker("local", project=project)
        .with_identifiers(app_id=app_id, partition_key=username)  # type: ignore
        .initialize_from(
            tracker,
            resume_at_next_action=True,
            default_entrypoint="get_query",
            default_state=dict(db=db, chat_history=[], has_web=has_web),
        )
    )
    return builder.build()
