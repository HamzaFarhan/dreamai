from pathlib import Path

from burr.core import Application, ApplicationBuilder, expr
from burr.tracking import LocalTrackingClient
from lancedb.db import DBConnection as LancedbDBConnection
from lancedb.rerankers import Reranker
from loguru import logger

from dreamai.ai import ModelName
from dreamai.dialog import MessageType
from dreamai.dialog_models import TableDescription
from dreamai.response_actions import (
    ask_assistant,
    create_search_response,
    terminate,
    update_chat_history,
)
from dreamai.routing_actions import (
    evaluate_answer,
    followup_or_not,
    get_query,
    router,
    web_or_not,
)
from dreamai.search_actions import create_step_back_questions, search_lancedb, search_web
from dreamai.settings import CreatorSettings, RAGAppSettings, RAGRoute

creator_settings = CreatorSettings()
rag_app_settings = RAGAppSettings()

MODEL = creator_settings.model
ONLY_AI = rag_app_settings.only_ai
ONLY_DATA = rag_app_settings.only_data
ONLY_WEB = rag_app_settings.only_web
HAS_WEB = rag_app_settings.has_web
ACTION_ATTEMPTS_LIMIT = rag_app_settings.action_attempts_limit


def action_loop(
    action: str,
    checker: str = "evaluate_answer",
    condition: str = "answer_evaluation.evaluation",
    updater_action: str = "update_chat_history",
    assistant_action: str = "ask_assistant",
    action_attempts_limit: int = ACTION_ATTEMPTS_LIMIT,
) -> list[tuple]:
    return [
        (action, checker),
        (checker, updater_action, expr(condition)),
        (
            checker,
            action,
            ~expr(condition) & expr(f"action_attempts <= {action_attempts_limit}"),
        ),
        (checker, assistant_action, ~expr(condition)),
    ]


def application(
    db: LancedbDBConnection | None = None,
    reranker: Reranker | None = None,
    model: ModelName = MODEL,
    chat_history: list[MessageType] | None = None,
    table_descriptions: list[TableDescription] = [],
    only_ai: bool = ONLY_AI,
    only_data: bool = ONLY_DATA,
    only_web: bool = ONLY_WEB,
    has_web: bool = HAS_WEB,
    app_id: str | None = None,
    username: str | None = None,
    project: str = "DreamAIRAG",
) -> Application:
    tracker = LocalTrackingClient(project=project)
    builder = (
        ApplicationBuilder()
        .with_actions(
            get_query,
            followup_or_not,
            router.bind(table_descriptions=table_descriptions),
            web_or_not,
            search_web,
            create_step_back_questions,
            search_lancedb.bind(reranker=reranker),
            create_search_response,
            evaluate_answer,
            update_chat_history,
            ask_assistant,
            terminate,
        )
        .with_transitions(
            ("get_query", "terminate", expr(f"steps[-1].step == '{RAGRoute.TERMINATE}'")),
            ("get_query", "search_web", expr(f"steps[-1].step == '{RAGRoute.WEB}'")),
            (
                "get_query",
                "followup_or_not",
                expr(f"steps[-1].step == '{RAGRoute.FOLLOWUP_OR_NOT}'"),
            ),
            ("get_query", "router", expr(f"steps[-1].step == '{RAGRoute.ROUTER}'")),
            (
                ["get_query", "followup_or_not", "router", "web_or_not"],
                "ask_assistant",
                expr(f"steps[-1].step == '{RAGRoute.ASSISTANT}'"),
            ),
            ("followup_or_not", "router"),
            ("router", "ask_assistant", expr(f"steps[-1].step == '{RAGRoute.MENU}'")),
            ("router", "web_or_not", expr(f"steps[-1].step == '{RAGRoute.WEB_OR_NOT}'")),
            ("router", "create_step_back_questions"),
            ("web_or_not", "search_web"),
            (
                ["search_web", "search_lancedb"],
                "ask_assistant",
                expr("len(search_results) == 0"),
            ),
            ("create_step_back_questions", "search_lancedb"),
            (["search_web", "search_lancedb"], "create_search_response"),
            *action_loop(
                action="create_search_response",
                checker="evaluate_answer",
                condition="answer_evaluation.evaluation",
                updater_action="update_chat_history",
                assistant_action="ask_assistant",
            ),
            ("ask_assistant", "update_chat_history"),
            ("update_chat_history", "get_query"),
        )
        .with_tracker("local", project=project)
        .with_identifiers(app_id=app_id, partition_key=username)  # type: ignore
        .initialize_from(
            tracker,
            resume_at_next_action=True,
            default_entrypoint="get_query",
            default_state=dict(
                db=db,
                model=model,
                chat_history=chat_history or [],
                only_ai=only_ai,
                only_data=only_data,
                only_web=only_web,
                has_web=only_web or has_web,
                steps=[],
                search_results=[],
            ),
        )
    )
    app = builder.build()
    app.visualize(output_file_path="statemachine", include_conditions=True, format="png")
    return app


def run_app(app: Application, queries: str | list[str]) -> Application:
    if isinstance(queries, str):
        queries = (
            Path(queries).read_text().splitlines() if queries.endswith(".txt") else [queries]
        )
    for query in queries:
        inputs = {"query": query}
        logger.info(f"\nProcessing query: {query}")
        while True:
            step_result = app.step(inputs=inputs)
            if step_result is None:
                logger.error("Error: app.step() returned None")
                break
            action, result, _ = step_result
            logger.info(f"\nAction: {action.name}\n")
            logger.success(f"RESULT: {result}\n")
            if action.name == "terminate":
                break
            elif action.name in ["update_chat_history"]:
                break
    return app
