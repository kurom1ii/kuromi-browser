"""
Tests for kuromi_browser.actions module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Test imports
def test_imports():
    """Test all exports are importable."""
    from kuromi_browser.actions import (
        ActionChain,
        create_action_chain,
        MouseController,
        MouseButton,
        MousePosition,
        KeyboardController,
        KeyModifier,
        KeyboardState,
        KEY_DEFINITIONS,
        FormHandler,
        FormField,
        SelectOption,
        InputType,
        ScrollController,
        ScrollBehavior,
        ScrollAlignment,
        ScrollPosition,
    )

    # Verify classes exist
    assert ActionChain is not None
    assert MouseController is not None
    assert KeyboardController is not None
    assert FormHandler is not None
    assert ScrollController is not None


class TestMouseController:
    """Tests for MouseController."""

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.send = AsyncMock(return_value={})
        return session

    @pytest.mark.asyncio
    async def test_move_to(self, mock_session):
        """Test mouse move to position."""
        from kuromi_browser.actions import MouseController

        mouse = MouseController(mock_session, human_like=False)
        await mouse.move_to(100, 200)

        assert mouse.x == 100
        assert mouse.y == 200
        mock_session.send.assert_called()

    @pytest.mark.asyncio
    async def test_click(self, mock_session):
        """Test mouse click."""
        from kuromi_browser.actions import MouseController

        mouse = MouseController(mock_session, human_like=False)
        mouse._position.x = 100
        mouse._position.y = 200
        await mouse.click()

        # Should have mousePressed and mouseReleased calls
        calls = mock_session.send.call_args_list
        methods = [call[0][0] for call in calls]
        assert "Input.dispatchMouseEvent" in methods

    @pytest.mark.asyncio
    async def test_double_click(self, mock_session):
        """Test double click."""
        from kuromi_browser.actions import MouseController

        mouse = MouseController(mock_session, human_like=False)
        mouse._position.x = 100
        mouse._position.y = 200
        await mouse.double_click()

        # Should have multiple mousePressed/mouseReleased pairs
        assert mock_session.send.call_count >= 4

    @pytest.mark.asyncio
    async def test_right_click(self, mock_session):
        """Test right click."""
        from kuromi_browser.actions import MouseController, MouseButton

        mouse = MouseController(mock_session, human_like=False)
        mouse._position.x = 100
        mouse._position.y = 200
        await mouse.right_click()

        # Check that right button was used
        calls = mock_session.send.call_args_list
        for call in calls:
            if call[0][0] == "Input.dispatchMouseEvent":
                params = call[0][1]
                if "button" in params:
                    assert params["button"] == "right"


class TestKeyboardController:
    """Tests for KeyboardController."""

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.send = AsyncMock(return_value={})
        return session

    @pytest.mark.asyncio
    async def test_press(self, mock_session):
        """Test key press."""
        from kuromi_browser.actions import KeyboardController

        keyboard = KeyboardController(mock_session, human_like=False)
        await keyboard.press("Enter")

        # Should have keyDown and keyUp
        calls = mock_session.send.call_args_list
        methods = [call[0][0] for call in calls]
        assert "Input.dispatchKeyEvent" in methods

    @pytest.mark.asyncio
    async def test_type(self, mock_session):
        """Test typing text."""
        from kuromi_browser.actions import KeyboardController

        keyboard = KeyboardController(mock_session, human_like=False)
        await keyboard.type("Hi")

        # Should have calls for each character
        assert mock_session.send.call_count >= 4  # keyDown + keyUp for each char

    @pytest.mark.asyncio
    async def test_shortcut(self, mock_session):
        """Test keyboard shortcut."""
        from kuromi_browser.actions import KeyboardController

        keyboard = KeyboardController(mock_session, human_like=False)
        await keyboard.shortcut("Control", "a")

        # Should have multiple key events
        assert mock_session.send.call_count >= 4


class TestScrollController:
    """Tests for ScrollController."""

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.send = AsyncMock(return_value={
            "result": {
                "value": {
                    "x": 0,
                    "y": 0,
                    "max_x": 1000,
                    "max_y": 5000,
                    "width": 1920,
                    "height": 1080,
                }
            }
        })
        return session

    @pytest.mark.asyncio
    async def test_get_position(self, mock_session):
        """Test getting scroll position."""
        from kuromi_browser.actions import ScrollController

        scroll = ScrollController(mock_session, human_like=False)
        pos = await scroll.get_position()

        assert pos.x == 0
        assert pos.y == 0
        assert pos.max_y == 5000

    def test_scroll_position_properties(self):
        """Test ScrollPosition properties."""
        from kuromi_browser.actions import ScrollPosition

        pos = ScrollPosition(x=0, y=0, max_x=1000, max_y=5000)
        assert pos.is_at_top
        assert not pos.is_at_bottom
        assert pos.is_at_left
        assert not pos.is_at_right
        assert pos.scroll_percent_y == 0.0

        pos2 = ScrollPosition(x=1000, y=5000, max_x=1000, max_y=5000)
        assert not pos2.is_at_top
        assert pos2.is_at_bottom
        assert not pos2.is_at_left
        assert pos2.is_at_right
        assert pos2.scroll_percent_y == 100.0


class TestFormHandler:
    """Tests for FormHandler."""

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.send = AsyncMock(return_value={})
        return session

    @pytest.fixture
    def mock_element(self):
        """Create mock element."""
        element = AsyncMock()
        element._session = AsyncMock()
        element.node_id = 1
        element.scroll_into_view = AsyncMock()
        element.focus = AsyncMock()
        element.fill = AsyncMock()
        element.clear = AsyncMock()
        element.is_checked = AsyncMock(return_value=False)
        element.bounding_box = AsyncMock(return_value={
            "x": 100, "y": 100, "width": 200, "height": 50
        })
        element._call_function = AsyncMock()
        return element

    @pytest.mark.asyncio
    async def test_fill(self, mock_session, mock_element):
        """Test filling input."""
        from kuromi_browser.actions import FormHandler

        form = FormHandler(mock_session, human_like=False)
        await form.fill(mock_element, "test value", use_keyboard=False)

        mock_element.fill.assert_called_once_with("test value")

    @pytest.mark.asyncio
    async def test_check(self, mock_session, mock_element):
        """Test checking checkbox."""
        from kuromi_browser.actions import FormHandler

        mock_element.is_checked = AsyncMock(return_value=False)

        form = FormHandler(mock_session, human_like=False)
        await form.check(mock_element, use_click=False)

        mock_element._call_function.assert_called()


class TestActionChain:
    """Tests for ActionChain."""

    @pytest.fixture
    def mock_session(self):
        """Create mock CDP session."""
        session = AsyncMock()
        session.send = AsyncMock(return_value={
            "result": {
                "value": {
                    "x": 0, "y": 0,
                    "max_x": 1000, "max_y": 5000,
                    "width": 1920, "height": 1080,
                }
            }
        })
        return session

    @pytest.mark.asyncio
    async def test_chain_actions(self, mock_session):
        """Test chaining multiple actions."""
        from kuromi_browser.actions import ActionChain

        chain = ActionChain(mock_session, human_like=False)

        # Queue actions
        chain.move_to(100, 100).click().wait(0.01)

        # Check actions queued
        assert len(chain._actions) == 3

        # Perform
        await chain.perform()

        # Check actions cleared
        assert len(chain._actions) == 0

    @pytest.mark.asyncio
    async def test_reset(self, mock_session):
        """Test resetting action queue."""
        from kuromi_browser.actions import ActionChain

        chain = ActionChain(mock_session)
        chain.click().type("test")

        assert len(chain._actions) == 2

        chain.reset()
        assert len(chain._actions) == 0

    def test_create_action_chain(self, mock_session):
        """Test factory function."""
        from kuromi_browser.actions import create_action_chain

        chain = create_action_chain(mock_session, human_like=True)
        assert chain is not None
        assert chain._human_like is True


class TestEnums:
    """Tests for enum types."""

    def test_mouse_button(self):
        """Test MouseButton enum."""
        from kuromi_browser.actions import MouseButton

        assert MouseButton.LEFT.value == "left"
        assert MouseButton.RIGHT.value == "right"
        assert MouseButton.MIDDLE.value == "middle"

    def test_key_modifier(self):
        """Test KeyModifier enum."""
        from kuromi_browser.actions import KeyModifier

        assert KeyModifier.NONE == 0
        assert KeyModifier.ALT == 1
        assert KeyModifier.CTRL == 2
        assert KeyModifier.META == 4
        assert KeyModifier.SHIFT == 8

    def test_scroll_behavior(self):
        """Test ScrollBehavior enum."""
        from kuromi_browser.actions import ScrollBehavior

        assert ScrollBehavior.AUTO.value == "auto"
        assert ScrollBehavior.SMOOTH.value == "smooth"
        assert ScrollBehavior.INSTANT.value == "instant"

    def test_scroll_alignment(self):
        """Test ScrollAlignment enum."""
        from kuromi_browser.actions import ScrollAlignment

        assert ScrollAlignment.START.value == "start"
        assert ScrollAlignment.CENTER.value == "center"
        assert ScrollAlignment.END.value == "end"
        assert ScrollAlignment.NEAREST.value == "nearest"

    def test_input_type(self):
        """Test InputType enum."""
        from kuromi_browser.actions import InputType

        assert InputType.TEXT.value == "text"
        assert InputType.PASSWORD.value == "password"
        assert InputType.EMAIL.value == "email"
        assert InputType.FILE.value == "file"
        assert InputType.CHECKBOX.value == "checkbox"


class TestKeyDefinitions:
    """Tests for key definitions."""

    def test_key_definitions_exist(self):
        """Test KEY_DEFINITIONS has common keys."""
        from kuromi_browser.actions import KEY_DEFINITIONS

        assert "Enter" in KEY_DEFINITIONS
        assert "Tab" in KEY_DEFINITIONS
        assert "Escape" in KEY_DEFINITIONS
        assert "Backspace" in KEY_DEFINITIONS
        assert "ArrowUp" in KEY_DEFINITIONS
        assert "F1" in KEY_DEFINITIONS

    def test_key_definition_structure(self):
        """Test key definition has required fields."""
        from kuromi_browser.actions import KEY_DEFINITIONS

        enter_def = KEY_DEFINITIONS["Enter"]
        assert "key" in enter_def
        assert "code" in enter_def
        assert "keyCode" in enter_def


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
