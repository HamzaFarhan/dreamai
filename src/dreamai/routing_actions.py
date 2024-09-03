from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Self

from burr.core import State, action
from loguru import logger
from pydantic import BaseModel, Field, model_validator

from dreamai.ai import ModelName
from dreamai.dialog import BadExample, Dialog, MessageType, assistant_message, user_message
from dreamai.dialog_models import (
    EvalWithReasoning,
    TableDescription,
    create_response_with_confidence_model,
)
from dreamai.response_actions import _query_to_response
from dreamai.settings import CreatorSettings, DialogSettings, RAGAppSettings, RAGRoute

creator_settings = CreatorSettings()
rag_app_settings = RAGAppSettings()
dialog_settings = DialogSettings()

MODEL = creator_settings.model
DEFAULT_CONFIDENCE = rag_app_settings.default_confidence
NON_ASSISTANT_CONFIDENCE_THRESHOLD = rag_app_settings.non_assistant_confidence_threshold
STEP_CONFIDENCE_THRESHOLD = rag_app_settings.step_confidence_threshold
DIALOGS_FOLDER = dialog_settings.dialogs_folder
TERMINATORS = rag_app_settings.terminators


class StepWithConfidence(BaseModel):
    step: str
    confidence: float = Field(ge=0.0, le=1.0)
    comment: str = ""

    @model_validator(mode="after")
    def validate_disclaimer(self) -> Self:
        if not self.comment:
            if self.confidence <= STEP_CONFIDENCE_THRESHOLD:
                self.comment = f"I believe the next step is {self.step}. But I'm only {self.confidence*100:.0f}% confident."
            else:
                self.comment = f"I am {self.confidence*100:.0f}% confident that the next step is {self.step}."
        return self


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


def _get_route(query: str) -> tuple[str, str]:
    route = RAGRoute.FOLLOWUP_OR_NOT
    if query.lower() in TERMINATORS:
        route = RAGRoute.TERMINATE
    elif "@ai" in query.lower():
        route = RAGRoute.ASSISTANT
    elif "@data" in query.lower():
        route = RAGRoute.ROUTER
    elif "@web" in query.lower():
        route = RAGRoute.WEB
    return route, query.replace("@ai", "").replace("@data", "").replace("@web", "").strip()


def _tables_menu(
    table: str,
    table_names: list[str],
    confidence: float,
    only_data: bool = False,
    has_web: bool = False,
) -> list[str]:
    menu = [f"{i}. {table_name}" for i, table_name in enumerate(table_names, start=1)]
    menu.append(f"{len(menu) + 1}. Use the selected table: {table}")
    if not only_data:
        if has_web:
            menu.append(f"{len(menu) + 1}. Search the web")
        menu.append(f"{len(menu) + 1}. Ignore tables and answering from general knowledge")
    menu.append(f"\nJust the number (1-{len(menu)}) > ")
    menu.insert(
        0,
        f"\n\nI've selected a table but I'm only {confidence*100:.0f}% confident. What should I do?\n",
    )
    return menu


@action(reads=["only_ai", "only_data", "only_web", "steps"], writes=["query", "steps"])
def get_query(state: State, query: str) -> tuple[dict[str, str | StepWithConfidence], State]:
    if state["only_ai"]:
        route = RAGRoute.ASSISTANT
    elif state["only_data"]:
        route = RAGRoute.ROUTER
    elif state["only_web"]:
        route = RAGRoute.WEB
    else:
        route, query = _get_route(query=query)
    step = StepWithConfidence(step=route, confidence=DEFAULT_CONFIDENCE)
    return {"query": query, "step": step}, state.update(query=query).append(steps=step)


