"""
Actions & Interactions module for kuromi-browser.

Provides high-level APIs for browser automation:
- Mouse actions (click, drag, hover, scroll)
- Keyboard actions (type, press, shortcuts)
- Form handling (input, select, checkbox, file upload)
- Scroll control (smooth scroll, scroll into view)
- Action chaining (fluent API)
"""

from kuromi_browser.actions.chain import ActionChain, create_action_chain
from kuromi_browser.actions.forms import (
    FormField,
    FormHandler,
    InputType,
    SelectOption,
)
from kuromi_browser.actions.keyboard import (
    KEY_DEFINITIONS,
    KeyboardController,
    KeyboardState,
    KeyModifier,
)
from kuromi_browser.actions.mouse import (
    MouseButton,
    MouseController,
    MousePosition,
)
from kuromi_browser.actions.scroll import (
    ScrollAlignment,
    ScrollBehavior,
    ScrollController,
    ScrollPosition,
)

__all__ = [
    # Chain
    "ActionChain",
    "create_action_chain",
    # Mouse
    "MouseController",
    "MouseButton",
    "MousePosition",
    # Keyboard
    "KeyboardController",
    "KeyModifier",
    "KeyboardState",
    "KEY_DEFINITIONS",
    # Forms
    "FormHandler",
    "FormField",
    "SelectOption",
    "InputType",
    # Scroll
    "ScrollController",
    "ScrollBehavior",
    "ScrollAlignment",
    "ScrollPosition",
]
