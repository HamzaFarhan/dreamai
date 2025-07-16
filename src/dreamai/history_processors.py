from collections import defaultdict
from dataclasses import replace

from loguru import logger
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelRequestPart,
    ModelResponsePart,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)


def remove_retries(message_history: list[ModelMessage]) -> list[ModelMessage]:
    if not isinstance(message_history[-1], ModelRequest):
        return message_history
    retry_tool_call_ids: list[str] = []
    successful_tools: set[str] = set()
    filtered_message_history: list[ModelMessage] = []
    for message in message_history[::-1]:
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                successful_tools.add(part.tool_name)
            if isinstance(part, RetryPromptPart) and part.tool_name in successful_tools:
                retry_tool_call_ids.append(part.tool_call_id)
                continue
            if isinstance(part, ToolCallPart) and part.tool_call_id in retry_tool_call_ids:
                continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Skipped {len(retry_tool_call_ids)} retries")
    return filtered_message_history[::-1]


def remove_used_tool_calls(
    message_history: list[ModelMessage], tool_names: list[str], lifespan: int | float = 3
) -> list[ModelMessage]:
    tools_to_remove: set[str] = set()
    filtered_message_history: list[ModelMessage] = []
    if isinstance(lifespan, float):
        lifespan = len(message_history) * lifespan
    num_skipped_messages: defaultdict[str, int] = defaultdict(int)
    for i, message in enumerate(message_history[::-1]):
        filtered_parts: list[ModelRequestPart | ModelResponsePart] = []
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and part.tool_name in tool_names and i >= lifespan:
                tools_to_remove.add(part.tool_name)
            if (
                isinstance(part, (ToolCallPart, ToolReturnPart, RetryPromptPart))
                and part.tool_name in tools_to_remove
            ):
                num_skipped_messages[part.tool_name] += 1
                continue
            filtered_parts.append(part)
        if filtered_parts:
            filtered_message_history.append(replace(message, parts=filtered_parts))
    logger.info(f"Skipped messages: {dict(num_skipped_messages)}")
    return filtered_message_history[::-1]
