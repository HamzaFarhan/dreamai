# Stdlib
import inspect
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import MISSING, dataclass, fields, is_dataclass
from functools import partial
from inspect import getdoc
from typing import Any, Union, cast, get_args, get_origin

from docstring_parser import parse
from loguru import logger
from pydantic import BaseModel, Field, create_model


def _is_async_function(func: Callable[..., Any]) -> bool:
    """
    Check if a function is async, even when wrapped by decorators like @staticmethod.

    This function tries to detect async functions by:
    1. Checking the function directly with inspect functions
    2. Looking at the original function if it's wrapped
    3. Checking the function's code object for async indicators
    """
    from inspect import iscoroutine, iscoroutinefunction

    # First, try the standard inspect functions
    if iscoroutinefunction(func) or iscoroutine(func):
        return True

    # If the function has a __wrapped__ attribute, check the original function
    if hasattr(func, "__wrapped__"):
        original_func = func.__wrapped__  # type: ignore
        if iscoroutinefunction(original_func) or iscoroutine(original_func):
            return True

    # Check if the function has CO_COROUTINE flag in its code object
    try:
        if hasattr(func, "__code__") and func.__code__.co_flags & 0x80:  # CO_COROUTINE flag
            return True
    except (AttributeError, TypeError):
        pass

    # For static methods, try to get the original function
    try:
        if hasattr(func, "__func__"):
            original_func = func.__func__  # type: ignore
            if iscoroutinefunction(original_func) or iscoroutine(original_func):
                return True
            # Check the code object of the original function
            if hasattr(original_func, "__code__") and original_func.__code__.co_flags & 0x80:
                return True
    except (AttributeError, TypeError):
        pass

    return False


def _remove_title_from_schema(schema: dict[str, Any]) -> None:
    """
    Remove the 'title' keyword from JSON schema and contained property schemas.

    :param schema: The JSON schema to remove the 'title' keyword from.
    """
    for key, value in list(schema.items()):
        # Make sure not to remove parameters named title
        if key == "properties" and isinstance(value, dict) and "title" in value:
            for sub_val in value.values():  # type: ignore
                _remove_title_from_schema(sub_val)  # type: ignore
        elif key == "title":
            del schema[key]
        elif isinstance(value, dict):
            _remove_title_from_schema(value)  # type: ignore
        elif isinstance(value, list):
            for item in value:  # type: ignore
                if isinstance(item, dict):
                    _remove_title_from_schema(item)  # type: ignore


