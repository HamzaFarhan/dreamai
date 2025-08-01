from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel


def fruit(name: str, color: str) -> dict[str, str]:
    """
    Returns a fruit with the given name and color.
    """
    return {"name": name, "color": color}


def vehicle(name: str, type: str) -> dict[str, str]:
    """
    Returns a vehicle with the given name and type.
    """
    return {"name": name, "type": type}


test_model = TestModel()
agent = Agent(test_model, output_type=[fruit, vehicle])
result = agent.run_sync("What is a banana?")
print([t.name for t in test_model.last_model_request_parameters.output_tools])
