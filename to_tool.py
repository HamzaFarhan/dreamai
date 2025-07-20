from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping, Sequence
from dataclasses import MISSING, dataclass, fields, is_dataclass
from enum import Enum
from functools import partial
from inspect import getdoc
from typing import Any, Literal, Optional, Union, cast, get_args, get_origin, get_type_hints

from docstring_parser import parse
from loguru import logger
from pydantic import BaseModel, Field, create_model


def _get_param_descriptions(method: Callable[..., Any]) -> tuple[str, dict[str, str]]:
    """
    Extracts parameter descriptions from the method's docstring using docstring_parser.

    :param method: The method to extract parameter descriptions from.
    :returns:
        A tuple including the short description of the method and a dictionary mapping parameter names to their
        descriptions.
    """
    docstring = getdoc(method)
    if not docstring:
        return "", {}

    parsed_doc = parse(docstring)
    param_descriptions: dict[str, str] = {}
    for param in parsed_doc.params:
        if not param.description:
            logger.warning(
                "Missing description for parameter '%s'. Please add a description in the component's "
                "run() method docstring using the format ':param %%s: <description>'. "
                "This description helps the LLM understand how to use this parameter." % param.arg_name
            )
        param_descriptions[param.arg_name] = param.description.strip() if param.description else ""
    return parsed_doc.short_description or "", param_descriptions


def _dataclass_to_pydantic_model(dc_type: Any) -> type[BaseModel]:
    """
    Convert a Python dataclass to an equivalent Pydantic model.

    :param dc_type: The dataclass type to convert.
    :returns:
        A dynamically generated Pydantic model class with fields and types derived from the dataclass definition.
        Field descriptions are extracted from docstrings when available.
    """
    _, param_descriptions = _get_param_descriptions(dc_type)
    cls = dc_type if isinstance(dc_type, type) else dc_type.__class__

    field_defs: dict[str, Any] = {}
    for field in fields(dc_type):
        f_type = field.type if isinstance(field.type, str) else _resolve_type(field.type)
        default = field.default if field.default is not MISSING else ...
        default = field.default_factory() if callable(field.default_factory) else default

        description = param_descriptions.get(field.name, f"Field '{field.name}' of '{cls.__name__}'.")
        field_defs[field.name] = (f_type, Field(default, description=description))

    model = create_model(cls.__name__, **field_defs)
    return model


def _resolve_type(_type: Any) -> Any:
    """
    Recursively resolve and convert complex type annotations, transforming dataclasses into Pydantic-compatible types.

    This function walks through nested type annotations (e.g., List, Dict, Union) and converts any dataclass types
    it encounters into corresponding Pydantic models.

    :param _type: The type annotation to resolve. If the type is a dataclass, it will be converted to a Pydantic model.
        For generic types (like List[SomeDataclass]), the inner types are also resolved recursively.

    :returns:
        A fully resolved type, with all dataclass types converted to Pydantic models
    """
    if is_dataclass(_type):
        return _dataclass_to_pydantic_model(_type)

    origin = get_origin(_type)
    args = get_args(_type)

    if origin is list:
        return list[_resolve_type(args[0]) if args else Any]  # type: ignore[misc]

    if origin is Sequence:
        return Sequence[_resolve_type(args[0]) if args else Any]  # type: ignore[misc]

    if origin is Union:
        return Union[tuple(_resolve_type(a) for a in args)]  # type: ignore[misc]

    if origin is dict:
        return dict[args[0] if args else Any, _resolve_type(args[1]) if args else Any]  # type: ignore[misc]

    return _type


def is_origin_union_type(origin: Any) -> bool:
    import sys

    if sys.version_info.minor >= 10:
        from types import UnionType  # type: ignore

        return origin in [Union, UnionType]

    return origin is Union


def get_json_type_for_py_type(arg: str) -> str:
    """
    Get the JSON schema type for a given type.
    :param arg: The type to get the JSON schema type for.
    :return: The JSON schema type.
    """
    # log_info(f"Getting JSON type for: {arg}")
    if arg in ("int", "float", "complex", "Decimal"):
        return "number"
    elif arg in ("str", "string"):
        return "string"
    elif arg in ("bool", "boolean"):
        return "boolean"
    elif arg in ("NoneType", "None"):
        return "null"
    elif arg in ("list", "tuple", "set", "frozenset"):
        return "array"
    elif arg in ("dict", "mapping"):
        return "object"

    # If the type is not recognized, return "object"
    return "object"


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
            result["anyOf"] = [process_schema(sub_schema, defs) for sub_schema in result["anyOf"]]

        # Handle allOf (for inheritance)
        if "allOf" in result:
            result["allOf"] = [process_schema(sub_schema, defs) for sub_schema in result["allOf"]]

        # Handle additionalProperties
        if "additionalProperties" in result:
            result["additionalProperties"] = process_schema(result["additionalProperties"], defs)

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


