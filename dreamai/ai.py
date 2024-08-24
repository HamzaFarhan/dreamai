import inspect
from enum import StrEnum
from typing import Any, Callable, Literal, Type

import instructor
from anthropic import Anthropic
from dotenv import load_dotenv
from google.generativeai import GenerativeModel
from langchain_core.messages import AnyMessage
from openai import OpenAI
from pydantic import BaseModel, create_model, validate_call

load_dotenv()


class ModelName(StrEnum):
    GPT = "gpt-4o-2024-08-06"
    GPT_MINI = "gpt-4o-mini"
    HAIKU = "claude-3-haiku-20240307"
    SONNET = "claude-3-5-sonnet-20240620"
    OPUS = "claude-3-opus-20240229"
    GEMINI_PRO = "gemini-1.5-pro-latest"
    GEMINI_PRO_EXP = "gemini-1.5-pro-exp-0801"
    GEMINI_FLASH = "gemini-1.5-flash-latest"


class Tool(BaseModel):
    tool_name: str


def convert_lc_messages(messages: AnyMessage | list[AnyMessage]) -> list[dict[str, Any]]:
    type_to_role = {"human": "user", "ai": "assistant"}

    if not isinstance(messages, list):
        messages = [messages]
    return [
        {"role": type_to_role[message.type], "content": message.content}
        for message in messages
    ]


def create_tool_model(func: Callable) -> Type[BaseModel]:
    sig = inspect.signature(func)
    fields = {}
    for name, parameter in sig.parameters.items():
        if parameter.annotation is not inspect.Parameter.empty and name != "return":
            is_required = parameter.default == inspect.Parameter.empty
            fields[name] = (
                parameter.annotation,
                ... if is_required else parameter.default,
            )
    fields["tool_name"] = (Literal[func.__name__], func.__name__)  # type: ignore
    model_name = "".join([s.title() for s in func.__name__.split("_")]) + "Tool"
    return create_model(model_name, __doc__=func.__doc__, __base__=Tool, **fields)


class ToolError(BaseModel):
    tool_name: str
    error: str


def run_tool(tool_model: Tool, tool_func: Callable, **kwargs) -> Any:
    print(f"Running tool: {tool_model.tool_name}")
    try:
        return tool_func(**tool_model.model_dump(exclude={"tool_name"}), **kwargs)
    except Exception as e:
        print(f"Error running tool: {tool_model.tool_name}, {e}")
        return ToolError(tool_name=tool_model.tool_name, error=str(e))


@validate_call
def create_creator(model: ModelName) -> instructor.Instructor:
    if model in [ModelName.GPT_MINI, ModelName.GPT]:
        return instructor.from_openai(OpenAI())
    elif model in [ModelName.HAIKU, ModelName.SONNET, ModelName.OPUS]:
        return instructor.from_anthropic(Anthropic())
    elif model in [
        ModelName.GEMINI_FLASH,
        ModelName.GEMINI_PRO,
        ModelName.GEMINI_PRO_EXP,
    ]:
        return instructor.from_gemini(GenerativeModel(model_name=model))
    else:
        raise ValueError(f"Model {model} not supported")
