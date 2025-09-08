# Smart Context Engineering with Pydantic AI - Part 1: History Processing for Long-Running Tasks

### This is the first blog in series about Context Engineering with Pydantic AI.

As we know by now, an agent is only as good as the context it is given.  
The first trick every AI Engineer learns is adding a `<current_date></current_date>` tag to the prompt/context because every model has its own knowledge cutoff date.  
System prompt, instructions, user prompt, message history, tool definitions etc. are all part of the context. And manipulating or curating any of these is called `Context Engineering`.  
In this blog, we will be manipulating the message history using `history_processors` in Pydantic AI.  
This is not intended to be a Pydantic AI tutorial, for that you can quickly go through their excellent [documentation](https://ai.pydantic.dev/). But you would be able to follow along regardless.

## Agent

Let's start off with a basic agent with some tools.  
We get the user prompt and we load and save the message history as we go.  
We also show the usage of the run.  
Entering `exit`, `quit`, `q` will end the run.  

```python title="heroes.py"
from enum import StrEnum
from pathlib import Path
from textwrap import dedent

from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.messages import ModelMessagesTypeAdapter

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


agent = Agent(
    model="google-gla:gemini-2.5-flash",
    instructions=(
        "You are a vigilant squad commander guiding heroes in the war against alien invaders, "
        "always decisive, mission-focused, and alert to threats."
    ),
    tools=[read_code_of_conduct, check_weapon_stock, arm_weapon_system, list_squad_members, issue_alien_warning],
    retries=3,
)

if __name__ == "__main__":
    res = None
    message_history_path = MODULE_DIR.joinpath("message_history.json")
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
```

### Instructions (previously known as `system_prompt`):

"You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats."

### Tools:

- `read_code_of_conduct`: Read the code of conduct for the heroes.
- `check_weapon_stock`: Check the stock of a weapon.
- `arm_weapon_system`: Arm the weapon system.
- `list_squad_members`: List the squad members.
- `issue_alien_warning`: Issue an alien warning.

## Simple Prompt

```zsh
uv run context_engineering/heroes.py

> list all the heroes in our squad

============
RunUsage(input_tokens=1134, output_tokens=89, details={'thoughts_tokens': 63, 'text_prompt_tokens': 1134}, requests=2, tool_calls=1)
============

Squad members: Aegis, Nova, Quark, Valkyr.
> q
```

### Message History JSON

This is what we have in the `message_history.json` file.

```json
[
    {
        "parts": [
            {
                "content": "list all the heroes in our squad",
                "timestamp": "2025-09-07T21:47:29.544777Z",
                "part_kind": "user-prompt"
            }
        ],
        "instructions": "You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.",
        "kind": "request"
    },
    {
        "parts": [
            {
                "tool_name": "list_squad_members",
                "args": {},
                "tool_call_id": "pyd_ai_2dfaa46381a446119a5e8787317c37e5",
                "part_kind": "tool-call"
            }
        ],
        "usage": {
            "input_tokens": 543,
            "cache_write_tokens": 0,
            "cache_read_tokens": 0,
            "output_tokens": 76,
            "input_audio_tokens": 0,
            "cache_audio_read_tokens": 0,
            "output_audio_tokens": 0,
            "details": {
                "thoughts_tokens": 63,
                "text_prompt_tokens": 543
            }
        },
        "model_name": "gemini-2.5-flash",
        "timestamp": "2025-09-07T21:47:31.929876Z",
        "kind": "response",
        "provider_name": "google-gla",
        "provider_details": {
            "finish_reason": "STOP"
        },
        "provider_response_id": "c_29aJyrN-j_nsEPsJ67kQM"
    }
]
```

### Message History Objects

If we hadn't used the `ModelMessagesTypeAdapter` and had just printed out `res.all_messages()`, we would have seen the following.

```python
[
    # User request
    ModelRequest(
        parts=[
            UserPromptPart(
                content='list all the heroes in our squad',
                timestamp=datetime.datetime(2025, 9, 7, 21, 47, 29, 544777, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI response - list squad members
    ModelResponse(
        parts=[
            ToolCallPart(
                tool_name='list_squad_members',
                args={},
                tool_call_id='pyd_ai_2dfaa46381a446119a5e8787317c37e5'
            )
        ],
        usage=RequestUsage(
            input_tokens=543,
            output_tokens=76,
            details={'thoughts_tokens': 63, 'text_prompt_tokens': 543}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 21, 47, 31, 929876, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='c_29aJyrN-j_nsEPsJ67kQM'
    ),
    # Tool return - squad member list
    ModelRequest(
        parts=[
            ToolReturnPart(
                tool_name='list_squad_members',
                content=['Aegis', 'Nova', 'Quark', 'Valkyr'],
                tool_call_id='pyd_ai_2dfaa46381a446119a5e8787317c37e5',
                timestamp=datetime.datetime(2025, 9, 7, 21, 47, 31, 932012, tzinfo=TzInfo(UTC))
            )
        ],
        instructions='You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.'
    ),
    # AI final response
    ModelResponse(
        parts=[
            TextPart(content='Squad members: Aegis, Nova, Quark, Valkyr.')
        ],
        usage=RequestUsage(
            input_tokens=591,
            output_tokens=13,
            details={'text_prompt_tokens': 591}
        ),
        model_name='gemini-2.5-flash',
        timestamp=datetime.datetime(2025, 9, 7, 21, 47, 32, 745208, tzinfo=TzInfo(UTC)),
        provider_name='google-gla',
        provider_details={'finish_reason': 'STOP'},
        provider_response_id='dP29aOfNLNnrnsEPvvSc8Aw'
    )
]
```

As you can see, we end up with a list of alternating `ModelRequest` and `ModelResponse` objects.  
You may be used to working with a list of dicts like this:

```python
[
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
]
```

But in Pydantic AI, we have well-defined, type-safe objects.

## More Tokens

Let's continue the conversation. Remember, `message_history` always gets loaded and saved.

```zsh
uv run context_engineering/heroes.py
> what is point 18 in our code of conduct?

============
RunUsage(input_tokens=1590, cache_read_tokens=698, output_tokens=34, details={'text_prompt_tokens': 1590, 'cached_content_tokens': 698, 'text_cache_tokens': 698}, requests=2, tool_calls=1)
============

Point 18 in the Code of Conduct states: "Meet mission deadlines and uphold quality standards."
> q
```

The whole code of conduct was loaded into our context using the `read_code_of_conduct` tool.

## ALERT!

```zsh
uv run context_engineering/heroes.py
> enemies detected on planet knd. send out a warning to the team and get 1 plasma rifle and 1 ion blaster ready        

============
RunUsage(input_tokens=4402, cache_read_tokens=2148, output_tokens=299, details={'thoughts_tokens': 202, 'text_prompt_tokens': 4402, 'cached_content_tokens': 2148, 'text_cache_tokens': 2148}, requests=4, tool_calls=3)
============

Alien activity detected on Planet KND. Threat level 3. Plasma rifle and Ion blaster allocated.
> q
```

Here's another thing we all know, the more tokens in our context, the longer the response time. And, it's easy to overwhelm the agent with too much context.  
Do we really need the tokens of the code of conduct in our context when we are attacking aliens?

## History Processors

We've finally reached the point where we can use [history_processors](https://ai.pydantic.dev/message-history/#processing-message-history) to edit the message history.  
We loaded and the code of conduct when we needed it. We no longer need it in our context. But I would argue that it's useful to know that we did need it at one point.  
So we won't delete the actual tool call from the message history, just the tool return value.

```python title="processed_heroes.py"
from collections import defaultdict
from collections.abc import Callable
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import Concatenate, ParamSpec

from dotenv import load_dotenv
from heroes import (
    arm_weapon_system,
    check_weapon_stock,
    issue_alien_warning,
    list_squad_members,
    read_code_of_conduct,
)
from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent
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

if __name__ == "__main__":
    res = None
    # I made sure to copy the message_history.json file to processed_message_history.json
    # So that we can continue the conversation from where we left off.
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
```

In Pydantic AI, `history_processors` are functions that take in the message history and return a new message history. These functions are applied to the message history in the order they are defined and before every step of the agent run.

```zsh
uv run context_engineering/processed_heroes.py
> how many weapons do we have left?

2025-09-08 06:13:41.124 | INFO     | __main__:edit_used_tools:96 - Edited parts: {'read_code_of_conduct': 2}

============
RunUsage(input_tokens=900, output_tokens=140, details={'thoughts_tokens': 130, 'text_prompt_tokens': 900}, requests=1)
============

Which weapon system are you asking about, hero?
> plasma

2025-09-08 06:13:52.393 | INFO     | __main__:edit_used_tools:96 - Edited parts: {'read_code_of_conduct': 2}
2025-09-08 06:13:54.559 | INFO     | __main__:edit_used_tools:96 - Edited parts: {'read_code_of_conduct': 2}

============
RunUsage(input_tokens=1867, cache_read_tokens=660, output_tokens=94, details={'thoughts_tokens': 64, 'text_prompt_tokens': 1867, 'cached_content_tokens': 660, 'text_cache_tokens': 660}, requests=2, tool_calls=1)
============

We have 12 plasma rifles left.
> q
```

Notice how our `input_tokens` went down significantly. Imagine if we had loaded an entire PDF with thousands of tokens, completely irrelevant to the current task.

### Message History JSON

Let's take a look at the `read_code_of_conduct` tool call and return.  
Before `history_processors`:

```json
[
    {
        "parts": [
            {
                "tool_name": "read_code_of_conduct",
                "args": {},
                "tool_call_id": "pyd_ai_9da20f22121c456196743506fd145ee4",
                "part_kind": "tool-call"
            }
        ],
        "usage": {
            "input_tokens": 618,
            "cache_write_tokens": 0,
            "cache_read_tokens": 0,
            "output_tokens": 14,
            "input_audio_tokens": 0,
            "cache_audio_read_tokens": 0,
            "output_audio_tokens": 0,
            "details": {
                "text_prompt_tokens": 618
            }
        },
        "model_name": "gemini-2.5-flash",
        "timestamp": "2025-09-07T21:59:10.624485Z",
        "kind": "response",
        "provider_name": "google-gla",
        "provider_details": {
            "finish_reason": "STOP"
        },
        "provider_response_id": "LgC-aNuBIuOznsEPrJz9gAw"
    },
    {
        "parts": [
            {
                "tool_name": "read_code_of_conduct",
                "content": "\n# Hero Squad Code of Conduct\n\n1. Always be battle-ready and arrive at mission briefings on time.  \n2. Respect fellow heroes, allies, and our base of operations.  \n3. Keep comms clear, professional, and mission-focused.  \n4. Complete your assigned quests and report results promptly.  \n5. Wear the appropriate armor or disguise for each mission.  \n6. Guard secret intel with your life—no leaks to alien spies.  \n7. Use squad gadgets and weapons responsibly.  \n8. Report strange signals, anomalies, or alien sightings ASAP.  \n9. Zero tolerance for betrayal, dishonor, or abandoning teammates.  \n10. Recharge only during designated rest cycles.  \n11. Follow all safety protocols in battle and training sims.  \n12. Own your mistakes—heroes take responsibility.  \n13. No disappearing without notifying Command.  \n14. Keep your gear and locker spotless.  \n15. Share intel and tactics in team huddles.  \n16. No holo-scrolling or personal calls mid-battle.  \n17. Secure approval before warp jumps or time off.  \n18. Meet mission deadlines and uphold quality standards.  \n19. Honor truth, courage, and loyalty at all times.  \n20. Breaking the Code may result in exile from the squad.  \n",
                "tool_call_id": "pyd_ai_9da20f22121c456196743506fd145ee4",
                "metadata": null,
                "timestamp": "2025-09-07T21:59:10.626637Z",
                "part_kind": "tool-return"
            }
        ],
        "instructions": "You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.",
        "kind": "request"
    }
]
```

After `history_processors`:

```json
[
    {
        "parts": [
            {
                "tool_name": "read_code_of_conduct",
                "content": "[Truncated to save tokens] You can call the tool again if you need this output.",
                "tool_call_id": "pyd_ai_9da20f22121c456196743506fd145ee4",
                "metadata": null,
                "timestamp": "2025-09-07T21:59:10.626637Z",
                "part_kind": "tool-return"
            }
        ],
        "instructions": "You are a vigilant squad commander guiding heroes in the war against alien invaders, always decisive, mission-focused, and alert to threats.",
        "kind": "request"
    }
]
```

## Next

If you've tried to develop agents that have many tools or have access to MCPs with multiple tools, you will know that once we go above 15-20 tools, the tool selection and tool parameter generation deteriorates significantly.  
In the next blog, we will develop an agent that can comfortably handle 100+ tools!