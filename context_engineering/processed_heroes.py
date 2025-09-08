from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from enum import StrEnum
from functools import partial
from pathlib import Path
from textwrap import dedent
from typing import Concatenate, ParamSpec

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequestPart,
    ModelResponsePart,
    ToolCallPart,
    ToolReturnPart,
)

load_dotenv()

MODULE_DIR = Path(__file__).parent


ARMORY_STOCK: dict[str, int] = {
    "plasma_rifle": 12,
    "ion_blaster": 7,
    "grav_grenade": 24,
    "shield_emitter": 5,
}


class Status(StrEnum):
    ACTIVE = "active"
    INJURED = "injured"
    ON_MISSION = "on_mission"


SQUAD_MEMBERS: dict[str, str] = {
    "Nova": Status.ACTIVE,
    "Aegis": Status.ACTIVE,
    "Valkyr": Status.INJURED,
    "Quark": Status.ON_MISSION,
}


def read_code_of_conduct() -> str:
    """Read the code of conduct for the heroes."""
    return dedent("""
# Hero Squad Code of Conduct

1. Always be battle-ready and arrive at mission briefings on time.  
2. Respect fellow heroes, allies, and our base of operations.  
3. Keep comms clear, professional, and mission-focused.  
4. Complete your assigned quests and report results promptly.  
5. Wear the appropriate armor or disguise for each mission.  
6. Guard secret intel with your life—no leaks to alien spies.  
7. Use squad gadgets and weapons responsibly.  
8. Report strange signals, anomalies, or alien sightings ASAP.  
9. Zero tolerance for betrayal, dishonor, or abandoning teammates.  
10. Recharge only during designated rest cycles.  
11. Follow all safety protocols in battle and training sims.  
12. Own your mistakes—heroes take responsibility.  
13. No disappearing without notifying Command.  
14. Keep your gear and locker spotless.  
15. Share intel and tactics in team huddles.  
16. No holo-scrolling or personal calls mid-battle.  
17. Secure approval before warp jumps or time off.  
18. Meet mission deadlines and uphold quality standards.  
19. Honor truth, courage, and loyalty at all times.  
20. Breaking the Code may result in exile from the squad.  
""")


def check_weapon_stock(weapon_name: str) -> int:
    """Return the available stock count for a weapon.

    Args:
        weapon_name (str): Case-insensitive weapon key (e.g., "plasma_rifle").

    Returns:
        int: Units available in the armory. Returns 0 if unknown.
    """
    key = weapon_name.strip().lower()
    return max(0, ARMORY_STOCK.get(key, 0))


def arm_weapon_system(weapon_name: str, units: int) -> bool:
    """Allocate weapon units to the squad if stock allows.

    Args:
        weapon_name (str): Case-insensitive weapon key (e.g., "ion_blaster").
        units (int): Number of units to allocate. Must be positive.

    Returns:
        bool: True if allocation succeeded, False otherwise.
    """
    if units <= 0:
        raise ModelRetry("units must be a positive integer")
    key = weapon_name.strip().lower()
    available = ARMORY_STOCK.get(key, 0)
    if available >= units:
        ARMORY_STOCK[key] = available - units
        return True
    return False


def list_squad_members(status: Status | None = None) -> list[str]:
    """List squad member names, optionally filtered by status.

    Args:
        status (Status | None): Filter by status (e.g., Status.ACTIVE, Status.INJURED, Status.ON_MISSION).
            If None, return all members.

    Returns:
        list[str]: Sorted list of member names matching the filter.
    """
    if status is None:
        return sorted(SQUAD_MEMBERS.keys())
    want = status.value.strip().lower()
    return sorted([name for name, st in SQUAD_MEMBERS.items() if st.lower() == want])


def issue_alien_warning(level: int, location: str) -> str:
    """Create a broadcast message for an alien threat warning.

    Args:
        level (int): Threat level from 1 to 5 where 5 is extreme.
        location (str): Sighting or engagement location.

    Returns:
        str: A formatted alert message suitable for broadcast.
    """

    labels = {1: "Info", 2: "Caution", 3: "Alert", 4: "Critical", 5: "Extreme"}
    if level not in labels:
        raise ModelRetry(f"Invalid level: {level}")
    label = labels[level]
    return f"[{label}] Alien activity detected at {location.strip()}. All units standby. Threat level {level}/5."


