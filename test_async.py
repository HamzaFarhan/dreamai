#!/usr/bin/env python3
"""Test async functionality."""

import asyncio
from to_tool import Tool


async def async_function(message: str, repeat: int = 1) -> str:
    """An async function for testing.
    
    :param message: The message to return
    :param repeat: Number of times to repeat
    """
    await asyncio.sleep(0.1)  # Simulate async work
    return message * repeat


async def main():
    tool = Tool.from_function(async_function)
    
    # Test async call
    result = await tool.acall(message="Hello ", repeat=3)
    print(f"Async result: {result}")
    
    # Test that sync call raises error for async function
    try:
        tool(message="Hello", repeat=2)
    except RuntimeError as e:
        print(f"Expected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
