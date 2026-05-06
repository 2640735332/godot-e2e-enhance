"""UI testing with Locator — no absolute paths required.

This is the Locator-equivalent of test_ui.py. Compare the two files:
Locator tests are shorter and resilient to scene tree restructuring.
"""


def test_initial_ui_state(game):
    """Verify the menu scene loads with correct initial state."""
    loc = game.locator()
    assert loc.by_text("UI Testing Demo").exists()
    assert loc.by_text("Not clicked yet").exists()


def test_button_click_updates_label(game):
    """Click a button and verify the label updates."""
    loc = game.locator()
    loc.by_text("Click Me!").click()
    game.wait_process_frames(2)
    assert loc.by_text("Clicked 1 times").exists()

    loc.by_text("Click Me!").click()
    game.wait_process_frames(2)
    assert loc.by_text("Clicked 2 times").exists()


def test_navigate_to_detail_page(game):
    """Click navigate button and verify scene changes."""
    loc = game.locator()

    # Find navigate button by its type + name filter
    loc.by_name("NavigateButton").click()
    game.wait_for_node("/root/Detail", timeout=5.0)

    assert loc.by_text("Detail Page").exists()


def test_navigate_back_to_menu(game):
    """Navigate to detail page and back to menu."""
    loc = game.locator()

    loc.by_name("NavigateButton").click()
    game.wait_for_node("/root/Detail", timeout=5.0)

    loc.by_name("BackButton").click()
    game.wait_for_node("/root/Menu", timeout=5.0)

    assert loc.by_text("UI Testing Demo").exists()


def test_scene_change_api(game):
    """Use the change_scene API directly, verify with locator."""
    game.change_scene("res://detail.tscn")
    game.wait_for_node("/root/Detail", timeout=5.0)

    assert game.locator().by_name("BackButton").exists()


def test_locator_count(game):
    """Verify count() returns expected number of matches."""
    loc = game.locator()
    buttons = loc.by_type("Button").all
    assert buttons.count() >= 2  # ClickButton and NavigateButton


def test_locator_all_iteration(game):
    """Verify .all.as_nodes() returns actionable node objects."""
    nodes = game.locator().by_type("Button").all.as_nodes()
    assert len(nodes) >= 2
    # Each should be a LocatorNode with a valid path
    for node in nodes:
        assert node.path.startswith("/root/")
        assert node.exists()
