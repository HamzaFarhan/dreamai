from functools import partial
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.messages import ModelMessagesTypeAdapter

from dreamai.history_processors import ToolEdit, edit_tool_return_part, edit_used_tools

load_dotenv()


MODULE_DIR = Path(__file__).parent
DATA_DIR = MODULE_DIR.joinpath("data")


async def read_file(file_path: str) -> str:
    """Reads a file and returns its content."""
    return DATA_DIR.joinpath(Path(file_path).name).read_text()


async def get_weather(city: str) -> str:
    """Gets the weather for a given city."""
    weather_map = {"NYC": "sunny", "LA": "raining", "London": "cloudy"}
    try:
        return weather_map[city]
    except KeyError:
        raise ModelRetry(f"{city} not found in weather map. Available cities: {weather_map.keys()}")


async def calculate_sum(numbers: list[int | float]) -> int | float:
    """Calculates the sum of a list of numbers."""
    return sum(numbers)


async def calculate_difference(n1: int | float, n2: int | float) -> int | float:
    """Calculates the difference between two numbers."""
    return n1 - n2


def list_data_files() -> str:
    return f"Available data files: {', '.join([f.name for f in DATA_DIR.iterdir() if f.is_file()])}"


truncate_tool_return = ToolEdit(
    edit_func=partial(
        edit_tool_return_part,
        content="[Truncated to save tokens] You can call the tool again if you need this output.",
        thresh=None,
    ),
    lifespan=3,
)

agent = Agent(
    model="google-gla:gemini-2.5-flash",
    instructions=list_data_files,
    tools=[read_file, get_weather, calculate_sum, calculate_difference],
    history_processors=[
        partial(
            edit_used_tools,
            tools_to_edit_funcs={"read_file": truncate_tool_return},
        )
    ],
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
