from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dreamai.ai import ModelName

DEV_DIR = "/home/hamza/dev"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="sai_settings.env", env_file_encoding="utf-8")


class CreatorSettings(Settings):
    model: ModelName = ModelName.GPT_MINI
    temperature: float = 0.3
    max_tokens: int = 2048
    attempts: int = 4


class DialogSettings(Settings):
    dialogs_folder: str = f"{DEV_DIR}/dreamai/src/dreamai/dialogs"
    default_template: str = "{}"
    default_dialog_version: float = 1.0
    chat_history_limit: int = Field(
        default=10, description="Send only the last N in 'messages' to the model."
    )


class DialogModelsSettings(Settings):
    max_sentence_components: int = Field(default=5, title="For SentenceComponents")
    max_step_back_questions: int = Field(default=3, title="For StepBackQuestions")
    max_response_sentences: int = Field(default=10, title="For SourcedResponse")
    max_non_sourced_factor: float = Field(
        default=0.5,
        description="The maximum percentage of the sentences that can be non-sourced.",
    )


class RAGSettings(Settings):
    chunk_size: int = 800
    chunk_overlap: int = 200
    min_full_text_size: int = 10_000
    separators: list[str] = [r"#{1,6}\s+", r"\*\*.*?\*\*", r"---", r"\n\n", r"\.\s+", r"\n"]
    lance_uri: str = "lance/rag/"
    ems_model: str = "hkunlp/instructor-base"
    reranker: str = "answerdotai/answerai-colbert-small-v1"
    # reranker: str = ""
    device: str = "cuda"
    text_field_name: str = "text"
    sample_text_limit: int = 300_000
    max_search_results: int = Field(
        default=5,
        description="The maximum number of results to get from the vector database or search engine.",
    )


class RAGRoute(StrEnum):
    ROUTER = "router"
    MENU = "menu"
    ASSISTANT = "assistant"
    FOLLOWUP_OR_NOT = "followup_or_not"
    WEB_OR_NOT = "web_or_not"
    WEB = "web"
    TERMINATE = "terminate"


class RAGAppSettings(Settings):
    only_ai: bool = False
    only_data: bool = False
    only_web: bool = False
    has_web: bool = False
    default_confidence: float = 1.0
    step_confidence_threshold: float = 0.6
    non_assistant_confidence_threshold: float = 0.4
    terminators: list[str] = ["exit", "quit", "q"]
    action_attempts_limit: int = 3


class ModalSettings(Settings):
    lance_dir: str = f"{DEV_DIR}/lance/"
    model: ModelName = ModelName.GPT_MINI
