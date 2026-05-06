"""godot-e2e: Out-of-process E2E testing tool for Godot."""

from .async_client import AsyncGodotE2E
from .commands import GodotE2E
from .expect import ExpectTarget, expect
from .locator import Locator, LocatorNode
from .types import (
    Vector2,
    Vector2i,
    Vector3,
    Vector3i,
    Rect2,
    Rect2i,
    Color,
    Transform2D,
    NodePath,
    deserialize,
    serialize,
    GodotE2EError,
    NodeNotFoundError,
    TimeoutError,
    ConnectionLostError,
    CommandError,
)
from .client import GodotClient
from .launcher import GodotLauncher

__version__ = "1.1.0"

__all__ = [
    "AsyncGodotE2E",
    "GodotE2E",
    "expect",
    "ExpectTarget",
    "Locator",
    "LocatorNode",
    "Vector2",
    "Vector2i",
    "Vector3",
    "Vector3i",
    "Rect2",
    "Rect2i",
    "Color",
    "Transform2D",
    "NodePath",
    "deserialize",
    "serialize",
    "GodotE2EError",
    "NodeNotFoundError",
    "TimeoutError",
    "ConnectionLostError",
    "CommandError",
    "GodotClient",
    "GodotLauncher",
]
