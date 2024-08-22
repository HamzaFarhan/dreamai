from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    ValidationInfo,
    create_model,
    field_validator,
)

from dreamai.settings import DialogModelsSettings
from dreamai.utils import to_camel

settings = DialogModelsSettings()

MAX_SENTENCE_COMPONENTS = settings.max_sentence_components
MAX_STEP_BACK_QUESTIONS = settings.max_step_back_questions
MAX_RESPONSE_SENTENCES = settings.max_response_sentences
ASSERTION_CATEGORIES = Literal[
    "Presentation Format",
    "Example Demonstration",
    "Workflow Description",
    "Count",
    "Inclusion",
    "Exclusion",
    "Qualitative Assessment",
    "Other",
]


def validate_sentence_components(
    x: list[str], max_components: int = MAX_SENTENCE_COMPONENTS
) -> list[str]:
    return list(set(x[:max_components]))


class SentenceComponents(BaseModel):
    noun: Annotated[list[str], AfterValidator(validate_sentence_components)]
    subject: Annotated[list[str], AfterValidator(validate_sentence_components)]
    object: Annotated[list[str], AfterValidator(validate_sentence_components)]
    verb: Annotated[list[str], AfterValidator(validate_sentence_components)]
    adjective: Annotated[list[str], AfterValidator(validate_sentence_components)]


class StepBackQuestions(BaseModel):
    questions: list[str] = Field(..., min_length=1, max_length=MAX_STEP_BACK_QUESTIONS)


class AssertionConcept(BaseModel):
    concept: str
    category: ASSERTION_CATEGORIES
    source: str


class TableDescription(BaseModel):
    name: str
    description: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str, info: ValidationInfo) -> str:
        v = to_camel(to_camel(v.strip(), sep="_"), sep=" ")
        context = info.context
        if context is None:
            return v
        if v in context.get("names", []):
            return str(uuid4())
        return v


class SourcedSentence(BaseModel):
    sentence: str
    sources: list[int] = Field(
        default_factory=lambda: [-1], description="The source document indices."
    )

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: list[int], info: ValidationInfo) -> list[int]:
        context = info.context
        if context is None:
            return v
        num_documents = context.get("num_documents", 0)
        valid_sources = []
        for source in v:
            if source < -1 or source >= num_documents:
                valid_sources.append(-1)
            else:
                valid_sources.append(source)
        return valid_sources

    def __str__(self) -> str:
        return f"{self.sentence} {self.sources}"


class SourcedResponse(BaseModel):
    sentences: list[SourcedSentence] = Field(
        min_length=1, max_length=MAX_RESPONSE_SENTENCES
    )

    def __str__(self) -> str:
        if len(self.sentences) == 1:
            return self.sentences[0].sentence
        else:
            return "\n".join(f"- {sentence}" for sentence in self.sentences)


def create_response_with_confidence_model(
    response_type: list | type, response_value: Any | None = None
) -> type[BaseModel]:
    if isinstance(response_type, list):
        response_type = Literal[*response_type]  # type: ignore
    return create_model(
        "ResponseWithConfidence",
        response=(response_type, response_value or ...),
        confidence=(float, Field(ge=0.0, le=1.0)),
        __base__=BaseModel,
    )
