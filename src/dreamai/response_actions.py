from copy import deepcopy
from pathlib import Path

from burr.core import State, action

from dreamai.dialog import Dialog, assistant_message, user_message
from dreamai.dialog_models import SourcedResponse, SourcedSentence
from dreamai.routing_actions import _query_to_response
from dreamai.settings import DialogSettings

dialog_settings = DialogSettings()

CHAT_HISTORY_LIMIT = dialog_settings.chat_history_limit
DIALOGS_FOLDER = dialog_settings.dialogs_folder


@action(reads=["model", "query", "chat_history"], writes=["assistant_response"])
def ask_assistant(state: State) -> tuple[dict, State]:
    try:
        response = _query_to_response(
            model=state["model"],
            query=state["query"],
            chat_history=state["chat_history"],
        )
    except Exception as e:
        print(f"Error in ask_assistant: {e}")
        response = "I'm sorry, but I encountered an error while processing your request. Could you please try again?"
    return {"assistant_response": response}, state.update(assistant_response=response)


@action(
    reads=["model", "query", "search_results", "chat_history"],
    writes=["assistant_response", "source_docs"],
)
def create_search_response(state: State) -> tuple[dict, State]:
    dialog = Dialog.load(path=str(Path(DIALOGS_FOLDER) / "sourced_rag_dialog.json"))
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
            validation_context={"documents": documents},
        )
    except Exception as e:
        print(f"Error in create_search_response: {e}")
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
    }, state.update(assistant_response=response).update(source_docs=response._source_docs)


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
