import json
import os
from difflib import unified_diff
from pathlib import Path
from typing import Annotated, Any, Self, cast
from uuid import uuid4

from pydantic import AfterValidator, BaseModel, Field, model_validator, validate_call

from dreamai.ai import (
    MessageType,
    ModelName,
    assistant_message,
    merge_same_role_messages,
    system_message,
    user_message,
)

DEFAULT_TEMPLATE = "{}"
DEFAULT_VERSION = 1.0
DIFF_CONTEXT_LINES = 1


class Example(BaseModel):
    user: Any
    assistant: Any

    @property
    def messages(self) -> list[MessageType]:
        return [
            user_message(content=self.user),
            assistant_message(content=self.assistant),
        ]

    @classmethod
    def from_messages(cls, messages: list[MessageType]) -> Self:
        assert len(messages) == 2, "Example must have exactly 2 messages"
        assert (
            messages[0]["role"] == "user" and messages[1]["role"] == "assistant"
        ), "Example must have a user and assistant message"
        return cls(user=messages[0]["content"], assistant=messages[1]["content"])


class BadExample(Example):
    feedback: Any

    @property
    def messages(self) -> list[MessageType]:
        return super().messages + [user_message(content=self.feedback)]

    @classmethod
    def from_messages(cls, messages: list[MessageType]) -> Self:
        assert len(messages) == 3, "BadExample must have exactly 3 messages"
        assert (
            messages[0]["role"] == "user"
            and messages[1]["role"] == "assistant"
            and messages[2]["role"] == "user"
        ), "BadExample must have a user, assistant, and user message"
        return cls(
            user=messages[0]["content"],
            assistant=messages[1]["content"],
            feedback=messages[2]["content"],
        )


class ChangeRecord(BaseModel):
    from_version: float
    to_version: float
    diff: str
    description: str = ""


def load_str(string: str | Path) -> str:
    string_path = Path(str(string).strip())
    suffix = string_path.suffix.strip()
    if suffix == ".txt":
        return string_path.read_text()
    if suffix in [".json", ".py", ".yaml", ".yml"]:
        raise ValueError(
            f"String must be a .txt file or a plain string. Suffix received: {suffix}"
        )
    return str(string).strip()


Str = Annotated[str, AfterValidator(load_str)]


