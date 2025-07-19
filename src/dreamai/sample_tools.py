"""
sample_tools.py
================
Ten representative “tool” functions showcasing modern Python 3.13 type hints that we
will use as acceptance tests for the automatic JSON‑schema generator.

The set climbs gradually in complexity — from single‑argument primitives to nested
Pydantic models and async generators — while staying completely framework‑agnostic.

Requirements
------------
* Python ≥ 3.13 (PEP 695 enabled, `|` unions, `Literal`, etc.)
* Pydantic ≥ 2.8 (for the runtime models below)
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict

from pydantic import BaseModel, Field

__all__ = [
    "add",
    "greet",
    "sort_numbers",
    "fetch_url",
    "User",
    "register_user",
    "Order",
    "process_orders",
    "calc_stats",
    "Event",
    "stream_events",
    "send_email",
    "SystemConfig",
    "configure_system",
    "SettingsDict",
    "update_settings",
]


# ---------------------------------------------------------------------------
# 1. Extremely simple — two required ints
# ---------------------------------------------------------------------------


def add(a: int, b: int) -> int:
    """Return the sum of *a* and *b*."""

    return a + b


# ---------------------------------------------------------------------------
# 2. One required arg, one optional boolean with a default
# ---------------------------------------------------------------------------


def greet(name: str, excited: bool = False) -> str:
    """Return a friendly greeting.

    Parameters
    ----------
    name
        The person to greet.
    excited
        If *True*, add an exclamation mark.
    """

    greeting = f"Hello, {name}"
    return f"{greeting}!" if excited else greeting


# ---------------------------------------------------------------------------
# 3. Literal argument for constrained values
# ---------------------------------------------------------------------------


def sort_numbers(numbers: list[int], order: Literal["asc", "desc"] = "asc") -> list[int]:
    """Return *numbers* sorted in ascending or descending order."""

    return sorted(numbers, reverse=order == "desc")


# ---------------------------------------------------------------------------
# 4. Async function with default timeout
# ---------------------------------------------------------------------------


async def fetch_url(url: str, timeout: float = 5.0) -> str:
    """Fetch *url* with an async sleep to simulate I/O."""

    await asyncio.sleep(0.001)  # pretend we did network I/O
    return f"<html><title>{url}</title></html>  <!-- fetched in {timeout}s -->"


# ---------------------------------------------------------------------------
# 5. Pydantic model argument
# ---------------------------------------------------------------------------


class User(BaseModel):
    """Minimal user model."""

    id: int = Field(..., description="Primary key")
    name: str = Field(description="Full name, 1–100 chars", min_length=1, max_length=100)
    email: str | None = Field(None, pattern=r".+@.+\..+")


def register_user(user: User) -> str:
    """Persist *user* and return a confirmation message."""

    # imaginary DB insert here…
    return f"User {user.name!r} ({user.id}) registered."


# ---------------------------------------------------------------------------
# 6. Dataclass argument inside a list
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Order:
    id: int
    sku: str
    quantity: int = 1


def process_orders(orders: list[Order]) -> int:
    """Process *orders* and return the total number processed."""

    return len(orders)


# ---------------------------------------------------------------------------
# 7. Literal with statistics method
# ---------------------------------------------------------------------------


def calc_stats(values: list[float], method: Literal["mean", "median", "mode"] = "mean") -> float:
    """Calculate a statistic over *values*."""

    if not values:
        raise ValueError("values must not be empty")

    match method:
        case "mean":
            return sum(values) / len(values)
        case "median":
            sorted_vals = sorted(values)
            mid = len(sorted_vals) // 2
            return sorted_vals[mid] if len(sorted_vals) % 2 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        case "mode":
            return max(set(values), key=values.count)


# ---------------------------------------------------------------------------
# 8. Async generator returning dataclass events
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Event:
    ts: float
    payload: str


async def stream_events(topic: str, limit: int | None = None) -> AsyncIterator[Event]:
    """Yield up to *limit* events from *topic*."""

    count = 0
    while limit is None or count < limit:
        await asyncio.sleep(0.001)
        yield Event(ts=asyncio.get_event_loop().time(), payload=f"{topic}:{count}")
        count += 1


# ---------------------------------------------------------------------------
# 9. Function with optional nested collection & pathlib.Path
# ---------------------------------------------------------------------------


def send_email(
    to: list[str],
    subject: str,
    body: str,
    attachments: list[Path] | None = None,
) -> None:
    """Pretend to send email. No return value."""

    # Nothing happens here; this is just an example.
    ...


# ---------------------------------------------------------------------------
# 10. Nested dataclasses inside a configuration object
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DatabaseConfig:
    url: str
    pool_size: int = 10


@dataclass(slots=True)
class SystemConfig:
    debug: bool = False
    database: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(url="sqlite:///:memory:"))


def configure_system(config: SystemConfig) -> str:
    """Apply *config* and return a status string."""

    return f"Configured with debug={config.debug!r} pool={config.database.pool_size}"


# ---------------------------------------------------------------------------
# 11. TypedDict example for ad‑hoc settings
# ---------------------------------------------------------------------------


class SettingsDict(TypedDict, total=False):
    app_name: str
    theme: Literal["light", "dark"]
    max_items: int


def update_settings(settings: SettingsDict) -> None:
    """Update app settings in‑place. No return value."""

    ...
