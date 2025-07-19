#!/usr/bin/env python3
"""Test the Tool implementation with various callable types."""

from functools import partial
from typing import Literal

from to_tool import Tool


def sync_function(name: str, age: int = 25) -> str:
    """A simple sync function for testing.
    
    :param name: The person's name
    :param age: The person's age
    """
    return f"Hello {name}, you are {age} years old"


async def async_function(message: str, repeat: int = 1) -> str:
    """An async function for testing.
    
    :param message: The message to return
    :param repeat: Number of times to repeat
    """
    return message * repeat


def function_with_literal(mode: Literal["fast", "slow"], value: str) -> str:
    """Function with Literal type.
    
    :param mode: Processing mode
    :param value: Input value
    """
    return f"Processing {value} in {mode} mode"


class CallableClass:
    """A callable class for testing."""
    
    def __call__(self, x: int, y: int = 10) -> int:
        """Add two numbers.
        
        :param x: First number
        :param y: Second number
        """
        return x + y


def test_sync_function():
    """Test Tool with sync function."""
    tool = Tool.from_function(sync_function)
    print(f"Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Parameters: {tool.parameters}")
    
    # Test invocation
    result = tool(name="Alice", age=30)
    print(f"Result: {result}")
    print()


def test_async_function():
    """Test Tool with async function."""
    tool = Tool.from_function(async_function)
    print(f"Async Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Parameters: {tool.parameters}")
    print()


def test_partial_function():
    """Test Tool with partial function."""
    partial_func = partial(sync_function, age=35)
    tool = Tool.from_function(partial_func)
    print(f"Partial Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Parameters: {tool.parameters}")
    
    # Test invocation
    result = tool(name="Bob")
    print(f"Result: {result}")
    print()


def test_literal_function():
    """Test Tool with Literal type."""
    tool = Tool.from_function(function_with_literal)
    print(f"Literal Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Parameters: {tool.parameters}")
    
    # Test invocation
    result = tool(mode="fast", value="data")
    print(f"Result: {result}")
    print()


def test_callable_class():
    """Test Tool with callable class."""
    callable_obj = CallableClass()
    tool = Tool.from_function(callable_obj)
    print(f"Callable Class Tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Parameters: {tool.parameters}")
    
    # Test invocation
    result = tool(x=5, y=15)
    print(f"Result: {result}")
    print()


def test_model_dump():
    """Test model_dump method."""
    tool = Tool.from_function(sync_function)
    dump = tool.model_dump()
    print(f"Model dump: {dump}")
    print()


if __name__ == "__main__":
    test_sync_function()
    test_async_function()
    test_partial_function()
    test_literal_function()
    test_callable_class()
    test_model_dump()