@action(reads=["model", "query", "chat_history"], writes=["steps"])
def followup_or_not(state: State) -> tuple[dict[str, StepWithConfidence], State]:
    chat_history = state.get("chat_history", [])
    if len(chat_history) == 0:
        step = StepWithConfidence(step=RAGRoute.ROUTER, confidence=DEFAULT_CONFIDENCE)
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
    except Exception:
        logger.exception("Error in followup_or_not")
        followup = False
    route = RAGRoute.ASSISTANT if followup else RAGRoute.ROUTER
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
            response_model=Literal[RAGRoute.ASSISTANT, RAGRoute.WEB],  # type: ignore
            template_data={
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "user_query": state["query"],
            },
        )
        dialog.add_messages(
            [
                assistant_message(content=route),
                user_message(content=str(Path(DIALOGS_FOLDER) / "confidence_task.txt")),
            ]
        )
        confidence: float = _query_to_response(
            model=state["model"],
            dialog=dialog,
            response_model=float,  # type: ignore
        )
    except Exception:
        logger.exception("Error in web_or_not")
        route = RAGRoute.ASSISTANT
        confidence = DEFAULT_CONFIDENCE
    step = StepWithConfidence(step=route, confidence=confidence)
    return {"step": step}, state.append(steps=step)


@action(
    reads=["db", "model", "query", "chat_history", "only_data", "has_web"],
    writes=["steps", "menu"],
)
def router(
    state: State, table_descriptions: list[TableDescription] = []
) -> tuple[dict[str, StepWithConfidence | list[str]], State]:
    only_data = state.get("only_data", False)
    has_web = state.get("has_web", False)
    menu = []
    route = RAGRoute.ASSISTANT
    confidence = DEFAULT_CONFIDENCE
    if db := state.get("db", None):
        if table_names := list(db.table_names()):
            try:
                response = _query_to_response(
                    model=state["model"],
                    dialog=Dialog.load(
                        path=str(Path(DIALOGS_FOLDER) / "table_selection_dialog.json")
                    ),
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
                    chat_history=state.get("chat_history", None),
                )
                route = response.response  # type: ignore
                confidence = response.confidence  # type: ignore
                # if confidence <= NON_ASSISTANT_CONFIDENCE_THRESHOLD:
                #     menu = _tables_menu(
                #         table=route,
                #         table_names=table_names,
                #         confidence=confidence,
                #         only_data=only_data,
                #         has_web=has_web,
                #     )
                #     route = RAGRoute.MENU
                #     confidence = DEFAULT_CONFIDENCE
            except Exception:
                logger.exception("Error in router")
    if confidence <= NON_ASSISTANT_CONFIDENCE_THRESHOLD and not only_data:
        logger.info(f"Route: {route} with confidence: {confidence*100:.0f}%")
        route = RAGRoute.ASSISTANT
        confidence = DEFAULT_CONFIDENCE
    if route == RAGRoute.ASSISTANT and has_web:
        route = RAGRoute.WEB_OR_NOT
        confidence = DEFAULT_CONFIDENCE
    step = StepWithConfidence(step=route, confidence=confidence)
    return {"step": step, "menu": menu}, state.append(steps=step).update(menu=menu)


@action(
    reads=[
        "model",
        "query",
        "assistant_response",
        "chat_history",
        "source_docs",
        "action_attempts",
    ],
    writes=["answer_evaluation", "action_attempts", "bad_interaction"],
)
def evaluate_answer(
    state: State,
) -> tuple[dict[str, int | EvalWithReasoning | BadExample | None], State]:
    dialog = Dialog.load(path=str(Path(DIALOGS_FOLDER) / "answer_eval_dialog.json"))
    user = dialog.template.format(
        query=state["query"],
        source_docs=state.get("source_docs", []),
        answer=state["assistant_response"],
    )
    try:
        evaluation = _query_to_response(
            query=user,
            model=state["model"],
            dialog=dialog,
            response_model=EvalWithReasoning,  # type: ignore
            chat_history=state.get("chat_history", None),
        )
    except Exception:
        logger.exception("Error in evaluate_answer")
        evaluation = EvalWithReasoning(evaluation=True, reasoning="")
    action_attempts = state.get("action_attempts", 0)
    if not evaluation.evaluation:
        action_attempts += 1
        bad_interaction = BadExample(
            user=f"<source_docs>{state.get('source_docs', [])}</source_docs>\n\n<user>{state['query']}</user>",
            assistant=state["assistant_response"],
            feedback=evaluation.reasoning + f"\nThis was attempt number: {action_attempts}.",
        )
    else:
        action_attempts = 0
        bad_interaction = None
    return {
        "answer_evaluation": evaluation,
        "action_attempts": action_attempts,
        "bad_interaction": bad_interaction,
    }, state.update(answer_evaluation=evaluation).update(
        action_attempts=action_attempts
    ).update(bad_interaction=bad_interaction)
