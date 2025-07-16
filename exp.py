from functools import partial
from importlib.resources import files
from pathlib import Path

import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from dreamai.basic_toolset import add_current_time_instructions, task_result, user_interaction
from dreamai.history_processors import remove_retries, remove_used_tool_calls
from dreamai.toolsets import (
    AgentDeps,
    Toolset,
    drop_toolsets,
    fetch_toolset,
    list_available_toolsets,
    list_fetched_toolsets,
    prepare_toolsets,
)

load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)


def add_numbers(numbers: list[int | float]) -> int | float:
    """Add numbers"""
    return sum(numbers)


def calculate_average(numbers: list[int | float]) -> int | float:
    """Calculate the average of numbers"""
    return sum(numbers) / len(numbers)


def guess_number(number: int) -> str:
    """Guess a number"""
    if number < 8:
        raise ModelRetry("Number is too low")
    return "correct!"


numerical_ops_tools = [add_numbers, calculate_average, guess_number]


model = OpenAIModel("openai/gpt-4.1-nano", provider=OpenRouterProvider())
agent = Agent(
    model=model,
    instructions=[
        files("dreamai.prompts").joinpath("toolsets.md").read_text(),
        add_current_time_instructions,
        list_available_toolsets,
        list_fetched_toolsets,
    ],
    deps_type=AgentDeps,
    tools=[fetch_toolset, drop_toolsets] + numerical_ops_tools,
    output_type=[user_interaction, task_result],
    prepare_tools=prepare_toolsets,
    history_processors=[
        remove_retries,
        partial(remove_used_tool_calls, tool_names=["guess_number"], lifespan=2),
        partial(remove_used_tool_calls, tool_names=["fetch_toolset", "drop_toolsets"], lifespan=1),
    ],
    retries=10,
)

agent_deps = AgentDeps()
agent_deps.add_toolsets(Toolset(name="numerical_ops", tools=numerical_ops_tools))

if __name__ == "__main__":
    message_history_path = Path("message_history.json")
    message_history: list[ModelMessage] = (
        ModelMessagesTypeAdapter.validate_json(message_history_path.read_bytes())
        if message_history_path.exists()
        else []
    )
    task = input("> ") or "guess a number between 1 and 10 and tell me the result once you're correct"
    while True:
        result = agent.run_sync(user_prompt=task, deps=agent_deps, message_history=message_history)
        message_history = result.all_messages()
        task = input(f"{result.output}\n> ")
        if task.lower() in ["q", "quit", "exit"]:
            break
    message_history_path.write_bytes(result.all_messages_json())
