from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

MAX_SENTENCE_COMPONENTS = 5
MAX_STEP_BACK_QUESTIONS = 3
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