class Dialog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task: Str = ""
    template: Str = DEFAULT_TEMPLATE
    examples: list[Example | BadExample] = Field(default_factory=list)
    chat_history: list[MessageType] = Field(default_factory=list)
    version: float = DEFAULT_VERSION
    description: str = ""
    original_task: Str = ""
    original_template: Str = DEFAULT_TEMPLATE
    change_history: list[ChangeRecord] = Field(default_factory=list)
    save_folder: str = str(Path.cwd())

    @model_validator(mode="after")
    def validate_not_empty(self) -> Self:
        assert (
            self.task or self.examples or self.chat_history
        ), "Dialog must have a task, examples, or chat history"
        return self

    @model_validator(mode="after")
    def validate_originals(self) -> Self:
        self.original_task = self.original_task or self.task
        self.original_template = self.original_template or self.template
        return self

    @property
    def name(self) -> str:
        return f"{self.id}_{self.version}"

    def format_task(self, **kwargs):
        self.task = self.task.format(**kwargs)

    @classmethod
    def from_dump(cls, dump: dict[str, Any], include_chat_history: bool = True) -> Self:
        dump["examples"] = [
            BadExample(**example) if "feedback" in example else Example(**example)
            for example in dump.get("examples", [])
        ]
        if not include_chat_history:
            dump["chat_history"] = []
        return cls(**dump)

    @classmethod
    def from_messages(cls, messages: list[MessageType] | str | Path) -> Self:
        if isinstance(messages, (str, Path)):
            assert Path(messages).suffix == ".json", "Path must be a .json file"
            messages = cast(list[MessageType], json.loads(Path(messages).read_text()))
        if messages[0]["role"] == "system":
            return cls(task=messages[0]["content"], chat_history=messages[1:])
        return cls(chat_history=messages)

    def save(self) -> str:
        os.makedirs(self.save_folder, exist_ok=True)
        path = Path(self.save_folder) / f"{self.name}.json"
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=2)
        return str(path)

    @classmethod
    def load(cls, path: str, include_chat_history: bool = True) -> Self:
        assert (
            Path(path).suffix == ".json"
        ), "Path must be a .json file made by calling .save()"
        return cls.from_dump(
            json.loads(Path(path).read_text()),
            include_chat_history=include_chat_history,
        )

    def add_examples(
        self, examples: list[Example | BadExample] | Example | BadExample
    ) -> None:
        if not isinstance(examples, list):
            examples = [examples]
        self.examples.extend(examples)

    def add_messages(self, messages: list[MessageType] | MessageType) -> None:
        if not isinstance(messages, list):
            messages = [messages]
        self.chat_history.extend(messages)

    @property
    def messages(self) -> list[MessageType]:
        messages = []
        if self.task:
            messages.append(system_message(content=self.task))
        for example in self.examples:
            messages.extend(example.messages)
        if self.chat_history:
            if self.chat_history[0]["role"] == "system":
                messages.extend(self.chat_history[1:])
            else:
                messages.extend(self.chat_history)
        return messages

    @property
    def merged_messages(self) -> list[MessageType]:
        return merge_same_role_messages(messages=self.messages)

    def _add_user_query(
        self,
        messages: list[MessageType],
        user: str = "",
        template_data: dict | None = None,
    ) -> list[MessageType]:
        if user:
            messages.append(user_message(content=user))
        elif template_data:
            messages.append(user_message(content=self.template.format(**template_data)))
        return messages

    def gpt_kwargs(
        self,
        model: ModelName = ModelName.GPT_MINI,
        user: str = "",
        template_data: dict | None = None,
    ) -> dict[str, str | list[MessageType]]:
        return {
            "model": model,
            "messages": self._add_user_query(
                messages=self.messages, user=user, template_data=template_data
            ),
        }

    def claude_kwargs(
        self,
        model: ModelName = ModelName.SONNET,
        user: str = "",
        template_data: dict | None = None,
    ) -> dict[str, str | list[MessageType]]:
        messages = self._add_user_query(
            messages=self.merged_messages, user=user, template_data=template_data
        )
        return {
            "model": model,
            "system": self.task,
            "messages": messages[1:] if self.task else messages,
        }

    def gemini_kwargs(
        self, user: str = "", template_data: dict | None = None
    ) -> dict[str, list[MessageType]]:
        return {
            "messages": self._add_user_query(
                messages=self.merged_messages, user=user, template_data=template_data
            )
        }

    def bump_version(self, new_version: float | None = None):
        if new_version is None:
            num_decimal_places = str(self.version)[::-1].find(".")
            new_version = round(
                self.version + 10**-num_decimal_places, num_decimal_places
            )
        self.version = cast(float, new_version)
        self.save()

    @validate_call
    def update(
        self,
        new_task: Str = "",
        new_template: Str = DEFAULT_TEMPLATE,
        new_version: float | None = None,
        description: str = "",
    ):
        if not new_task and not new_template:
            return

        current_version = self.version
        self.bump_version(new_version=new_version)

        changes = []
        if new_task and new_task != self.task:
            task_diff = list(
                unified_diff(
                    self.task.splitlines(keepends=True),
                    new_task.splitlines(keepends=True),
                    fromfile=f"task_v{current_version}",
                    tofile=f"task_v{self.version}",
                    n=DIFF_CONTEXT_LINES,
                )
            )
            changes.append("".join(task_diff))
            self.task = new_task

        if new_template and new_template != self.template:
            template_diff = list(
                unified_diff(
                    self.template.splitlines(keepends=True),
                    new_template.splitlines(keepends=True),
                    fromfile=f"template_v{current_version}",
                    tofile=f"template_v{self.version}",
                    n=DIFF_CONTEXT_LINES,
                )
            )
            changes.append("".join(template_diff))
            self.template = new_template

        if changes:
            self.change_history.append(
                ChangeRecord(
                    from_version=current_version,
                    to_version=self.version,
                    description=description,
                    diff="\n".join(changes),
                )
            )
            self.description = description
            self.save()