def get_json_schema_for_arg(type_hint: Any) -> Optional[dict[str, Any]]:
    # log_info(f"Getting JSON schema for arg: {t}")
    type_args = get_args(type_hint)
    # log_info(f"Type args: {type_args}")
    type_origin = get_origin(type_hint)
    # log_info(f"Type origin: {type_origin}")

    # Handle Literal types
    if type_origin is Literal:
        values = list(type_args)
        if not values:
            return {"type": "string"}
        # Use the type of the first value to determine the JSON type
        first_value_type = type(values[0]).__name__
        json_type = get_json_type_for_py_type(first_value_type)
        return {"type": json_type, "enum": values}

    if type_origin is not None:
        if type_origin in (list, tuple, set, frozenset):
            json_schema_for_items = get_json_schema_for_arg(type_args[0]) if type_args else {"type": "string"}
            return {"type": "array", "items": json_schema_for_items}
        elif type_origin is dict:
            # Handle both key and value types for dictionaries
            key_schema = get_json_schema_for_arg(type_args[0]) if type_args else {"type": "string"}
            value_schema = get_json_schema_for_arg(type_args[1]) if len(type_args) > 1 else {"type": "string"}
            return {"type": "object", "propertyNames": key_schema, "additionalProperties": value_schema}
        elif is_origin_union_type(type_origin):
            types: list[dict[str, Any]] = []
            for arg in type_args:
                try:
                    schema = get_json_schema_for_arg(arg)
                    if schema:
                        types.append(schema)
                except Exception:
                    continue
            return {"anyOf": types} if types else None

    if isinstance(type_hint, type) and issubclass(type_hint, Enum):
        enum_values = [member.value for member in type_hint]
        return {"type": "string", "enum": enum_values}

    if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
        # Get the schema and inline it
        schema = type_hint.model_json_schema()
        return inline_pydantic_schema(schema)  # type: ignore

    if hasattr(type_hint, "__dataclass_fields__"):
        # Convert dataclass to JSON schema
        properties: dict[str, Any] = {}
        required: list[str] = []

        for field_name, field in type_hint.__dataclass_fields__.items():  # type: ignore
            field_type = field.type  # type: ignore
            field_schema = get_json_schema_for_arg(field_type)

            if (
                field_schema
                and "anyOf" in field_schema
                and any(schema["type"] == "null" for schema in field_schema["anyOf"])
            ):
                field_schema["type"] = next(
                    schema["type"] for schema in field_schema["anyOf"] if schema["type"] != "null"
                )
                field_schema.pop("anyOf")
            else:
                required.append(field_name)  # type: ignore

            if field_schema:
                properties[field_name] = field_schema

        arg_json_schema = {"type": "object", "properties": properties, "additionalProperties": False}

        if required:
            arg_json_schema["required"] = required  # type: ignore
        return arg_json_schema

    json_schema: dict[str, Any] = {"type": get_json_type_for_py_type(type_hint.__name__)}
    if json_schema["type"] == "object":
        json_schema["properties"] = {}
        json_schema["additionalProperties"] = False
    return json_schema


