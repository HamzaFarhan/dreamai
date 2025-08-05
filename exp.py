from dataclasses import dataclass

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ToolReturn

load_dotenv()


@dataclass
class AgentDeps:
    city: str


def temperature_celsius(ctx: RunContext[AgentDeps]) -> ToolReturn:
    """get the temperature in celsius for the user's city."""
    temp_map = {"New York": 21.0, "Paris": 19.0, "Tokyo": 22.0}
    city = ctx.deps.city
    return ToolReturn(
        return_value=temp_map.get(city, 20.0),
        content="waow kya nikala hai",
        metadata={f"{city}_temp_celsius": temp_map.get(city, 20.0)},
    )


agent = Agent(model="google-gla:gemini-2.5-flash", deps_type=AgentDeps, tools=[temperature_celsius])
deps = AgentDeps(city="New York")
res = agent.run_sync("whats the temp at my city?", deps=deps)
print(res)
print("\n-------------------------\n")
print(res.all_messages())
