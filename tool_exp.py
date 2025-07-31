from collections.abc import Callable
from pprint import pprint
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, TypeAdapter

load_dotenv()


def remove_title_from_schema(schema: dict[str, Any]) -> None:
    """
    Remove the 'title' keyword from JSON schema and contained property schemas.

    :param schema:
        The JSON schema to remove the 'title' keyword from.
    """
    for key, value in list(schema.items()):
        # Make sure not to remove parameters named title
        if key == "properties" and isinstance(value, dict) and "title" in value:
            for sub_val in value.values():  # type: ignore
                remove_title_from_schema(sub_val)  # type: ignore
        elif key == "title":
            del schema[key]
        elif isinstance(value, dict):
            remove_title_from_schema(value)  # type: ignore
        elif isinstance(value, list):
            for item in value:  # type: ignore
                if isinstance(item, dict):
                    remove_title_from_schema(item)  # type: ignore


def inline_pydantic_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively inline Pydantic model schemas by replacing $ref with actual schema.
    """
    if not isinstance(schema, dict):  # type: ignore
        return schema

    def resolve_ref(ref: str, defs: dict[str, Any]) -> dict[str, Any]:
        """Resolve a $ref to its actual schema."""
        if not ref.startswith("#/$defs/"):
            return {"type": "object"}  # Fallback for external refs

        def_name = ref.split("/")[-1]
        if def_name in defs:
            return defs[def_name]
        return {"type": "object"}  # Fallback if definition not found

    def process_schema(s: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
        """Process a schema dictionary, resolving all references."""
        if not isinstance(s, dict):  # type: ignore
            return s

        # Handle $ref
        if "$ref" in s:
            return resolve_ref(s["$ref"], defs)

        # Create a new dict to avoid modifying the input
        result = s.copy()

        # Handle arrays
        if "items" in result:
            result["items"] = process_schema(result["items"], defs)

        # Handle object properties
        if "properties" in result:
            for prop_name, prop_schema in result["properties"].items():
                result["properties"][prop_name] = process_schema(prop_schema, defs)

        # Handle anyOf (for Union types)
        if "anyOf" in result:
            result["anyOf"] = [
                process_schema(sub_schema, defs) for sub_schema in result["anyOf"]
            ]

        # Handle allOf (for inheritance)
        if "allOf" in result:
            result["allOf"] = [
                process_schema(sub_schema, defs) for sub_schema in result["allOf"]
            ]

        # Handle additionalProperties
        if "additionalProperties" in result:
            result["additionalProperties"] = process_schema(
                result["additionalProperties"], defs
            )

        # Handle propertyNames
        if "propertyNames" in result:
            result["propertyNames"] = process_schema(result["propertyNames"], defs)

        return result

    # Store definitions for later use
    definitions = schema.pop("$defs", {})

    # First, resolve any nested references in definitions
    resolved_definitions: dict[str, Any] = {}
    for def_name, def_schema in definitions.items():
        resolved_definitions[def_name] = process_schema(def_schema, definitions)

    # Process the main schema with resolved definitions
    result = process_schema(schema, resolved_definitions)

    # Remove any remaining definitions
    if "$defs" in result:
        del result["$defs"]

    return result


def to_tool(func: Callable[..., Any]) -> dict[str, Any]:
    func_schema: dict[str, Any] = {
        "type": "function",
        "name": func.__name__,
        "description": func.__doc__,
        "parameters": TypeAdapter(func).json_schema(),
    }
    pprint(func_schema)
    print("\n---------------------------\n")
    return func_schema
    remove_title_from_schema(func_schema)
    return inline_pydantic_schema(func_schema)


def camel_to_snake(name: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in name]).lstrip("_")


class Day(BaseModel):
    """A day of the week."""

    name: Literal[
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ]


def get_weather(day: Day, city: str = "paris") -> str:
    weather_map = {
        "monday": "It's sunny and warm.",
        "tuesday": "It's cloudy with a chance of rain.",
        "wednesday": "It's windy and cool.",
        "thursday": "It's rainy and chilly.",
        "friday": "It's sunny and hot.",
        "saturday": "It's overcast with light showers.",
        "sunday": "It's partly cloudy with a chance of thunderstorms.",
    }
    return weather_map.get(day.name, "Weather data not available for this day.")


class GetWeather(BaseModel):
    """Get current temperature for provided city at day"""

    city: str
    day: Literal[
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    ]

    # @field_validator("day")
    # @classmethod
    # def validate_day(
    #     cls,
    #     v: Literal[
    #         "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    #     ],
    # ) -> Literal[
    #     "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
    # ]:
    #     if v == "monday":
    #         raise ModelRetry(
    #             "Monday is not a valid day right now. try some other day and let the user know"
    #         )
    #     return v


client = OpenAI()

tools = [to_tool(get_weather)]

pprint(tools)
print("\n---------------------------\n")

response = client.responses.create(
    model="gpt-4.1-nano",
    input=[{"role": "user", "content": "What is the weather on sunday?"}],
    tools=tools,
)

print(response.output)
