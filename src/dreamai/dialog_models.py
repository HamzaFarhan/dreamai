from typing import Annotated, Any, Literal, Self
from uuid import uuid4

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
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
MAX_THOUGHTS = settings.max_thoughts
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


class ThoughtStep(BaseModel):
    title: str
    content: str

    def __str__(self) -> str:
        return f"<{self.title}>\n{self.content}\n</{self.title}>"


class ThoughtProcess(BaseModel):
    task: str
    steps: list[ThoughtStep] = Field(min_length=1, max_length=MAX_THOUGHTS)
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "task": "How many words are in your response to this prompt?",
                    "steps": [
                        {
                            "title": "Addressing paradoxical query",
                            "content": "I'm working through a paradoxical question, which involves self-reference and determining the response length. Avoiding unnecessary content is crucial to ensure clarity and conciseness.",
                        },
                        {
                            "title": "Figuring out word count",
                            "content": "OK, let me see. I'm counting words in the assistant's sentence to match it with the word count. This approach seems interesting.",
                        },
                        {
                            "title": "Identifying word patterns",
                            "content": "I'm examining sentences with varying word counts, finding inconsistencies in some while confirming others. This helps determine the most accurate way to count words.",
                        },
                        {
                            "title": "Counting words",
                            "content": 'Okay, let me see. The sentence spans five words. Here\'s a concise tally: "This sentence has five words. Is 5 words. So the assistant can answer with "There are seven words."',
                        },
                        {
                            "title": "Clarifying response accuracy",
                            "content": "I'm analyzing various ways to specify the word count in responses, highlighting the need for consistent and clear communication. Progressing towards enhancing precise clarity.",
                        },
                    ],
                },
                {
                    "task": "What is the fourth word in your response to this prompt?",
                    "steps": [
                        {
                            "title": "Analyzing the instructions",
                            "content": "Taking a closer look at how to approach the task, which involves addressing a tricky question effectively.",
                        },
                        {
                            "title": "Assessing the response",
                            "content": "I'm trying to figure out what the assistant should say to accurately identify the fourth word in its response. It's tricky to pinpoint without context, but I'm considering phrasing like \"My 4th word in response is 'X'.\"",
                        },
                        {
                            "title": "Clarifying the task",
                            "content": "The assistant needs to determine the 4th word in its response after generating it, adhering to OpenAI's helpful, instruction-following, and hidden prompt policies.",
                        },
                        {
                            "title": "Organizing the response",
                            "content": "I'm gathering and analyzing potential responses for the 4th word in the assistant's message, considering different ways to present the word or provide an example sentence.",
                        },
                        {
                            "title": "Weighing options",
                            "content": 'I\'m thinking through the assistant\'s fourth word using different words like "alternatively" and "subsequently", and even revisiting previous answers to ensure the response aligns with the question.',
                        },
                        {
                            "title": "Identifying the response",
                            "content": "OK, let me see. The fourth word in the response is 'in'. This conclusion comes from examining the response text, noting that 'in' appears fourth.",
                        },
                    ],
                },
            ]
        }
    )

    def __str__(self) -> str:
        return f"<task>\n{self.task}\n</task>\n\n<thought_process>\n\n{'\n\n'.join(str(step) for step in self.steps)}\n\n</thought_process>"


class SourcedSentence(BaseModel):
    text: str
    sources: list[int] = Field(
        default_factory=lambda: [-1], description="The source document indices."
    )
    # thought_process: ThoughtProcess

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


class ThoughtfulResponse(BaseModel):
    thought_process: ThoughtProcess = Field(
        description="The thought process of the assistant."
    )
    response: str = Field(description="The actual response of the assistant.")

    def __str__(self) -> str:
        return f"{self.thought_process}\n\n<response>\n{self.response}\n</response>"


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
