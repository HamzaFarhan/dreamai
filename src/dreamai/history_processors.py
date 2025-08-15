from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from typing import Concatenate, ParamSpec

from loguru import logger
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelRequestPart,
    ModelResponsePart,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)

EditFuncParams = ParamSpec("EditFuncParams")
EditFunc = Callable[
    Concatenate[ToolCallPart | ToolReturnPart, EditFuncParams], ToolCallPart | ToolReturnPart | None
]


def remove_retries(message_history: list[ModelMessage], keep_last_n: int = 1) -> list[ModelMessage]:
    if not isinstance(message_history[-1], ModelRequest):
        return message_history
    keep_last_n = min(len(message_history) - 1, max(0, keep_last_n))
    num_kept_retries: int = 0
    retry_tool_call_ids: list[str] = []
    successful_tools: set[str] = set()
    filtered_message_history: list[ModelMessage] = []
    for message in message_history[::-1]:
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                successful_tools.add(part.tool_name)
            if isinstance(part, RetryPromptPart) and part.tool_name in successful_tools:
                if num_kept_retries < keep_last_n:
                    num_kept_retries += 1
                else:
                    retry_tool_call_ids.append(part.tool_call_id)
                    continue
            if isinstance(part, ToolCallPart) and part.tool_call_id in retry_tool_call_ids:
                continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Skipped {len(retry_tool_call_ids)} retries")
    return filtered_message_history[::-1]


def remove_used_tools(
    message_history: list[ModelMessage], tool_names: list[str], lifespan: int | float = 3
) -> list[ModelMessage]:
    tools_to_remove: set[str] = set()
    filtered_message_history: list[ModelMessage] = []
    if isinstance(lifespan, float):
        lifespan = len(message_history) * lifespan
    num_skipped_parts: defaultdict[str, int] = defaultdict(int)
    for i, message in enumerate(message_history[::-1]):
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name in tool_names and i >= lifespan:
                tools_to_remove.add(part.tool_name)
            if (
                isinstance(part, (ToolCallPart, ToolReturnPart, RetryPromptPart))
                and part.tool_name in tools_to_remove
            ):
                num_skipped_parts[part.tool_name] += 1
                continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Skipped parts: {dict(num_skipped_parts)}")
    return filtered_message_history[::-1]


class ToolEdit(BaseModel):
    edit_func: EditFunc[...]
    lifespan: int | float = 3


def edit_used_tools(
    message_history: list[ModelMessage], tools_to_edit_funcs: dict[str, ToolEdit]
) -> list[ModelMessage]:
    tools_to_edit: dict[str, EditFunc[...]] = {}
    filtered_message_history: list[ModelMessage] = []
    num_edited_parts: defaultdict[str, int] = defaultdict(int)
    for i, message in enumerate(message_history[::-1]):
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if (
                isinstance(part, ToolReturnPart)
                and (tool_edit := tools_to_edit_funcs.get(part.tool_name)) is not None
            ):
                if isinstance(tool_edit.lifespan, float):
                    tool_edit.lifespan = len(message_history) * tool_edit.lifespan
                if i >= tool_edit.lifespan:
                    tools_to_edit[part.tool_name] = tool_edit.edit_func
            if isinstance(part, (ToolCallPart, ToolReturnPart)) and (
                (edit_func := tools_to_edit.get(part.tool_name)) is not None
            ):
                num_edited_parts[part.tool_name] += 1
                if (part := edit_func(part)) is None:
                    continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Edited parts: {dict(num_edited_parts)}")
    return filtered_message_history[::-1]


def edit_tool_call_part(
    part: ToolCallPart | ToolReturnPart, content: str | None, thresh: int | None = 200
) -> ToolCallPart | ToolReturnPart | None:
    if isinstance(part, ToolReturnPart):
        return part
    if content is None:
        return None
    tool_args = part.args_as_json_str()
    if not tool_args or (thresh is not None and len(tool_args) < thresh):
        return part
    return ToolCallPart(
        tool_name=part.tool_name, args=content, tool_call_id=part.tool_call_id, part_kind=part.part_kind
    )


def edit_tool_return_part(
    part: ToolCallPart | ToolReturnPart, content: str | None, thresh: int | None = 200
) -> ToolCallPart | ToolReturnPart | None:
    if isinstance(part, ToolCallPart):
        return part
    if content is None:
        return None
    return_content = part.model_response_str()
    if thresh is not None and len(return_content) < thresh:
        return part
    return ToolReturnPart(
        tool_name=part.tool_name,
        content=content,
        tool_call_id=part.tool_call_id,
        metadata=part.metadata,
        timestamp=part.timestamp,
        part_kind=part.part_kind,
    )


def add_reminder_since_tool_call(
    message_history: list[ModelMessage], tool_name: str, reminder: str, reminder_interval: int = 6
) -> list[ModelMessage]:
    if not isinstance(message_history[-1], ModelRequest):
        return message_history
    messages_since_tool = 0
    has_target_tool = False
    for message in message_history[::-1]:
        if has_target_tool := any(
            isinstance(part, ToolReturnPart) and part.tool_name == tool_name for part in message.parts
        ):
            messages_since_tool = 0
            break
        messages_since_tool += 1
        if messages_since_tool >= reminder_interval:
            break
    if (has_target_tool and messages_since_tool >= reminder_interval) or not has_target_tool:
        message_history.append(ModelRequest.user_text_prompt(reminder))
    return message_history