def _parse_docstring(method: Callable[..., Any]) -> tuple[str, dict[str, str]]:
    """
    Extracts the full description and parameter descriptions from the method's docstring.

    :param method: The method to extract descriptions from.
    :returns:
        A tuple including the full description of the method and a dictionary mapping parameter names to their
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

    lines: list[str] = []
    if parsed_doc.short_description:
        lines.append(parsed_doc.short_description)
    if parsed_doc.long_description:
        lines.extend(parsed_doc.long_description.split("\n"))

    full_description = "\n".join(lines)

    return full_description, param_descriptions


def is_origin_union_type(origin: Any) -> bool:
    import sys

    if sys.version_info.minor >= 10:
        from types import UnionType

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
    resolved_definitions: dict[str, dict[str, Any]] = {}
    for def_name, def_schema in definitions.items():
        resolved_definitions[def_name] = process_schema(def_schema, definitions)

    # Process the main schema with resolved definitions
    result = process_schema(schema, resolved_definitions)

    # Remove any remaining definitions
    if "$defs" in result:
        del result["$defs"]

    return result


def _dataclass_to_pydantic_model(dc_type: Any) -> type[BaseModel]:
    """
    Convert a Python dataclass to an equivalent Pydantic model.

    :param dc_type: The dataclass type to convert.
    :returns:
        A dynamically generated Pydantic model class with fields and types derived from the dataclass definition.
        Field descriptions are extracted from docstrings when available.
    """
    _, param_descriptions = _parse_docstring(dc_type)
    cls = dc_type if isinstance(dc_type, type) else dc_type.__class__

    field_defs: dict[str, Any] = {}
    for field in fields(dc_type):
        f_type = field.type if isinstance(field.type, str) else _resolve_type(field.type)
        default = field.default if field.default is not MISSING else ...
        default = field.default_factory() if callable(field.default_factory) else default
        field_name = field.name
        description = param_descriptions.get(field_name, f"Field '{field_name}' of '{cls.__name__}'.")
        field_defs[field_name] = (f_type, Field(default, description=description))

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
        return list[_resolve_type(args[0]) if args else Any]

    if origin is Sequence:
        return Sequence[_resolve_type(args[0]) if args else Any]

    if is_origin_union_type(origin):
        return Union[tuple(_resolve_type(a) for a in args)]  # type: ignore[misc]

    if origin is dict:
        return dict[args[0] if args else Any, _resolve_type(args[1]) if args else Any]

    return _type


class SchemaGenerationError(Exception):
    """
    Exception raised when automatic schema generation fails.
    """

    pass


@dataclass
class Tool:  # noqa: D101 – simple container
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., Any]

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the underlying function, awaiting if necessary."""

        if self._is_async:
            return await self.function(*args, **kwargs)
        return self.function(*args, **kwargs)

    def run_sync(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous wrapper that raises if the tool is async."""

        if self._is_async:
            raise RuntimeError(f"Tool '{self.name}' is async – use 'await tool.run()' instead")
        return self.function(*args, **kwargs)

    def __post_init__(self):
        self._is_async = _is_async_function(self.function)


def create_tool_from_function(
    function: Callable[..., Any] | Callable[..., Awaitable[Any]],
    name: str | None = None,
    description: str | None = None,
) -> Tool:
    """Generate a :class:`Tool` wrapper from *function*.

    • Supports plain callables, ``async`` functions, and ``functools.partial``
      objects (bound arguments are transparently handled).
    """

    underlying = function.func if isinstance(function, partial) else function

    doc_description, doc_param_descriptions = _parse_docstring(underlying)
    tool_description = description if description is not None else doc_description

    signature = inspect.signature(cast(Callable[..., Any], function))

    # collect fields (types and defaults) and descriptions from function parameters
    fields: dict[str, Any] = {}
    descriptions: dict[str, str] = doc_param_descriptions.copy()

    for param_name, param in signature.parameters.items():
        if param.annotation is param.empty:
            raise ValueError(
                f"Function '{underlying.__name__}': parameter '{param_name}' does not have a type hint."
            )

        # if the parameter has not a default value, Pydantic requires an Ellipsis (...)
        # to explicitly indicate that the parameter is required
        default = param.default if param.default is not param.empty else ...
        annotation = _resolve_type(param.annotation)
        fields[param_name] = (annotation, default)

        if hasattr(param.annotation, "__metadata__"):
            descriptions[param_name] = param.annotation.__metadata__[0]

    try:
        model = create_model(underlying.__name__, **fields)
        # Provide the function's module globals to resolve forward references
        if hasattr(underlying, "__globals__"):
            # Use the correct parameter name for model_rebuild
            model.model_rebuild(_types_namespace=underlying.__globals__)
        else:
            model.model_rebuild()
        schema = model.model_json_schema()
    except Exception as e:
        raise SchemaGenerationError(f"Failed to create JSON schema for function '{underlying.__name__}'") from e

    schema = inline_pydantic_schema(schema)
    _remove_title_from_schema(schema)

    for param_name, param_description in descriptions.items():
        if param_name in schema.get("properties", {}):
            schema["properties"][param_name]["description"] = param_description

    return Tool(
        name=name or underlying.__name__,
        description=tool_description,
        parameters=schema,
        function=cast(Callable[..., Any], function),
    )
