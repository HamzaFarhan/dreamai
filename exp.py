from dataclasses import dataclass

import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext

load_dotenv()
logfire.configure()
logfire.instrument_pydantic_ai()


@dataclass
class AgentDeps: ...


async def add_numbers(ctx:RunContext[AgentDeps], a: int, b: int) -> int:
    print(ctx.usage)
    """Add two numbers"""
    return a + b


agent = Agent(model="google-gla:gemini-2.5-flash", deps_type=AgentDeps, tools=[add_numbers])

agent_deps = AgentDeps()

result = agent.run_sync("What is 1 + 1?", deps=agent_deps)
for message in result.all_messages():
    print(message, "\n")
