from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from burr.core import State, action
from burr.visibility import trace
from instructor.client import T
from lancedb.db import DBConnection as LancedbDBConnection
from pydantic import BaseModel

from dreamai.ai import ModelName
from dreamai.dialog import Dialog, MessageType, assistant_message, user_message
from dreamai.dialog_models import (
    TableDescription,
    create_response_with_confidence_model,
    EvalWithReasoning,
)
from dreamai.settings import CreatorSettings, DialogSettings, RAGAppSettings

creator_settings = CreatorSettings()
rag_app_settings = RAGAppSettings()
dialog_settings = DialogSettings()

MODEL = creator_settings.model
ROUTER = rag_app_settings.router
ASSISTANT = rag_app_settings.assistant
FOLLOWUP_OR_NOT = rag_app_settings.followup_or_not
TERMINATORS = rag_app_settings.terminators
TERMINATE = rag_app_settings.terminate
WEB = rag_app_settings.web
WEB_OR_NOT = rag_app_settings.web_or_not
UPDATE_CHAT_HISTORY = rag_app_settings.update_chat_history
DEFAULT_CONFIDENCE = rag_app_settings.default_confidence
ASSISTANT_CONFIDENCE_THRESHOLD = rag_app_settings.assistant_confidence_threshold
DIALOGS_FOLDER = dialog_settings.dialogs_folder


class StepWithConfidence(BaseModel):
    step: str
    confidence: float


@trace()
def _query_to_response(
    query: str = "",
    model: ModelName = MODEL,
    dialog: Dialog | None = None,
    response_model: type[T] = str,
    template_data: dict | None = None,
    chat_history: list[MessageType] | None = None,
    validation_context: dict[str, Any] | None = None,
) -> T:
    dialog = dialog or Dialog(task=str(Path(DIALOGS_FOLDER) / "assistant_task.txt"))
    if chat_history:
        dialog.chat_history = chat_history
    creator, creator_kwargs = dialog.creator_with_kwargs(
        model=model, user=query, template_data=template_data
    )
    # print(f"\n\nMESSAGES:\n{creator_kwargs['messages']}\n\n")
    response = creator.create(
        response_model=response_model, validation_context=validation_context, **creator_kwargs
    )
    return response


def _query_to_route(
    query: str,
    model: ModelName,
    routes: list[Any],
    chat_history: list[MessageType] | None = None,
) -> StepWithConfidence:
    response_model = create_response_with_confidence_model(response_type=routes)
    dialog = Dialog(
        task=str(Path(DIALOGS_FOLDER) / "router_task.txt"), chat_history=chat_history or []
    )
    response = _query_to_response(
        query=query,
        model=model,
        dialog=dialog,
        response_model=response_model,
        template_data={"user_query": query, "available_routes": routes},
    )
    return StepWithConfidence(step=response.response, confidence=response.confidence)  # type: ignore


def _get_route(query: str) -> str:
    route = FOLLOWUP_OR_NOT
    if query.lower() in TERMINATORS:
        route = TERMINATE
    if "@web" in query.lower():
        route = WEB
    return route


@action(reads=[], writes=["query", "steps"])
def get_query(state: State, query: str) -> tuple[dict[str, str | StepWithConfidence], State]:
    route = _get_route(query=query)
    if route == WEB:
        query = query.replace("@web", "").strip()
    step = StepWithConfidence(step=route, confidence=DEFAULT_CONFIDENCE)
    return {"query": query, "step": step}, state.update(query=query).append(steps=step)


@action(reads=["model", "query", "chat_history"], writes=["steps"])
def followup_or_not(state: State) -> tuple[dict[str, StepWithConfidence], State]:
    chat_history = state.get("chat_history", [])
    if len(chat_history) == 0:
        step = StepWithConfidence(step=ROUTER, confidence=DEFAULT_CONFIDENCE)
        return {"step": step}, state.append(steps=step)
    try:
        followup = _query_to_response(
            query=state["query"],
            model=state["model"],
            dialog=Dialog(
                task=str(Path(DIALOGS_FOLDER) / "followup_or_not_task.txt"),
                chat_history=chat_history,
            ),
            response_model=bool,  # type: ignore
        )
    except Exception as e:
        print(f"Error in followup_or_not: {e}")
        followup = False
    route = ASSISTANT if followup else ROUTER
    step = StepWithConfidence(step=route, confidence=DEFAULT_CONFIDENCE)
    return {"step": step}, state.append(steps=step)


@action(reads=["model", "query", "chat_history"], writes=["steps"])
def web_or_not(state: State) -> tuple[dict[str, StepWithConfidence], State]:
    try:
        dialog = Dialog.load(path=str(Path(DIALOGS_FOLDER) / "web_or_not_dialog.json"))
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
                user_message(content=str(Path(DIALOGS_FOLDER) / "confidence_message.txt")),
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
    step = StepWithConfidence(step=route, confidence=confidence)
    return {"step": step}, state.append(steps=step)


@action(
    reads=["db", "model", "query", "chat_history", "only_data", "has_web"], writes=["steps"]
)
def router(
    state: State, table_descriptions: list[TableDescription] = []
) -> tuple[dict[str, StepWithConfidence], State]:
    db: LancedbDBConnection = state["db"]
    try:
        response = _query_to_response(
            model=state["model"],
            dialog=Dialog.load(path=str(Path(DIALOGS_FOLDER) / "table_selection_dialog.json")),
            response_model=create_response_with_confidence_model(
                response_type=list(db.table_names())
            ),
            template_data={
                "user_query": state["query"],
                "database_list": [
                    table_description.model_dump_json(indent=2)
                    for table_description in table_descriptions
                ],
            },
            chat_history=state.get("chat_history", None),
        )
        route = response.response  # type: ignore
        confidence = response.confidence  # type: ignore
    except Exception as e:
        print(f"Error in router: {e}")
        route = ASSISTANT
        confidence = DEFAULT_CONFIDENCE
    if confidence <= ASSISTANT_CONFIDENCE_THRESHOLD and not state["only_data"]:
        route = ASSISTANT
        confidence = DEFAULT_CONFIDENCE
    if route == ASSISTANT and state["has_web"]:
        route = WEB_OR_NOT
        confidence = DEFAULT_CONFIDENCE
    step = StepWithConfidence(step=route, confidence=confidence)
    return {"step": step}, state.append(steps=step)


@action(
    reads=["model", "query", "assistant_response", "chat_history"],
    writes=["answer_evaluation", "steps"],
)
def evaluate_answer(
    state: State,
) -> tuple[dict[str, StepWithConfidence | EvalWithReasoning], State]:
    try:
        evaluation = _query_to_response(
            model=state["model"],
            dialog=Dialog.load(path=str(Path(DIALOGS_FOLDER) / "answer_eval_dialog.json")),
            response_model=EvalWithReasoning,  # type: ignore
            template_data={"query": state["query"], "answer": state["assistant_response"]},
            chat_history=state.get("chat_history", None),
        )
    except Exception as e:
        print(f"Error in evaluate_answer: {e}")
        evaluation = EvalWithReasoning(evaluation=True, reasoning="")
    route = UPDATE_CHAT_HISTORY if evaluation.evaluation else ASSISTANT
    step = StepWithConfidence(step=route, confidence=DEFAULT_CONFIDENCE)
    return {"step": step, "answer_evaluation": evaluation}, state.update(
        answer_evaluation=evaluation
    ).append(steps=step)
