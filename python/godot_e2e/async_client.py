"""Async API for godot-e2e.

Provides an asyncio-compatible interface for writing E2E tests with
async/await syntax. Supports parallel wait operations and integrates
with pytest-asyncio.

Usage::

    import pytest
    from godot_e2e.async_client import AsyncGodotE2E

    @pytest.mark.asyncio
    async def test_player_movement():
        async with AsyncGodotE2E.launch("./my_project") as game:
            await game.wait_for_node("/root/Main")
            await game.press_action("move_right")
            await game.wait_physics_frames(10)
            pos = await game.get_property("/root/Main/Player", "position:x")
            assert pos > 0
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, List, Optional

from .client import GodotClient
from .launcher import GodotLauncher
from .locator import Locator, LocatorNode
from .types import deserialize, serialize


class AsyncGodotE2E:
    """Async wrapper around :class:`godot_e2e.GodotE2E`.

    All blocking operations are delegated to a thread pool so the event
    loop stays free.
    """

    def __init__(self, client: GodotClient, launcher=None,
                 executor: Optional[concurrent.futures.ThreadPoolExecutor] = None) -> None:
        self._client = client
        self._launcher = launcher
        self._executor = executor or concurrent.futures.ThreadPoolExecutor(max_workers=4)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    async def launch(
        cls,
        project_path: str,
        godot_path: Optional[str] = None,
        port: int = 0,
        timeout: float = 10.0,
        extra_args: Optional[List[str]] = None,
    ) -> "AsyncGodotE2E":
        """Launch Godot and return a connected ``AsyncGodotE2E`` instance."""
        loop = asyncio.get_running_loop()
        launcher = GodotLauncher()
        client = await loop.run_in_executor(
            None,
            lambda: launcher.launch(project_path, godot_path, port, timeout, extra_args),
        )
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        return cls(client, launcher, executor)

    @classmethod
    async def connect(
        cls,
        host: str = "127.0.0.1",
        port: int = 6008,
        token: str = "",
    ) -> "AsyncGodotE2E":
        """Connect to an already-running Godot instance."""
        loop = asyncio.get_running_loop()
        client = GodotClient(host, port)

        def _connect():
            client.connect()
            client.hello(token)
            return client

        await loop.run_in_executor(None, _connect)
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        return cls(client, None, executor)

    async def __aenter__(self) -> "AsyncGodotE2E":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def close(self) -> None:
        """Shut down the Godot process and close the connection."""
        if self._launcher:
            await asyncio.get_running_loop().run_in_executor(
                None, self._launcher.kill
            )
        else:
            await asyncio.get_running_loop().run_in_executor(
                None, self._client.close
            )
        self._executor.shutdown(wait=False)

    def _run(self, func, *args, **kwargs) -> Any:
        """Run a synchronous call in the thread pool."""
        return asyncio.get_running_loop().run_in_executor(
            self._executor, lambda: func(*args, **kwargs)
        )

    # ------------------------------------------------------------------
    # Node Operations
    # ------------------------------------------------------------------

    async def node_exists(self, path: str) -> bool:
        resp = await self._run(self._client.send_command, "node_exists", path=path)
        return resp.get("exists", False)

    async def get_property(self, path: str, property_name: str) -> Any:
        resp = await self._run(
            self._client.send_command, "get_property", path=path, property=property_name
        )
        return deserialize(resp["result"])

    async def set_property(self, path: str, property_name: str, value: Any) -> None:
        await self._run(
            self._client.send_command, "set_property",
            path=path, property=property_name, value=serialize(value)
        )

    async def call(self, path: str, method: str, args: Optional[list] = None) -> Any:
        resp = await self._run(
            self._client.send_command, "call_method",
            path=path, method=method,
            args=[serialize(a) for a in (args or [])]
        )
        return deserialize(resp.get("result"))

    async def find_by_group(self, group: str) -> list:
        resp = await self._run(
            self._client.send_command, "find_by_group", group=group
        )
        return resp.get("nodes", [])

    async def get_tree(self, path: str = "/root", depth: int = 4) -> dict:
        resp = await self._run(
            self._client.send_command, "get_tree", path=path, depth=depth
        )
        return resp.get("tree", {})

    # ------------------------------------------------------------------
    # Input Simulation
    # ------------------------------------------------------------------

    async def press_action(self, action_name: str, strength: float = 1.0) -> None:
        await self._run(
            self._client.send_command, "input_action",
            action_name=action_name, pressed=True, strength=strength
        )
        await self._run(
            self._client.send_command, "input_action",
            action_name=action_name, pressed=False
        )

    async def press_key(self, keycode: int) -> None:
        await self._run(
            self._client.send_command, "input_key", keycode=keycode, pressed=True
        )
        await self._run(
            self._client.send_command, "input_key", keycode=keycode, pressed=False
        )

    async def click(self, x: float, y: float, button: int = 1) -> None:
        await self._run(
            self._client.send_command, "input_mouse_button",
            x=x, y=y, button=button, pressed=True
        )
        await self._run(
            self._client.send_command, "input_mouse_button",
            x=x, y=y, button=button, pressed=False
        )

    # ------------------------------------------------------------------
    # Frame Synchronization
    # ------------------------------------------------------------------

    async def wait_process_frames(self, count: int = 1) -> None:
        await self._run(
            self._client.send_command, "wait_process_frames", count=count
        )

    async def wait_physics_frames(self, count: int = 1) -> None:
        await self._run(
            self._client.send_command, "wait_physics_frames", count=count
        )

    async def wait_seconds(self, seconds: float) -> None:
        await self._run(
            self._client.send_command, "wait_seconds", seconds=seconds
        )

    async def wait_for_node(self, path: str, timeout: float = 5.0) -> None:
        await self._run(
            self._client.send_command, "wait_for_node", path=path, timeout=timeout
        )

    async def wait_for_signal(self, path: str, signal_name: str,
                              timeout: float = 5.0) -> dict:
        resp = await self._run(
            self._client.send_command, "wait_for_signal",
            path=path, signal_name=signal_name, timeout=timeout
        )
        return resp

    async def wait_for_property(self, path: str, property_name: str,
                                value: Any, timeout: float = 5.0) -> None:
        await self._run(
            self._client.send_command, "wait_for_property",
            path=path, property=property_name,
            value=serialize(value), timeout=timeout
        )

    # ------------------------------------------------------------------
    # Parallel wait support
    # ------------------------------------------------------------------

    async def wait_all(self, *coroutines) -> List[Any]:
        """Run multiple wait operations in parallel.

        Example::

            await game.wait_all(
                game.wait_for_node("/root/Main/Player"),
                game.wait_for_node("/root/Main/UI"),
            )
        """
        return await asyncio.gather(*coroutines)

    # ------------------------------------------------------------------
    # Scene Management
    # ------------------------------------------------------------------

    async def get_scene(self) -> str:
        resp = await self._run(self._client.send_command, "get_scene")
        return resp.get("scene", "")

    async def change_scene(self, scene_path: str) -> None:
        await self._run(
            self._client.send_command, "change_scene", scene_path=scene_path
        )

    async def reload_scene(self) -> None:
        await self._run(self._client.send_command, "reload_scene")

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    async def screenshot(self, save_path: str = "") -> str:
        resp = await self._run(
            self._client.send_command, "screenshot", save_path=save_path
        )
        return resp.get("path", "")

    # ------------------------------------------------------------------
    # Locator
    # ------------------------------------------------------------------

    def locator(self) -> Locator:
        return Locator(self._client)

    # ------------------------------------------------------------------
    # Log Capture
    # ------------------------------------------------------------------

    async def get_logs(self, verbosity: str = "") -> list:
        resp = await self._run(
            self._client.send_command, "get_logs", verbosity=verbosity
        )
        return resp.get("logs", [])

    async def clear_logs(self) -> None:
        await self._run(self._client.send_command, "clear_logs")

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    async def quit(self, exit_code: int = 0) -> None:
        try:
            await self._run(
                self._client.send_command, "quit", exit_code=exit_code
            )
        except Exception:
            pass  # Expected — Godot exits
