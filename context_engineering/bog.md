# Context Engineering Using History Processors in Pydantic AI

### This is the first blog in series about Context Engineering using Pydantic AI.

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

```python
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