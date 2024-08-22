from datetime import datetime
from typing import Any, Literal

from burr.core import State, action
from instructor.client import T
from lancedb.db import DBConnection as LancedbDBConnection

from dreamai.ai import ModelName
from dreamai.dialog import Dialog, MessageType, assistant_message, user_message
from dreamai.dialog_models import (
    TableDescription,
    create_response_with_confidence_model,
)
from dreamai.rag_utils import StepWithConfidence
from dreamai.settings import CreatorSettings, DialogSettings, RAGAppSettings

creator_settings = CreatorSettings()
rag_app_settings = RAGAppSettings()
dialog_settings = DialogSettings()

MODEL = creator_settings.model
ATTEMPTS = creator_settings.attempts
ROUTER = rag_app_settings.router
ASSISTANT = rag_app_settings.assistant
TERMINATORS = rag_app_settings.terminators
TERMINATE = rag_app_settings.terminate
WEB = rag_app_settings.web
WEB_OR_NOT = rag_app_settings.web_or_not
DEFAULT_CONFIDENCE = rag_app_settings.default_confidence
ASSISTANT_CONFIDENCE_THRESHOLD = rag_app_settings.assistant_confidence_threshold
DIALOGS_FOLDER = dialog_settings.dialogs_folder


def _get_route(query: str) -> str:
    route = "followup_or_not"
    if query.lower() in TERMINATORS:
        route = TERMINATE
    if "@web" in query.lower():
        route = WEB
    return route


def _query_to_response(
    query: str = "",
    model: ModelName = MODEL,
    dialog: Dialog | None = None,
    response_model: type[T] = str,
    template_data: dict | None = None,
    chat_history: list[MessageType] | None = None,
    validation_context: dict[str, Any] | None = None,
    attempts: int = ATTEMPTS,
) -> T:
    dialog = dialog or Dialog(task=f"{DIALOGS_FOLDER}/assistant_task.txt")
    if chat_history:
        dialog.chat_history = chat_history
    creator, creator_kwargs = dialog.creator_with_kwargs(
        model=model, user=query, template_data=template_data
    )
    response = creator.create(
        response_model=response_model,
        validation_context=validation_context,
        max_retries=attempts,
        **creator_kwargs,
    )
    return response


def _query_to_route(
    query: str,
    model: ModelName,
    routes: list[Any],
    chat_history: list[MessageType] | None = None,
) -> dict[str, str | float]:
    response_model = create_response_with_confidence_model(response_type=routes)
    dialog = Dialog(
        task=f"{DIALOGS_FOLDER}/router_task.txt", chat_history=chat_history or []
    )
    response = _query_to_response(
        query=query,
        model=model,
        dialog=dialog,
        response_model=response_model,
        template_data={"user_query": query, "available_routes": routes},
    )
    return {"route": response.response, "confidence": response.confidence}  # type: ignore


@action(reads=[], writes=["query", "steps"])
def get_query(state: State, query: str) -> tuple[dict[str, str], State]:
    route = _get_route(query=query)
    if route == WEB:
        query = query.replace("@web", "").strip()
    return {"query": query, "route": route}, state.update(query=query).append(
        steps=StepWithConfidence(step=route, confidence=DEFAULT_CONFIDENCE)
    )


@action(reads=["model", "query", "chat_history"], writes=["route", "confidence"])
def followup_or_not(state: State) -> tuple[dict[str, str | float], State]:
    chat_history = state.get("chat_history", [])
    if len(chat_history) == 0:
        return {"route": ROUTER, "confidence": DEFAULT_CONFIDENCE}, state.update(
            route=ROUTER, confidence=DEFAULT_CONFIDENCE
        )
    try:
        followup = _query_to_response(
            query=state["query"],
            model=state["model"],
            dialog=Dialog(
                task=f"{DIALOGS_FOLDER}/followup_or_not_task.txt",
                chat_history=chat_history,
            ),
            response_model=bool,  # type: ignore
        )
    except Exception as e:
        print(f"Error in followup_or_not: {e}")
        followup = False
    route = ASSISTANT if followup else ROUTER
    return {"route": route, "confidence": DEFAULT_CONFIDENCE}, state.append(
        steps=StepWithConfidence(step=route, confidence=DEFAULT_CONFIDENCE)
    )


@action(reads=["model", "query", "chat_history"], writes=["steps"])
def web_or_not(
    state: State,
) -> tuple[dict[str, str | float], State]:
    try:
        dialog = Dialog.load(path=f"{DIALOGS_FOLDER}/web_or_not_dialog.json")
        dialog.chat_history += state.get("chat_history", [])
        route: str = _query_to_response(
            model=state["model"],
            dialog=dialog,
            response_model=Literal[ASSISTANT, WEB],  # type: ignore
            template_data={
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "user_query": state["query"],
            },
        )
        dialog.add_messages(
            [
                assistant_message(content=route),
                user_message(content=f"{DIALOGS_FOLDER}/confidence_message.txt"),
            ]
        )
        confidence: float = _query_to_response(
            model=state["model"],
            dialog=dialog,
            response_model=float,  # type: ignore
        )

    except Exception as e:
        print(f"Error in web_or_not: {e}")
        route = ASSISTANT
        confidence = DEFAULT_CONFIDENCE
    return {"route": route, "confidence": confidence}, state.append(
        steps=StepWithConfidence(step=route, confidence=confidence)
    )


@action(
    reads=["query", "db", "chat_history", "has_web"],
    writes=["steps", "table_names"],
)
def router(
    state: State, table_descriptions: list[TableDescription] = []
) -> tuple[dict[str, str | float | list[str]], State]:
    db: LancedbDBConnection = state["db"]
    table_names = list(db.table_names())
    try:
        response = _query_to_response(
            model=state["model"],
            dialog=Dialog.load(path=f"{DIALOGS_FOLDER}/table_selection_dialog.json"),
            response_model=create_response_with_confidence_model(
                response_type=table_names
            ),
            template_data={
                "user_query": state["query"],
                "database_list": [
                    table_description.model_dump_json(indent=2)
                    for table_description in table_descriptions
                ],
            },
        )
        route = response.response  # type: ignore
        confidence = response.confidence  # type: ignore
    except Exception as e:
        print(f"Error in router: {e}")
        route = ASSISTANT
        confidence = DEFAULT_CONFIDENCE
    if confidence <= ASSISTANT_CONFIDENCE_THRESHOLD:
        route = ASSISTANT
        confidence = DEFAULT_CONFIDENCE
    if route == ASSISTANT and state["has_web"]:
        route = WEB_OR_NOT
        confidence = DEFAULT_CONFIDENCE
    return {
        "route": route,
        "confidence": confidence,
        "table_names": table_names,
    }, state.append(steps=StepWithConfidence(step=route, confidence=confidence)).update(
        table_names=table_names
    )
