import asyncio
from typing import Literal

from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel, field_validator
from pydantic_ai import ModelRetry
from pydantic_ai.direct import model_request
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelRequestPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.tools import ToolDefinition

load_dotenv()


def camel_to_snake(name: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in name]).lstrip("_")


def get_weather(
    city: str, day: Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
) -> str:
    return f"The weather in {city} on {day} is sunny."


class GetWeather(BaseModel):
    """Get current temperature for provided city at day"""

    city: str
    day: Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    @field_validator("day")
    @classmethod
    def validate_day(
        cls, v: Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    ) -> Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        if v == "monday":
            raise ModelRetry("Monday is not a valid day right now. try some other day and let the user know")
        return v


tools = {"get_weather": {"func": get_weather, "model": GetWeather}}


class FailedToolCall(BaseModel):
    tool_name: str
    error: str


async def main():
    user_prompt = "what is the weather in Tokyo on Monday and in London on Tuesday?"
    messages: list[ModelMessage] = [ModelRequest.user_text_prompt(user_prompt)]
    attempts = 0
    tries = 5
    while attempts < tries:
        try:
            for message in messages:
                print(message)
            print("------------")
            model_response = await model_request(
                "google-gla:gemini-2.5-flash",
                messages=messages,
                model_request_parameters=ModelRequestParameters(
                    function_tools=[
                        ToolDefinition(
                            name=camel_to_snake(GetWeather.__name__),
                            description=GetWeather.__doc__,
                            parameters_json_schema=GetWeather.model_json_schema(),
                        )
                    ],
                    allow_text_output=True,
                ),
            )
            logger.success(f"Model response: {model_response}\n------------\n")
            num_failed = 0
            return_parts: list[ModelRequestPart] = []
            for part in model_response.parts:
                if isinstance(part, ToolCallPart) and (tool := tools.get(part.tool_name)):
                    try:
                        tool_model = tool["model"](**part.args)  # type: ignore
                        result = tool["func"](**tool_model.model_dump())  # type: ignore
                        print(result, "\n------------\n")  # type: ignore

                    except ModelRetry as e:
                        num_failed += 1
                        logger.warning(f"Tool {part.tool_name} failed: {e.message}")
                        result = e.message
                    except Exception as e:
                        raise e
                    return_parts.append(
                        ToolReturnPart(tool_name=part.tool_name, content=result, tool_call_id=part.tool_call_id)
                    )
            messages.append(ModelRequest(parts=return_parts))
            if num_failed == 0:
                break
            attempts += 1
        except Exception as e:
            attempts += 1
            logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
