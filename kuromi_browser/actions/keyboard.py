"""
Keyboard Actions Controller for kuromi-browser.

Provides high-level keyboard interaction APIs using CDP Input domain.
Integrates with HumanKeyboard for stealth human-like typing.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp.session import CDPSession
    from kuromi_browser.dom.element import Element

from kuromi_browser.stealth.behavior.keyboard import HumanKeyboard, TYPING_SPEED_NORMAL


class KeyModifier(int, Enum):
    """Keyboard modifier flags."""

    NONE = 0
    ALT = 1
    CTRL = 2
    META = 4  # Command on Mac
    SHIFT = 8


# Special key mappings to CDP key identifiers
KEY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Function keys
    "F1": {"key": "F1", "code": "F1", "keyCode": 112},
    "F2": {"key": "F2", "code": "F2", "keyCode": 113},
    "F3": {"key": "F3", "code": "F3", "keyCode": 114},
    "F4": {"key": "F4", "code": "F4", "keyCode": 115},
    "F5": {"key": "F5", "code": "F5", "keyCode": 116},
    "F6": {"key": "F6", "code": "F6", "keyCode": 117},
    "F7": {"key": "F7", "code": "F7", "keyCode": 118},
    "F8": {"key": "F8", "code": "F8", "keyCode": 119},
    "F9": {"key": "F9", "code": "F9", "keyCode": 120},
    "F10": {"key": "F10", "code": "F10", "keyCode": 121},
    "F11": {"key": "F11", "code": "F11", "keyCode": 122},
    "F12": {"key": "F12", "code": "F12", "keyCode": 123},
    # Navigation
    "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp", "keyCode": 38},
    "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown", "keyCode": 40},
    "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft", "keyCode": 37},
    "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "keyCode": 39},
    "Home": {"key": "Home", "code": "Home", "keyCode": 36},
    "End": {"key": "End", "code": "End", "keyCode": 35},
    "PageUp": {"key": "PageUp", "code": "PageUp", "keyCode": 33},
    "PageDown": {"key": "PageDown", "code": "PageDown", "keyCode": 34},
    # Editing
    "Backspace": {"key": "Backspace", "code": "Backspace", "keyCode": 8},
    "Delete": {"key": "Delete", "code": "Delete", "keyCode": 46},
    "Insert": {"key": "Insert", "code": "Insert", "keyCode": 45},
    # Whitespace
    "Enter": {"key": "Enter", "code": "Enter", "keyCode": 13, "text": "\r"},
    "Tab": {"key": "Tab", "code": "Tab", "keyCode": 9, "text": "\t"},
    "Space": {"key": " ", "code": "Space", "keyCode": 32, "text": " "},
    # Modifiers
    "Shift": {"key": "Shift", "code": "ShiftLeft", "keyCode": 16},
    "ShiftLeft": {"key": "Shift", "code": "ShiftLeft", "keyCode": 16},
    "ShiftRight": {"key": "Shift", "code": "ShiftRight", "keyCode": 16},
    "Control": {"key": "Control", "code": "ControlLeft", "keyCode": 17},
    "ControlLeft": {"key": "Control", "code": "ControlLeft", "keyCode": 17},
    "ControlRight": {"key": "Control", "code": "ControlRight", "keyCode": 17},
    "Alt": {"key": "Alt", "code": "AltLeft", "keyCode": 18},
    "AltLeft": {"key": "Alt", "code": "AltLeft", "keyCode": 18},
    "AltRight": {"key": "Alt", "code": "AltRight", "keyCode": 18},
    "Meta": {"key": "Meta", "code": "MetaLeft", "keyCode": 91},
    "MetaLeft": {"key": "Meta", "code": "MetaLeft", "keyCode": 91},
    "MetaRight": {"key": "Meta", "code": "MetaRight", "keyCode": 92},
    # Special
    "Escape": {"key": "Escape", "code": "Escape", "keyCode": 27},
    "CapsLock": {"key": "CapsLock", "code": "CapsLock", "keyCode": 20},
    "NumLock": {"key": "NumLock", "code": "NumLock", "keyCode": 144},
    "ScrollLock": {"key": "ScrollLock", "code": "ScrollLock", "keyCode": 145},
    "PrintScreen": {"key": "PrintScreen", "code": "PrintScreen", "keyCode": 44},
    "Pause": {"key": "Pause", "code": "Pause", "keyCode": 19},
    "ContextMenu": {"key": "ContextMenu", "code": "ContextMenu", "keyCode": 93},
}

# Alias mappings
KEY_ALIASES: Dict[str, str] = {
    "Up": "ArrowUp",
    "Down": "ArrowDown",
    "Left": "ArrowLeft",
    "Right": "ArrowRight",
    "Return": "Enter",
    "Esc": "Escape",
    "Ctrl": "Control",
    "Cmd": "Meta",
    "Command": "Meta",
    "Win": "Meta",
    "Windows": "Meta",
    "Option": "Alt",
    "Del": "Delete",
    "Ins": "Insert",
    "PgUp": "PageUp",
    "PgDn": "PageDown",
    "PgDown": "PageDown",
}


def _resolve_key(key: str) -> str:
    """Resolve key alias to standard name."""
    return KEY_ALIASES.get(key, key)


def _get_key_definition(key: str) -> Dict[str, Any]:
    """Get key definition for CDP."""
    resolved = _resolve_key(key)

    if resolved in KEY_DEFINITIONS:
        return KEY_DEFINITIONS[resolved].copy()

    # Single character
    if len(resolved) == 1:
        char = resolved
        code = f"Key{char.upper()}" if char.isalpha() else f"Digit{char}" if char.isdigit() else ""
        return {
            "key": char,
            "code": code,
            "text": char,
            "keyCode": ord(char.upper()) if char.isalpha() else ord(char),
        }

    # Unknown key - return as-is
    return {"key": resolved, "code": resolved, "keyCode": 0}


@dataclass
class KeyboardState:
    """Current keyboard state."""

    pressed_keys: Set[str]
    modifiers: int

    def is_pressed(self, key: str) -> bool:
        return _resolve_key(key) in self.pressed_keys


class KeyboardController:
    """High-level keyboard actions controller.

    Provides typing, key press, shortcuts, and key combinations
    with optional human-like behavior.

    Example:
        keyboard = KeyboardController(cdp_session)
        await keyboard.type("Hello World!")
        await keyboard.press("Enter")
        await keyboard.shortcut("Control", "a")  # Select all
    """

    def __init__(
        self,
        cdp_session: "CDPSession",
        *,
        human_like: bool = True,
        typing_speed: Optional[float] = None,
    ) -> None:
        """Initialize KeyboardController.

        Args:
            cdp_session: CDP session for sending commands.
            human_like: Use human-like typing delays.
            typing_speed: Characters per minute (None for default ~250).
        """
        self._session = cdp_session
        self._human_like = human_like
        self._typing_speed = typing_speed or TYPING_SPEED_NORMAL
        self._state = KeyboardState(pressed_keys=set(), modifiers=0)

    @property
    def state(self) -> KeyboardState:
        """Get current keyboard state."""
        return self._state

    def _get_modifiers(self) -> int:
        """Calculate current modifier flags."""
        modifiers = 0
        if "Alt" in self._state.pressed_keys:
            modifiers |= KeyModifier.ALT
        if "Control" in self._state.pressed_keys:
            modifiers |= KeyModifier.CTRL
        if "Meta" in self._state.pressed_keys:
            modifiers |= KeyModifier.META
        if "Shift" in self._state.pressed_keys:
            modifiers |= KeyModifier.SHIFT
        return modifiers

    async def _dispatch_key_event(
        self,
        event_type: str,
        key_def: Dict[str, Any],
        modifiers: Optional[int] = None,
    ) -> None:
        """Dispatch a key event via CDP."""
        params: Dict[str, Any] = {
            "type": event_type,
            "modifiers": modifiers if modifiers is not None else self._get_modifiers(),
        }

        if "key" in key_def:
            params["key"] = key_def["key"]
        if "code" in key_def:
            params["code"] = key_def["code"]
        if "keyCode" in key_def:
            params["windowsVirtualKeyCode"] = key_def["keyCode"]
            params["nativeVirtualKeyCode"] = key_def["keyCode"]

        # Add text for char events
        if event_type == "keyDown" and "text" in key_def:
            params["text"] = key_def["text"]

        await self._session.send("Input.dispatchKeyEvent", params)

    async def down(
        self,
        key: str,
        *,
        modifiers: Optional[int] = None,
    ) -> "KeyboardController":
        """Press a key down (without release).

        Args:
            key: Key to press.
            modifiers: Optional modifier override.

        Returns:
            Self for chaining.
        """
        resolved = _resolve_key(key)
        key_def = _get_key_definition(resolved)

        await self._dispatch_key_event("keyDown", key_def, modifiers)

        # Track modifier state
        if resolved in ("Shift", "ShiftLeft", "ShiftRight"):
            self._state.pressed_keys.add("Shift")
        elif resolved in ("Control", "ControlLeft", "ControlRight"):
            self._state.pressed_keys.add("Control")
        elif resolved in ("Alt", "AltLeft", "AltRight"):
            self._state.pressed_keys.add("Alt")
        elif resolved in ("Meta", "MetaLeft", "MetaRight"):
            self._state.pressed_keys.add("Meta")
        else:
            self._state.pressed_keys.add(resolved)

        return self

    async def up(
        self,
        key: str,
        *,
        modifiers: Optional[int] = None,
    ) -> "KeyboardController":
        """Release a key.

        Args:
            key: Key to release.
            modifiers: Optional modifier override.

        Returns:
            Self for chaining.
        """
        resolved = _resolve_key(key)
        key_def = _get_key_definition(resolved)

        await self._dispatch_key_event("keyUp", key_def, modifiers)

        # Update modifier state
        if resolved in ("Shift", "ShiftLeft", "ShiftRight"):
            self._state.pressed_keys.discard("Shift")
        elif resolved in ("Control", "ControlLeft", "ControlRight"):
            self._state.pressed_keys.discard("Control")
        elif resolved in ("Alt", "AltLeft", "AltRight"):
            self._state.pressed_keys.discard("Alt")
        elif resolved in ("Meta", "MetaLeft", "MetaRight"):
            self._state.pressed_keys.discard("Meta")
        else:
            self._state.pressed_keys.discard(resolved)

        return self

    async def press(
        self,
        key: str,
        *,
        delay: Optional[float] = None,
        modifiers: Optional[int] = None,
    ) -> "KeyboardController":
        """Press and release a key.

        Args:
            key: Key to press.
            delay: Hold duration (None for auto).
            modifiers: Optional modifier override.

        Returns:
            Self for chaining.
        """
        resolved = _resolve_key(key)

        if self._human_like:
            await HumanKeyboard.press_key(
                self._session,
                resolved,
                hold_duration=delay,
            )
        else:
            await self.down(key, modifiers=modifiers)

            if delay:
                await asyncio.sleep(delay)
            else:
                await asyncio.sleep(random.uniform(0.02, 0.05))

            await self.up(key, modifiers=modifiers)

        return self

    async def type(
        self,
        text: str,
        *,
        delay: Optional[float] = None,
        include_typos: bool = False,
    ) -> "KeyboardController":
        """Type text with realistic timing.

        Args:
            text: Text to type.
            delay: Delay between keystrokes (None for auto).
            include_typos: Occasionally make and correct typos.

        Returns:
            Self for chaining.
        """
        if self._human_like:
            await HumanKeyboard.type_text(
                self._session,
                text,
                speed=self._typing_speed,
                include_typos=include_typos,
            )
        else:
            for char in text:
                await self._session.send(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyDown",
                        "key": char,
                        "text": char,
                    },
                )
                await self._session.send(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyUp",
                        "key": char,
                    },
                )

                if delay:
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(0.02)

        return self

    async def insert_text(self, text: str) -> "KeyboardController":
        """Insert text directly (bypasses keyboard events).

        This is faster but may be detected as non-human.
        For human-like typing, use type() instead.

        Args:
            text: Text to insert.

        Returns:
            Self for chaining.
        """
        await self._session.send("Input.insertText", {"text": text})
        return self

    async def shortcut(self, *keys: str) -> "KeyboardController":
        """Press a keyboard shortcut (e.g., Ctrl+C).

        Args:
            *keys: Keys to press together (modifiers first, then main key).

        Returns:
            Self for chaining.
        """
        if not keys:
            return self

        if self._human_like:
            await HumanKeyboard.press_combination(self._session, *keys)
        else:
            # Press all keys down in order
            for key in keys:
                await self.down(key)
                await asyncio.sleep(random.uniform(0.02, 0.05))

            # Release in reverse order
            for key in reversed(keys):
                await asyncio.sleep(random.uniform(0.02, 0.05))
                await self.up(key)

        return self

    async def combo(self, combo_string: str) -> "KeyboardController":
        """Press a key combination specified as string.

        Args:
            combo_string: Combination like "Ctrl+Shift+A" or "Meta+C".

        Returns:
            Self for chaining.
        """
        keys = [k.strip() for k in combo_string.split("+")]
        return await self.shortcut(*keys)

    # Common shortcuts

    async def select_all(self) -> "KeyboardController":
        """Select all (Ctrl+A / Cmd+A)."""
        return await self.shortcut("Control", "a")

    async def copy(self) -> "KeyboardController":
        """Copy (Ctrl+C / Cmd+C)."""
        return await self.shortcut("Control", "c")

    async def cut(self) -> "KeyboardController":
        """Cut (Ctrl+X / Cmd+X)."""
        return await self.shortcut("Control", "x")

    async def paste(self) -> "KeyboardController":
        """Paste (Ctrl+V / Cmd+V)."""
        return await self.shortcut("Control", "v")

    async def undo(self) -> "KeyboardController":
        """Undo (Ctrl+Z / Cmd+Z)."""
        return await self.shortcut("Control", "z")

    async def redo(self) -> "KeyboardController":
        """Redo (Ctrl+Y / Cmd+Shift+Z)."""
        return await self.shortcut("Control", "y")

    async def save(self) -> "KeyboardController":
        """Save (Ctrl+S / Cmd+S)."""
        return await self.shortcut("Control", "s")

    async def find(self) -> "KeyboardController":
        """Find (Ctrl+F / Cmd+F)."""
        return await self.shortcut("Control", "f")

    async def close_tab(self) -> "KeyboardController":
        """Close tab (Ctrl+W / Cmd+W)."""
        return await self.shortcut("Control", "w")

    async def new_tab(self) -> "KeyboardController":
        """New tab (Ctrl+T / Cmd+T)."""
        return await self.shortcut("Control", "t")

    async def refresh(self) -> "KeyboardController":
        """Refresh page (F5 / Ctrl+R)."""
        return await self.shortcut("Control", "r")

    async def hard_refresh(self) -> "KeyboardController":
        """Hard refresh (Ctrl+Shift+R)."""
        return await self.shortcut("Control", "Shift", "r")

    async def clear_field(self) -> "KeyboardController":
        """Clear input field (Select All + Delete)."""
        await self.select_all()
        await asyncio.sleep(0.05)
        return await self.press("Delete")

    async def focus_element(self, element: "Element") -> "KeyboardController":
        """Focus an element before typing.

        Args:
            element: Element to focus.

        Returns:
            Self for chaining.
        """
        await element.focus()
        return self

    async def type_into(
        self,
        element: "Element",
        text: str,
        *,
        clear_first: bool = True,
        delay: Optional[float] = None,
    ) -> "KeyboardController":
        """Type text into an element.

        Args:
            element: Element to type into.
            text: Text to type.
            clear_first: Clear existing content first.
            delay: Delay between keystrokes.

        Returns:
            Self for chaining.
        """
        await element.focus()

        if clear_first:
            await self.clear_field()
            await asyncio.sleep(0.05)

        return await self.type(text, delay=delay)

    def set_human_like(self, enabled: bool) -> "KeyboardController":
        """Enable or disable human-like typing.

        Args:
            enabled: Enable human-like behavior.

        Returns:
            Self for chaining.
        """
        self._human_like = enabled
        return self

    def set_typing_speed(self, speed: float) -> "KeyboardController":
        """Set typing speed.

        Args:
            speed: Characters per minute.

        Returns:
            Self for chaining.
        """
        self._typing_speed = speed
        return self


__all__ = ["KeyboardController", "KeyModifier", "KeyboardState", "KEY_DEFINITIONS"]
