from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dreamai.ai import ModelName


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="sai_settings.env", env_file_encoding="utf-8")


class CreatorSettings(Settings):
    model: ModelName = ModelName.GEMINI_FLASH
    temperature: float = 0.3
    max_tokens: int = 2048
    attempts: int = 4


class DialogSettings(Settings):
    dialogs_folder: str = "/home/hamza/dev/dreamai/dreamai/dialogs"
    default_template: str = "{}"
    default_dialog_version: float = 1.0
    chat_history_limit: int = Field(
        default=10, description="Send only the last N in 'messages' to the model."
    )


class DialogModelsSettings(Settings):
    max_sentence_components: int = Field(default=5, title="For SentenceComponents")
    max_step_back_questions: int = Field(default=3, title="For StepBackQuestions")
    max_response_sentences: int = Field(default=10, title="For SourcedResponse")


class RAGSettings(Settings):
    chunk_size: int = 800
    chunk_overlap: int = 200
    separators: list[str] = [
        r"#{1,6} ",
        r"```\n",
        r"\*{2,}",
        r"---+\n",
        r"__+\n",
        r"\n\n",
        r"\n",
    ]
    lance_uri: str = "lance/rag/"
    ems_model: str = "hkunlp/instructor-base"
    reranker: str = "answerdotai/answerai-colbert-small-v1"
    device: str = "cuda"
    text_field_name: str = "text"
    max_search_results: int = Field(
        default=5,
        description="The maximum number of results to get from the vector database or search engine.",
    )


class RAGAppSettings(Settings):
    router: str = "router"
    assistant: str = "assistant"
    web_or_not: str = "web_or_not"
    web: str = "web"
    terminate: str = "terminate"
    default_confidence: float = 1.0
    route_confidence_threshold: float = 0.6
    assistant_confidence_threshold: float = 0.4
    terminators: list[str] = ["exit", "quit", "q"]
