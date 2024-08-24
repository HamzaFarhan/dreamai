from burr.core import State, action

from dreamai.dialog import Dialog, assistant_message, user_message
from dreamai.dialog_models import SourcedResponse, SourcedSentence
from dreamai.routing_actions import _query_to_response
from dreamai.settings import DialogSettings

dialog_settings = DialogSettings()

CHAT_HISTORY_LIMIT = dialog_settings.chat_history_limit
DIALOGS_FOLDER = dialog_settings.dialogs_folder


@action(
    reads=["model", "query", "chat_history"], writes=["assistant_response", "chat_history"]
)
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
    return {"assistant_response": response}, state.update(assistant_response=response).append(
        chat_history=user_message(content=state["query"])
    ).append(chat_history=assistant_message(content=response))


@action(
    reads=["model", "query", "search_results", "chat_history"],
    writes=["assistant_response", "chat_history"],
)
def create_search_response(state: State) -> tuple[dict, State]:
    dialog = Dialog.load(f"{DIALOGS_FOLDER}/sourced_rag_dialog.json")
    documents = state["search_results"]
    if isinstance(documents[0], dict) and "index" in documents[0]:
        documents = [
            {k: v for k, v in document.items() if k != "index"} for document in documents
        ]
    user = dialog.template.format(documents=documents, user_query=state["query"])
    try:
        response = _query_to_response(
            query=user,
            model=state["model"],
            dialog=dialog,
            response_model=SourcedResponse,
            chat_history=state.get("chat_history", None),
            validation_context={"num_documents": len(documents)},
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
    return {"assistant_response": str(response)}, state.update(
        assistant_response=response
    ).append(chat_history=user_message(content=user)).append(
        chat_history=assistant_message(content=str(response))
    )


@action(reads=["chat_history"], writes=[])
def terminate(state: State) -> tuple[dict[str, list[dict[str, str]]], State]:
    return {"chat_history": state["chat_history"]}, state
