from burr.core import Application, ApplicationBuilder, expr
from burr.tracking import LocalTrackingClient
from lancedb.db import DBConnection as LancedbDBConnection
from lancedb.rerankers import Reranker

from dreamai.ai import ModelName
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
from dreamai.settings import CreatorSettings, RAGAppSettings

creator_settings = CreatorSettings()
rag_app_settings = RAGAppSettings()

MODEL = creator_settings.model
ONLY_DATA = rag_app_settings.only_data
HAS_WEB = rag_app_settings.has_web
ROUTER = rag_app_settings.router
ASSISTANT = rag_app_settings.assistant
WEB_OR_NOT = rag_app_settings.web_or_not
WEB = rag_app_settings.web
TERMINATE = rag_app_settings.terminate
UPDATE_CHAT_HISTORY = rag_app_settings.update_chat_history
ACTION_ATTEMPTS_LIMIT = rag_app_settings.action_attempts_limit


def application(
    db: LancedbDBConnection,
    reranker: Reranker | None = None,
    model: ModelName = MODEL,
    table_descriptions: list[TableDescription] = [],
    only_data: bool = ONLY_DATA,
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
            ("get_query", "terminate", expr(f"steps[-1].step == '{TERMINATE}'")),  # type: ignore
            ("get_query", "search_web", expr(f"steps[-1].step == '{WEB}'")),  # type: ignore
            ("get_query", "followup_or_not"),
            (
                ["followup_or_not", "router", "web_or_not"],
                "ask_assistant",
                expr(f"steps[-1].step == '{ASSISTANT}'"),  # type: ignore
            ),
            ("followup_or_not", "router"),
            ("router", "web_or_not", expr(f"steps[-1].step == '{WEB_OR_NOT}'")),  # type: ignore
            ("router", "create_step_back_questions"),
            ("web_or_not", "search_web"),
            (
                ["search_web", "search_lancedb"],
                "ask_assistant",
                expr("len(search_results) == 0"),  # type: ignore
            ),
            ("create_step_back_questions", "search_lancedb"),
            (["search_web", "search_lancedb"], "create_search_response"),
            ("create_search_response", "evaluate_answer"),
            ("evaluate_answer", "update_chat_history", expr("answer_evaluation.evaluation")),
            (
                "evaluate_answer",
                "create_search_response",
                ~expr("answer_evaluation.evaluation")
                & expr(f"action_attempts <= {ACTION_ATTEMPTS_LIMIT}"),
            ),
            ("evaluate_answer", "ask_assistant", expr(f"steps[-1].step == '{ASSISTANT}'")),
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
                chat_history=[],
                only_data=only_data,
                has_web=has_web,
                steps=[],
                search_results=[],
            ),
        )
    )
    return builder.build()
