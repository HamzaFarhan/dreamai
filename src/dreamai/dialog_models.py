from typing import Annotated, Any, Literal, Self
from uuid import uuid4

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    ValidationInfo,
    create_model,
    field_validator,
    model_validator,
)

from dreamai.settings import DialogModelsSettings
from dreamai.utils import to_camel

settings = DialogModelsSettings()

MAX_SENTENCE_COMPONENTS = settings.max_sentence_components
MAX_STEP_BACK_QUESTIONS = settings.max_step_back_questions
MAX_RESPONSE_SENTENCES = settings.max_response_sentences
MAX_NON_SOURCED_FACTOR = settings.max_non_sourced_factor
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
    questions: list[str] = Field(..., min_length=1)

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, v: list[str]) -> list[str]:
        return list(set(v))[:MAX_STEP_BACK_QUESTIONS]


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
        v = "".join(c for c in v if c.isalnum() or c in ["_", "-", "."])
        context = info.context
        if context is None:
            return v
        if v in context.get("names", []):
            return str(uuid4())
        return v


class SourcedSentence(BaseModel):
    text: str
    sources: list[int] = Field(
        default_factory=lambda: [-1], description="The source document indices."
    )

    @model_validator(mode="after")
    def validate_sources(self, info: ValidationInfo) -> Self:
        self._source_docs = []
        self.sources = self.sources or [-1]
        context = info.context
        if context is None:
            return self
        documents = context.get("documents", 0)
        self.sources = list(
            dict.fromkeys(
                -1 if source < -1 or source >= len(documents) else source
                for source in self.sources
            )
        )
        self._source_docs = [documents[source] for source in self.sources if source != -1]
        return self

    def __str__(self) -> str:
        # return f"{self.text} {self.sources}"
        return self.text


class SourcedResponse(BaseModel):
    sentences: list[SourcedSentence] = Field(min_length=1, max_length=MAX_RESPONSE_SENTENCES)

    @model_validator(mode="after")
    def validate_sources(self, info: ValidationInfo) -> Self:
        context = info.context or {}
        max_non_sourced_factor = context.get("max_non_sourced_factor", MAX_NON_SOURCED_FACTOR)
        non_sourced_sentences = [
            sentence for sentence in self.sentences if sentence.sources == [-1]
        ]
        self._sure = len(non_sourced_sentences) <= max_non_sourced_factor * len(self.sentences)
        self._source_docs = [sentence._source_docs for sentence in self.sentences]
        return self

    def __str__(self) -> str:
        res = "\n".join(f"- {sentence}" for sentence in self.sentences).strip()
        if len(self.sentences) == 1:
            res = res[2:]
        return res


class EvalWithReasoning(BaseModel):
    evaluation: bool
    reasoning: str


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
