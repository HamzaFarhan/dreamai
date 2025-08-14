from datetime import datetime

from pydantic import BaseModel, Field


def add_current_date_instructions() -> str:
    return f"<current_date>{datetime.now().astimezone().strftime('%Y-%m-%d')}</current_date>\n"


def user_interaction(message: str) -> str:
    """
    Interacts with the user. Could be:
    - A question
    - A progress update
    - An assumption made that needs to be validated
    - A request for clarification
    - Anything else needed from the user to proceed

    Args:
        message: The message to display to the user.
    """
    return message


class TaskResult(BaseModel):
    """
    A task result.
    """

    message: str = Field(description="The final response to the user.")


def task_result(message: str) -> TaskResult:
    """Returns the final response to the user."""
    return TaskResult(message=message)


def scratch_pad(thoughts: str):
    """Put your internal thoughts here in between toolsets and tools"""
    pass
