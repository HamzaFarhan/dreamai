from copy import deepcopy
from pathlib import Path
from typing import Any

from burr.core import State, action
from burr.visibility import trace
from instructor.client import T
from loguru import logger

from dreamai.ai import ModelName
from dreamai.dialog import Dialog, MessageType, assistant_message, user_message
from dreamai.dialog_models import SourcedResponse, SourcedSentence
from dreamai.settings import CreatorSettings, DialogSettings

creator_settings = CreatorSettings()
dialog_settings = DialogSettings()

MODEL = creator_settings.model
DIALOGS_FOLDER = dialog_settings.dialogs_folder


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
    response = creator.create(
        response_model=response_model, validation_context=validation_context, **creator_kwargs
    )
    return response


@action(
    reads=["model", "query", "chat_history", "bad_example"],
    writes=["assistant_response", "bad_example"],
)
def ask_assistant(state: State) -> tuple[dict, State]:
    dialog = Dialog(task=str(Path(DIALOGS_FOLDER) / "assistant_task.txt"))
    bad_example = state.get("bad_example", None)
    if bad_example:
        dialog.add_examples(deepcopy(bad_example))
        bad_example = None
    try:
        response = _query_to_response(
            model=state["model"],
            query=state["query"],
            dialog=dialog,
            chat_history=state.get("chat_history", None),
        )
    except Exception:
        logger.exception("Error in ask_assistant")
        response = "I'm sorry, but I encountered an error while processing your request. Could you please try again?"
    return {"assistant_response": response}, state.update(assistant_response=response).update(
        bad_example=bad_example
    )


@action(
    reads=["model", "query", "search_results", "chat_history"],
    writes=["assistant_response", "source_docs", "bad_example"],
)
def create_search_response(state: State) -> tuple[dict, State]:
    dialog = Dialog.load(path=str(Path(DIALOGS_FOLDER) / "sourced_rag_dialog.json"))
    bad_example = state.get("bad_example", None)
    if bad_example:
        dialog.add_examples(deepcopy(bad_example))
        bad_example = None
    documents = [
        {k: v for k, v in document.items() if k != "index"}
        for document in state["search_results"]
    ]
    user = dialog.template.format(documents=documents, user_query=state["query"])
    try:
        response = _query_to_response(
            query=user,
            model=state["model"],
            dialog=dialog,
            response_model=SourcedResponse,
            chat_history=state.get("chat_history", None),
            validation_context={
                "documents": [
                    {"name": document["name"], "index": document["index"]}
                    for document in state["search_results"]
                ]
            },
        )
    except Exception:
        logger.exception("Error in create_search_response")
        response = SourcedResponse(
            sentences=[
                SourcedSentence(
                    text="Sorry, I couldn't find an answer to your question. Please try again."
                )
            ]
        )
    return {
        "assistant_response": str(response),
        "source_docs": response._source_docs,
    }, state.update(assistant_response=str(response)).update(
        source_docs=response._source_docs
    ).update(bad_example=bad_example)


@action(reads=["query", "assistant_response"], writes=["chat_history"])
def update_chat_history(state: State) -> tuple[dict, State]:
    chat_history = deepcopy(state["chat_history"])
    user = user_message(content=state["query"])
    assistant = assistant_message(content=state["assistant_response"])
    return {"chat_history": chat_history + [user, assistant]}, state.append(
        chat_history=user
    ).append(chat_history=assistant)


@action(reads=["chat_history"], writes=[])
def terminate(state: State) -> tuple[dict[str, list[dict[str, str]]], State]:
    return {"chat_history": state["chat_history"]}, state
