"""expect() — auto-retry assertions for godot-e2e.

Provides chainable, polling assertions that eliminate flaky timing-dependent
tests. Each matcher re-resolves the locator and retries until the condition
is met or a timeout is reached.

Usage::

    from godot_e2e import GodotE2E
    from godot_e2e.expect import expect

    def test_player_health(game):
        expect(game.locator().by_name("Player")).to_have_property("health", 100)
        expect(game.locator().by_text("Start Game")).to_be_visible()
        expect(game.locator().by_name("ScoreLabel")).to_have_text("Score: 10")
"""

from __future__ import annotations

import time
from typing import Any, Callable, Optional

from .types import deserialize, CommandError


class ExpectTarget:
    """A chainable assertion target created by ``expect()``.

    Each method polls until the condition is satisfied or times out.
    """

    def __init__(self, locator, timeout: float = 5.0, interval: float = 0.1) -> None:
        self._locator = locator
        self._timeout = timeout
        self._interval = interval

    # -- Matchers ------------------------------------------------------------

    def to_exist(self, timeout: Optional[float] = None) -> None:
        """Assert that at least one matching node exists in the scene tree."""
        deadline = time.monotonic() + (timeout or self._timeout)
        last_count = 0
        while time.monotonic() < deadline:
            try:
                c = self._locator.count()
                last_count = c
                if c > 0:
                    return
            except CommandError:
                pass
            time.sleep(self._interval)
        raise AssertionError(
            f"Expected locator {self._locator} to match at least 1 node "
            f"after {timeout or self._timeout}s (matched {last_count})"
        )

    def to_be_visible(self, timeout: Optional[float] = None) -> None:
        """Assert that the resolved Control node is visible."""
        deadline = time.monotonic() + (timeout or self._timeout)
        last_error = ""
        while time.monotonic() < deadline:
            try:
                node = self._locator.first
                # Use direct property check
                resp = node._client.send_command(
                    "get_property", path=node.path, property="visible"
                )
                if resp.get("result") is True or resp.get("result") == "true":
                    return
                last_error = "node exists but visible == false"
            except Exception as e:
                last_error = str(e)
            time.sleep(self._interval)
        raise AssertionError(
            f"Expected locator {self._locator} to be visible "
            f"after {timeout or self._timeout}s ({last_error})"
        )

    def to_have_property(self, property_name: str, expected_value: Any,
                         timeout: Optional[float] = None) -> None:
        """Assert that the resolved node has a property with the expected value."""
        deadline = time.monotonic() + (timeout or self._timeout)
        last_value = None
        while time.monotonic() < deadline:
            try:
                node = self._locator.first
                actual = node.get_property(property_name)
                last_value = actual
                if actual == expected_value:
                    return
            except Exception:
                pass
            time.sleep(self._interval)
        raise AssertionError(
            f"Expected locator {self._locator} property '{property_name}' "
            f"to equal {expected_value!r} after {timeout or self._timeout}s "
            f"(last value: {last_value!r})"
        )

    def to_have_text(self, expected_text: str,
                     timeout: Optional[float] = None) -> None:
        """Assert that the resolved Control node has the expected text."""
        self.to_have_property("text", expected_text, timeout)

    def to_satisfy(self, predicate: Callable[[Any], bool],
                   timeout: Optional[float] = None,
                   description: str = "predicate") -> None:
        """Assert that a predicate on the resolved node returns True.

        The predicate receives the resolved node's path as a string.
        """
        deadline = time.monotonic() + (timeout or self._timeout)
        last_error = ""
        while time.monotonic() < deadline:
            try:
                node = self._locator.first
                if predicate(node):
                    return
                last_error = f"{description} returned False"
            except Exception as e:
                last_error = str(e)
            time.sleep(self._interval)
        raise AssertionError(
            f"Expected locator {self._locator} to satisfy {description} "
            f"after {timeout or self._timeout}s ({last_error})"
        )

    def to_have_count(self, expected_count: int,
                      timeout: Optional[float] = None) -> None:
        """Assert that the locator matches exactly *n* nodes."""
        deadline = time.monotonic() + (timeout or self._timeout)
        last_count = 0
        while time.monotonic() < deadline:
            try:
                c = self._locator.count()
                last_count = c
                if c == expected_count:
                    return
            except CommandError:
                pass
            time.sleep(self._interval)
        raise AssertionError(
            f"Expected locator {self._locator} to match {expected_count} node(s) "
            f"after {timeout or self._timeout}s (last count: {last_count})"
        )

    def to_be_greater_than(self, property_name: str, threshold: float,
                           timeout: Optional[float] = None) -> None:
        """Assert that the resolved node's property is greater than *threshold*."""
        deadline = time.monotonic() + (timeout or self._timeout)
        last_value = None
        while time.monotonic() < deadline:
            try:
                node = self._locator.first
                actual = node.get_property(property_name)
                last_value = actual
                if actual is not None and actual > threshold:
                    return
            except Exception:
                pass
            time.sleep(self._interval)
        raise AssertionError(
            f"Expected locator {self._locator} property '{property_name}' "
            f"> {threshold} after {timeout or self._timeout}s "
            f"(last value: {last_value!r})"
        )

    def to_be_less_than(self, property_name: str, threshold: float,
                        timeout: Optional[float] = None) -> None:
        """Assert that the resolved node's property is less than *threshold*."""
        deadline = time.monotonic() + (timeout or self._timeout)
        last_value = None
        while time.monotonic() < deadline:
            try:
                node = self._locator.first
                actual = node.get_property(property_name)
                last_value = actual
                if actual is not None and actual < threshold:
                    return
            except Exception:
                pass
            time.sleep(self._interval)
        raise AssertionError(
            f"Expected locator {self._locator} property '{property_name}' "
            f"< {threshold} after {timeout or self._timeout}s "
            f"(last value: {last_value!r})"
        )


def expect(locator, timeout: float = 5.0, interval: float = 0.1) -> ExpectTarget:
    """Create an auto-retry assertion target bound to *locator*.

    Args:
        locator: A :class:`Locator` instance from ``game.locator()``.
        timeout: How long to keep retrying (seconds).
        interval: How long to wait between retries (seconds).

    Returns:
        An :class:`ExpectTarget` with chainable matchers.

    Example::

        expect(game.locator().by_text("Start")).to_be_visible(timeout=10.0)
        expect(game.locator().by_name("Player")).to_have_property("health", 100)
    """
    return ExpectTarget(locator, timeout=timeout, interval=interval)
