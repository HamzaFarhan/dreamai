from typing import Any, Self

from pydantic import BaseModel, Field

from dreamai.ai import (
    MessageType,
    assistant_message,
    merge_same_role_messages,
    system_message,
    user_message,
)


class Example(BaseModel):
    user: Any
    assistant: Any

    @property
    def messages(self) -> list[MessageType]:
        return [
            user_message(content=self.user),
            assistant_message(content=self.assistant),
        ]


class BadExample(Example):
    feedback: Any

    @property
    def messages(self) -> list[MessageType]:
        return super().messages + [user_message(content=self.feedback)]


class Prompt(BaseModel):
    system: str = ""
    examples: list[Example] = Field(default_factory=list)
    chat_history: list[MessageType] = Field(default_factory=list)

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
        messages.extend(self.chat_history)
        return messages

    @property
    def merged_messages(self) -> list[MessageType]:
        return merge_same_role_messages(messages=self.messages)

    @property
    def gpt_kwargs(self) -> dict[str, list[MessageType]]:
        return {"messages": self.messages}

    @property
    def claude_kwargs(self) -> dict[str, str | list[MessageType]]:
        return {
            "system": self.system,
            "messages": self.merged_messages[1:]
            if self.system
            else self.merged_messages,
        }

    @property
    def gemini_kwargs(self) -> dict[str, list[MessageType]]:
        return {"messages": self.merged_messages}

    @classmethod
    def from_messages(
        cls, messages: list[MessageType], is_chat_history: bool = False
    ) -> Self:
        if messages[0]["role"] == "system":
            system = messages[0]["content"]
            messages = messages[1:]
        else:
            system = ""
        if is_chat_history:
            return cls(system=system, chat_history=messages)
        examples = []
        current_example = {}
        for message in messages:
            role = message["role"]
            content = message["content"]
            if role == "user":
                if "feedback" in current_example:
                    examples.append(BadExample(**current_example))
                    current_example = {"user": content}
                elif "assistant" in current_example:
                    current_example["feedback"] = content
                else:
                    current_example["user"] = content
            elif role == "assistant":
                if "feedback" in current_example:
                    examples.append(
                        Example(
                            user=current_example["user"],
                            assistant=current_example["assistant"],
                        )
                    )
                    current_example = {
                        "user": current_example["feedback"],
                        "assistant": content,
                    }
                else:
                    current_example["assistant"] = content

        if "feedback" in current_example:
            examples.append(BadExample(**current_example))
        elif "assistant" in current_example:
            examples.append(Example(**current_example))

        return cls(system=system, examples=examples)