EditFuncParams = ParamSpec("EditFuncParams")
EditFunc = Callable[
    Concatenate[ToolCallPart | ToolReturnPart, EditFuncParams], ToolCallPart | ToolReturnPart | None
]


class ToolEdit(BaseModel):
    """Configuration for editing tool calls and returns in message history.

    This class defines how to edit tool interactions in the message history,
    including the edit function to apply and the lifespan for when to apply it.

    Attributes:
        edit_func: Function to apply to tool call or return parts for editing.
        lifespan: Number of messages or fraction of history length after which
            to apply the edit. Defaults to 3.
    """

    edit_func: EditFunc[...]
    lifespan: int | float = 3


def edit_used_tools(
    message_history: list[ModelMessage], tools_to_edit_funcs: dict[str, ToolEdit]
) -> list[ModelMessage]:
    """Apply editing functions to tool calls and returns based on their lifespan.

    This function applies custom editing functions to tool interactions in the message
    history once they exceed their specified lifespan, helping manage token usage
    by truncating or modifying old tool outputs.

    Args:
        message_history: List of ModelMessage objects representing the conversation history.
        tools_to_edit_funcs: Dictionary mapping tool names to ToolEdit configurations
            that specify how and when to edit each tool's interactions.

    Returns:
        Filtered list of ModelMessage objects with tool interactions edited according
        to their ToolEdit configurations.
    """
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
    """Edit tool call parts by replacing arguments with custom content.

    This function modifies tool call parts by replacing their arguments with
    custom content if the original arguments exceed a threshold length.
    Only affects ToolCallPart objects, ToolReturnPart objects are returned unchanged.

    Args:
        part: The tool call or return part to potentially edit.
        content: Custom content to replace the tool arguments with. If None,
            the part is removed entirely.
        thresh: Minimum length threshold for tool arguments. If None, always
            replaces content. Defaults to 200.

    Returns:
        Modified ToolCallPart with custom content, original part if below threshold,
        None if content is None, or original ToolReturnPart unchanged.
    """
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
    """Edit tool return parts by replacing content with custom content.

    This function modifies tool return parts by replacing their content with
    custom content if the original content exceeds a threshold length.
    Only affects ToolReturnPart objects, ToolCallPart objects are returned unchanged.

    Args:
        part: The tool call or return part to potentially edit.
        content: Custom content to replace the tool return content with. If None,
            the part is removed entirely.
        thresh: Minimum length threshold for tool return content. If None, always
            replaces content. Defaults to 200.

    Returns:
        Modified ToolReturnPart with custom content, original part if below threshold,
        None if content is None, or original ToolCallPart unchanged.
    """
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


truncate_tool_return = ToolEdit(
    edit_func=partial(
        edit_tool_return_part,
        content="[Truncated to save tokens] You can call the tool again if you need this output.",
        thresh=None,
    ),
    lifespan=2,
)

agent = Agent(
    model="google-gla:gemini-2.5-flash",
    instructions=(
        "You are a vigilant squad commander guiding heroes in the war against alien invaders, "
        "always decisive, mission-focused, and alert to threats."
    ),
    tools=[read_code_of_conduct, check_weapon_stock, arm_weapon_system, list_squad_members, issue_alien_warning],
    retries=3,
    history_processors=[
        partial(
            edit_used_tools,
            tools_to_edit_funcs={"read_code_of_conduct": truncate_tool_return},
        )
    ],
)

res = None
message_history_path = MODULE_DIR.joinpath("processed_message_history.json")
user_prompt = input("> ")

while True:
    res = agent.run_sync(
        user_prompt=user_prompt,
        output_type=str,
        message_history=ModelMessagesTypeAdapter.validate_json(message_history_path.read_bytes())
        if message_history_path.exists()
        else None,
    )
    message_history_path.write_bytes(res.all_messages_json())
    print(f"\n============\n{res.usage()}\n============\n")
    user_prompt = input(f"{res.output}\n> ")
    if user_prompt.lower() in ["exit", "quit", "q"]:
        break
