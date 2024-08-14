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


def load_system(system: str | Path) -> str:
    system = Path(str(system).strip())
    assert (
        system.suffix == ".txt" or system.suffix == ""
    ), "System must be a .txt file or a plain string"
    if not system.suffix == ".txt":
        return str(system)
    return system.read_text()


SystemType = Annotated[str, AfterValidator(load_system)]


class Prompt(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    system: SystemType = ""
    examples: list[Example | BadExample] = Field(default_factory=list)
    chat_history: list[MessageType] = Field(default_factory=list)
    version: float = DEFAULT_VERSION
    description: str = ""
    original_system: SystemType = ""
    change_history: list[ChangeRecord] = Field(default_factory=list)
    save_folder: str = str(Path.cwd())

    @model_validator(mode="after")
    def validate_not_empty(self) -> Self:
        assert (
            self.system or self.examples or self.chat_history
        ), "Prompt must have a system, examples, or chat history"
        return self

    @model_validator(mode="after")
    def validate_original_system(self) -> Self:
        self.original_system = self.original_system or self.system
        return self

    @property
    def name(self) -> str:
        return f"{self.id}_{self.version}"

    def format(self, **kwargs):
        self.system = self.system.format(**kwargs)

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
            return cls(system=messages[0]["content"], chat_history=messages[1:])
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

    def add_user_message(self, content: Any) -> None:
        self.chat_history.append(user_message(content=content))

    def add_assistant_message(self, content: Any) -> None:
        self.chat_history.append(assistant_message(content=content))

    @property
    def messages(self) -> list[MessageType]:
        messages = []
        if self.system:
            messages.append(system_message(content=self.system))
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

    @property
    def gpt_kwargs(
        self, model: str = ModelName.GPT_MINI
    ) -> dict[str, str | list[MessageType]]:
        return {"model": model, "messages": self.messages}

    @property
    def claude_kwargs(
        self, model: str = ModelName.SONNET
    ) -> dict[str, str | list[MessageType]]:
        return {
            "model": model,
            "system": self.system,
            "messages": self.merged_messages[1:]
            if self.system
            else self.merged_messages,
        }

    @property
    def gemini_kwargs(self) -> dict[str, list[MessageType]]:
        return {"messages": self.merged_messages}

    def bump_version(self, new_version: float | None = None):
        if new_version is None:
            num_decimal_places = str(self.version)[::-1].find(".")
            new_version = round(
                self.version + 10**-num_decimal_places, num_decimal_places
            )
        self.version = cast(float, new_version)
        self.save()

    @validate_call
    def update_system(
        self,
        new_system: SystemType,
        new_version: float | None = None,
        description: str = "",
    ):
        if new_system == self.system:
            return
        current_version = self.version
        self.bump_version(new_version=new_version)
        diff = list(
            unified_diff(
                self.system.splitlines(keepends=True),
                new_system.splitlines(keepends=True),
                fromfile=f"v{current_version}",
                tofile=f"v{self.version}",
                n=DIFF_CONTEXT_LINES,
            )
        )
        self.change_history.append(
            ChangeRecord(
                from_version=current_version,
                to_version=self.version,
                description=description,
                diff="".join(diff),
            )
        )
        self.system = new_system
        self.description = description
        self.save()

    def reset_to_original(self):
        desc = "Reset to original system prompt"
        self.system = self.original_system
        new_version = DEFAULT_VERSION
        self.change_history.append(
            ChangeRecord(
                from_version=self.version,
                to_version=new_version,
                description=desc,
                diff="",
            )
        )
        self.version = new_version
        self.description = desc
        self.save()
