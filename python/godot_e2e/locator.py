"""Locator — multi-strategy lazy node resolution for godot-e2e.

Provides a chainable, lazy API for finding nodes in the Godot scene tree
without hard-coding absolute paths.

Usage::

    from godot_e2e.locator import Locator

    def test_button_click(game):
        loc = game.locator()
        loc.by_text("Start Game").click()
        loc.by_name("*Title*").get_property("text")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from .types import deserialize, serialize, TimeoutError, NodeNotFoundError


class LocatorNode:
    """A single matched node, providing direct action methods."""

    def __init__(self, client, path: str) -> None:
        self._client = client
        self._path = path

    @property
    def path(self) -> str:
        """The absolute node path."""
        return self._path

    def click(self) -> None:
        """Click the center of this node."""
        self._client.send_command("click_node", path=self._path)

    def get_property(self, property_name: str) -> Any:
        """Read a property value from this node."""
        resp = self._client.send_command(
            "get_property", path=self._path, property=property_name
        )
        return deserialize(resp["result"])

    def set_property(self, property_name: str, value: Any) -> None:
        """Set a property value on this node."""
        self._client.send_command(
            "set_property", path=self._path,
            property=property_name, value=serialize(value)
        )

    def call(self, method: str, args: Optional[List[Any]] = None) -> Any:
        """Call a method on this node."""
        resp = self._client.send_command(
            "call_method", path=self._path, method=method,
            args=[serialize(a) for a in (args or [])]
        )
        return deserialize(resp.get("result"))

    def exists(self) -> bool:
        """Check if the node exists."""
        resp = self._client.send_command("node_exists", path=self._path)
        return resp.get("exists", False)

    def wait_visible(self, timeout: float = 5.0) -> None:
        """Wait for this Control node to become visible."""
        self._client.send_command(
            "locator_action",
            filters=[{"strategy": "path", "value": self._path}],
            locator_action="wait_visible",
            timeout=timeout,
        )

    def __repr__(self) -> str:
        return f"LocatorNode({self._path!r})"


class Locator:
    """Lazy, chainable node locator.

    Each action method re-resolves the query against the current scene tree,
    so the locator stays valid across scene changes and reloads.

    By default, multi-match raises ``locator_ambiguous``. Use:

    * ``.first`` — return the first match.
    * ``.nth(i)`` — return the i-th match (0-indexed).
    * ``.all`` — return every match as a list of ``LocatorNode``.

    Strategies (first call):

    ==============  ========================================================
    ``by_path()``   Absolute path or glob pattern (e.g. ``"/root/Main/*"``).
    ``by_name()``   Node name with wildcard support (``"Player"``).
    ``by_group()``  Nodes in a group (``"enemies"``).
    ``by_text()``   Control nodes with matching ``text`` property.
    ``by_type()``   Nodes of a specific class (``"Button"``).
    ``by_script()`` Nodes using a script (``"player.gd"``).
    ==============  ========================================================

    Chaining filters (refine after initial strategy):

    * ``.filter_by_name(pattern)``
    * ``.filter_by_group(group)``
    * ``.filter_by_text(text)``
    * ``.filter_by_type(type_name)``
    * ``.filter_by_script(script_name)``
    * ``.filter_visible()``
    """

    def __init__(self, client) -> None:
        self._client = client
        self._filters: List[Dict[str, str]] = []
        self._multi: str = "error"  # error | first | nth | all
        self._nth_index: int = 0

    # -- Strategy builders (first filter) -----------------------------------

    def by_path(self, pattern: str) -> "Locator":
        self._filters = [{"strategy": "path", "value": pattern}]
        return self

    def by_name(self, pattern: str) -> "Locator":
        self._filters = [{"strategy": "name", "value": pattern}]
        return self

    def by_group(self, group: str) -> "Locator":
        self._filters = [{"strategy": "group", "value": group}]
        return self

    def by_text(self, text: str) -> "Locator":
        self._filters = [{"strategy": "text", "value": text}]
        return self

    def by_type(self, type_name: str) -> "Locator":
        self._filters = [{"strategy": "type", "value": type_name}]
        return self

    def by_script(self, script_name: str) -> "Locator":
        self._filters = [{"strategy": "script", "value": script_name}]
        return self

    # -- Filter chainers ----------------------------------------------------

    def filter_by_name(self, pattern: str) -> "Locator":
        self._filters.append({"strategy": "name", "value": pattern})
        return self

    def filter_by_group(self, group: str) -> "Locator":
        self._filters.append({"strategy": "group", "value": group})
        return self

    def filter_by_text(self, text: str) -> "Locator":
        self._filters.append({"strategy": "text", "value": text})
        return self

    def filter_by_type(self, type_name: str) -> "Locator":
        self._filters.append({"strategy": "type", "value": type_name})
        return self

    def filter_by_script(self, script_name: str) -> "Locator":
        self._filters.append({"strategy": "script", "value": script_name})
        return self

    def filter_visible(self) -> "Locator":
        self._filters.append({"strategy": "visible", "value": ""})
        return self

    # -- Multi-match selectors ----------------------------------------------

    @property
    def first(self) -> "Locator":
        self._multi = "first"
        return self

    def nth(self, index: int) -> "Locator":
        self._multi = "nth"
        self._nth_index = index
        return self

    @property
    def all(self) -> "Locator":
        self._multi = "all"
        return self

    # -- Action methods (re-resolve on every call) --------------------------

    def _resolve(self) -> Dict[str, Any]:
        """Send the locator_find command and return the response."""
        params: Dict[str, Any] = {
            "filters": self._filters,
            "multi": self._multi,
        }
        if self._multi == "nth":
            params["nth"] = self._nth_index
        return self._client.send_command("locator_find", **params)

    def _resolve_one(self) -> str:
        """Return a single resolved path or raise an error."""
        resp = self._resolve()
        if "error" in resp:
            from .types import CommandError
            raise CommandError(resp.get("message", resp["error"]))
        nodes: List[str] = resp.get("nodes", [])
        if not nodes:
            raise NodeNotFoundError(
                f"Locator matched no nodes with filters: {self._filters}"
            )
        return nodes[0]

    def _resolve_all(self) -> List[str]:
        """Return all resolved paths."""
        resp = self._resolve()
        if "error" in resp:
            from .types import CommandError
            raise CommandError(resp.get("message", resp["error"]))
        return resp.get("nodes", [])

    # -- Single-node actions ------------------------------------------------

    def click(self) -> None:
        """Click the resolved node."""
        self._client.send_command(
            "locator_action",
            filters=self._filters,
            locator_action="click",
            multi=self._multi,
        )

    def get_property(self, property_name: str) -> Any:
        """Read a property from the resolved node."""
        resp = self._client.send_command(
            "locator_action",
            filters=self._filters,
            locator_action="get_property",
            property=property_name,
            multi=self._multi,
        )
        if "result" in resp:
            return deserialize(resp["result"])
        raise NodeNotFoundError(f"Locator matched no nodes: {self._filters}")

    def set_property(self, property_name: str, value: Any) -> None:
        """Set a property on the resolved node."""
        self._client.send_command(
            "locator_action",
            filters=self._filters,
            locator_action="set_property",
            property=property_name,
            value=serialize(value),
            multi=self._multi,
        )

    def call(self, method: str, args: Optional[List[Any]] = None) -> Any:
        """Call a method on the resolved node."""
        resp = self._client.send_command(
            "locator_action",
            filters=self._filters,
            locator_action="call",
            method=method,
            args=[serialize(a) for a in (args or [])],
            multi=self._multi,
        )
        if "result" in resp:
            return deserialize(resp["result"])
        raise NodeNotFoundError(f"Locator matched no nodes: {self._filters}")

    def exists(self) -> bool:
        """Check if any node matching the query exists."""
        resp = self._resolve()
        return len(resp.get("nodes", [])) > 0

    def wait_visible(self, timeout: float = 5.0) -> None:
        """Wait until the resolved Control node is visible."""
        self._client.send_command(
            "locator_action",
            filters=self._filters,
            locator_action="wait_visible",
            timeout=timeout,
            multi=self._multi,
        )

    def count(self) -> int:
        """Return the number of nodes matching this query."""
        resp = self._resolve()
        return len(resp.get("nodes", []))

    # -- Multi-node iteration -----------------------------------------------

    def as_nodes(self) -> List[LocatorNode]:
        """Resolve and return a list of ``LocatorNode`` objects."""
        paths = self._resolve_all()
        return [LocatorNode(self._client, p) for p in paths]

    def __iter__(self):
        return iter(self.as_nodes())

    def __repr__(self) -> str:
        multi_str = {"error": "", "first": ".first", "all": ".all", "nth": f".nth({self._nth_index})"}.get(self._multi, "")
        return f"Locator(filters={self._filters!r}{multi_str})"