def get_json_schema(
    type_hints: dict[str, Any],
    param_descriptions: Optional[dict[str, str]] = None,
    strict: bool = False,
    signature: Optional[inspect.Signature] = None,
) -> dict[str, Any]:
    json_schema: dict[str, Any] = {
        "type": "object",
        "properties": {},
    }
    if strict:
        json_schema["additionalProperties"] = False

    required_params: list[str] = []

    # We only include the fields in the type_hints dict
    for parameter_name, type_hint in type_hints.items():
        # log_info(f"Parsing arg: {k} | {v}")
        if parameter_name == "return":
            continue

        try:
            # Check if type is Optional (Union with NoneType)
            type_origin = get_origin(type_hint)
            type_args = get_args(type_hint)
            is_optional = (
                type_origin is Union and len(type_args) == 2 and any(arg is type(None) for arg in type_args)
            )

            # Check if parameter has a default value
            has_default = False
            if signature and parameter_name in signature.parameters:
                param = signature.parameters[parameter_name]
                has_default = param.default is not inspect.Parameter.empty

            # Get the actual type if it's Optional
            if is_optional:
                type_hint = next(arg for arg in type_args if arg is not type(None))

            if type_hint:
                arg_json_schema = get_json_schema_for_arg(type_hint)
            else:
                arg_json_schema = {}

            if arg_json_schema is not None:
                # Add description
                if (
                    param_descriptions
                    and parameter_name in param_descriptions
                    and param_descriptions[parameter_name]
                ):
                    arg_json_schema["description"] = param_descriptions[parameter_name]

                json_schema["properties"][parameter_name] = arg_json_schema

                # Add to required if not optional and no default
                if not is_optional and not has_default:
                    required_params.append(parameter_name)

            else:
                logger.warning(f"Could not parse argument {parameter_name} of type {type_hint}")
        except Exception as e:
            logger.error(f"Error processing argument {parameter_name}: {str(e)}")
            continue

    # Add required fields if any
    if required_params:
        json_schema["required"] = required_params

    return json_schema


def get_func_docstring(func: Callable[..., Any]) -> str:
    if isinstance(func, partial):
        return str(func)  # type: ignore
    docstring = getdoc(func)
    if not docstring:
        return ""
    parsed_doc = parse(docstring)
    lines: list[str] = []
    if parsed_doc.short_description:
        lines.append(parsed_doc.short_description)
    if parsed_doc.long_description:
        lines.extend(parsed_doc.long_description.split("\n"))
    return "\n".join(lines)


@dataclass(slots=True, kw_only=True, frozen=True)
class Tool:
    """Lightweight callable-to-schema wrapper usable by LLM runtimes."""

    name: str
    description: str
    parameters: Mapping[str, Any]
    strict: bool = False
    _callable: Callable[..., Any]  # private, still invokable

    @classmethod
    def from_function(
        cls,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        description: str | None = None,
        strict: bool = False,
    ) -> Tool:
        """Create a Tool from any callable (sync/async/partial)."""
        # Unwrap partials to fetch the original function for introspection
        if isinstance(fn, partial):
            raw_fn = fn.func
        # User-defined callable objects (instances with __call__)
        elif callable(fn) and not (inspect.isfunction(fn) or inspect.ismethod(fn) or inspect.isbuiltin(fn)):
            raw_fn = getattr(fn, "__call__")  # type: ignore[attr-defined]
        else:
            raw_fn = fn

        # Get type hints (signature handled automatically by get_json_schema)
        try:
            hints = get_type_hints(raw_fn, include_extras=True)
        except (NameError, AttributeError, TypeError):
            # Fallback if type hints can't be resolved
            hints = getattr(raw_fn, "__annotations__", {})

        # Get function signature for parameter defaults
        sig = inspect.signature(raw_fn)

        # Extract parameter descriptions from docstring
        short_desc, param_desc = _get_param_descriptions(raw_fn)

        # Generate JSON schema for parameters
        schema = get_json_schema(hints, param_desc, strict=strict, signature=sig)

        # Use provided name or derive from function
        tool_name = name or getattr(raw_fn, "__name__", "unknown_function")

        # Use provided description or derive from docstring
        tool_description = description or (short_desc or get_func_docstring(raw_fn))

        return cls(
            name=tool_name,
            description=tool_description,
            parameters=schema,
            strict=strict,
            _callable=cast(Callable[..., Any], fn),  # satisfy the type checker
        )

    def run_sync(self, **kwargs: Any) -> Any:
        """Invoke the tool synchronously."""
        result = self._callable(**kwargs)
        # Any awaitable (coroutine, custom Awaitable, etc.) means the caller must `await`.
        if inspect.isawaitable(result):
            raise RuntimeError(f"Tool {self.name!r} is async; use 'await tool.run(**kwargs)' instead.")
        return result

    async def run(self, **kwargs: Any) -> Any:
        """Invoke the tool asynchronously."""
        result = self._callable(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    def model_dump(self) -> dict[str, Any]:
        """Export as OpenAI/Anthropic style tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
            "strict": self.strict,
        }
