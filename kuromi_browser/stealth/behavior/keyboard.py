"""
Human-like keyboard input simulation.

Simulates realistic typing patterns with variable delays,
typos, and corrections to appear more human-like.
"""

import random
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class KeyTiming:
    """Timing information for a keystroke."""

    key: str
    delay_before: float  # Delay before pressing this key (seconds)
    hold_duration: float  # How long the key is held (seconds)


# Average typing speeds (characters per minute)
TYPING_SPEED_SLOW = 150
TYPING_SPEED_NORMAL = 250
TYPING_SPEED_FAST = 400

# Key position map for QWERTY keyboard (row, col)
QWERTY_LAYOUT = {
    # Row 0 (numbers)
    '`': (0, 0), '1': (0, 1), '2': (0, 2), '3': (0, 3), '4': (0, 4),
    '5': (0, 5), '6': (0, 6), '7': (0, 7), '8': (0, 8), '9': (0, 9),
    '0': (0, 10), '-': (0, 11), '=': (0, 12),
    # Row 1 (qwerty)
    'q': (1, 0), 'w': (1, 1), 'e': (1, 2), 'r': (1, 3), 't': (1, 4),
    'y': (1, 5), 'u': (1, 6), 'i': (1, 7), 'o': (1, 8), 'p': (1, 9),
    '[': (1, 10), ']': (1, 11), '\\': (1, 12),
    # Row 2 (asdf)
    'a': (2, 0), 's': (2, 1), 'd': (2, 2), 'f': (2, 3), 'g': (2, 4),
    'h': (2, 5), 'j': (2, 6), 'k': (2, 7), 'l': (2, 8), ';': (2, 9),
    "'": (2, 10),
    # Row 3 (zxcv)
    'z': (3, 0), 'x': (3, 1), 'c': (3, 2), 'v': (3, 3), 'b': (3, 4),
    'n': (3, 5), 'm': (3, 6), ',': (3, 7), '.': (3, 8), '/': (3, 9),
    # Space
    ' ': (4, 5),
}


def _key_distance(key1: str, key2: str) -> float:
    """Calculate approximate distance between two keys."""
    k1 = key1.lower()
    k2 = key2.lower()

    pos1 = QWERTY_LAYOUT.get(k1, (2, 5))
    pos2 = QWERTY_LAYOUT.get(k2, (2, 5))

    # Euclidean distance
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5


def _get_adjacent_keys(key: str) -> list[str]:
    """Get keys adjacent to the given key on QWERTY keyboard."""
    key = key.lower()
    if key not in QWERTY_LAYOUT:
        return []

    row, col = QWERTY_LAYOUT[key]
    adjacent = []

    for k, (r, c) in QWERTY_LAYOUT.items():
        if k != key and abs(r - row) <= 1 and abs(c - col) <= 1:
            adjacent.append(k)

    return adjacent


class HumanKeyboard:
    """Generate human-like keyboard input.

    Simulates realistic typing with variable speeds, occasional
    typos, and natural pauses.
    """

    # Default timing parameters
    MIN_DELAY = 0.03  # Minimum delay between keystrokes (seconds)
    MAX_DELAY = 0.15  # Maximum delay between keystrokes (seconds)
    HOLD_MIN = 0.02   # Minimum key hold duration
    HOLD_MAX = 0.08   # Maximum key hold duration

    # Typo probability (0.0 to 1.0)
    TYPO_PROBABILITY = 0.02

    # Pause probability at word boundaries
    WORD_PAUSE_PROBABILITY = 0.3
    WORD_PAUSE_MIN = 0.1
    WORD_PAUSE_MAX = 0.5

    @classmethod
    def generate_timing(
        cls,
        text: str,
        speed: Optional[float] = None,
        include_typos: bool = False,
    ) -> list[KeyTiming]:
        """Generate timing information for typing text.

        Args:
            text: Text to type
            speed: Characters per minute (uses TYPING_SPEED_NORMAL if None)
            include_typos: Whether to occasionally include typos

        Returns:
            List of KeyTiming objects
        """
        if speed is None:
            speed = TYPING_SPEED_NORMAL

        # Calculate base delay from speed
        base_delay = 60.0 / speed

        timings = []
        prev_key = None

        for i, char in enumerate(text):
            # Base delay with some randomness
            delay = base_delay * random.uniform(0.7, 1.5)

            # Adjust delay based on key distance
            if prev_key:
                distance = _key_distance(prev_key, char)
                delay *= 1 + (distance * 0.05)

            # Add extra delay at word boundaries
            if char == ' ' and random.random() < cls.WORD_PAUSE_PROBABILITY:
                delay += random.uniform(cls.WORD_PAUSE_MIN, cls.WORD_PAUSE_MAX)

            # Add extra delay after punctuation
            if prev_key and prev_key in '.!?':
                delay += random.uniform(0.2, 0.5)

            # Clamp delay
            delay = max(cls.MIN_DELAY, min(delay, cls.MAX_DELAY * 3))

            # Hold duration
            hold = random.uniform(cls.HOLD_MIN, cls.HOLD_MAX)

            # Possibly add a typo
            if include_typos and random.random() < cls.TYPO_PROBABILITY:
                adjacent = _get_adjacent_keys(char)
                if adjacent:
                    typo_key = random.choice(adjacent)
                    # Add the typo
                    timings.append(KeyTiming(
                        key=typo_key,
                        delay_before=delay,
                        hold_duration=hold,
                    ))
                    # Add backspace to correct it
                    timings.append(KeyTiming(
                        key='Backspace',
                        delay_before=random.uniform(0.1, 0.3),
                        hold_duration=hold,
                    ))
                    # The correct key comes with a shorter delay
                    delay = random.uniform(0.05, 0.15)

            timings.append(KeyTiming(
                key=char,
                delay_before=delay,
                hold_duration=hold,
            ))

            prev_key = char

        return timings

    @classmethod
    async def type_text(
        cls,
        cdp_session: Any,
        text: str,
        speed: Optional[float] = None,
        include_typos: bool = False,
    ) -> None:
        """Type text with human-like timing.

        Args:
            cdp_session: CDP session with send() method
            text: Text to type
            speed: Characters per minute
            include_typos: Whether to include occasional typos
        """
        import asyncio

        timings = cls.generate_timing(text, speed, include_typos)

        for timing in timings:
            # Wait before pressing the key
            await asyncio.sleep(timing.delay_before)

            # Send the keystroke
            if len(timing.key) == 1:
                # Regular character
                await cdp_session.send(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyDown",
                        "key": timing.key,
                        "text": timing.key,
                    },
                )
                await asyncio.sleep(timing.hold_duration)
                await cdp_session.send(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyUp",
                        "key": timing.key,
                    },
                )
            else:
                # Special key (Backspace, Enter, etc.)
                await cls.press_key(cdp_session, timing.key, timing.hold_duration)

    @classmethod
    async def press_key(
        cls,
        cdp_session: Any,
        key: str,
        hold_duration: Optional[float] = None,
    ) -> None:
        """Press a single key.

        Args:
            cdp_session: CDP session with send() method
            key: Key to press (e.g., 'Enter', 'Tab', 'Escape')
            hold_duration: How long to hold the key
        """
        import asyncio

        if hold_duration is None:
            hold_duration = random.uniform(cls.HOLD_MIN, cls.HOLD_MAX)

        # Map common key names to CDP key identifiers
        key_map = {
            'Enter': ('Enter', '\r'),
            'Tab': ('Tab', '\t'),
            'Backspace': ('Backspace', ''),
            'Delete': ('Delete', ''),
            'Escape': ('Escape', ''),
            'ArrowUp': ('ArrowUp', ''),
            'ArrowDown': ('ArrowDown', ''),
            'ArrowLeft': ('ArrowLeft', ''),
            'ArrowRight': ('ArrowRight', ''),
            'Home': ('Home', ''),
            'End': ('End', ''),
            'PageUp': ('PageUp', ''),
            'PageDown': ('PageDown', ''),
        }

        if key in key_map:
            key_name, text = key_map[key]
        else:
            key_name = key
            text = key if len(key) == 1 else ''

        await cdp_session.send(
            "Input.dispatchKeyEvent",
            {
                "type": "keyDown",
                "key": key_name,
                "text": text,
            },
        )

        await asyncio.sleep(hold_duration)

        await cdp_session.send(
            "Input.dispatchKeyEvent",
            {
                "type": "keyUp",
                "key": key_name,
            },
        )

    @classmethod
    async def press_combination(
        cls,
        cdp_session: Any,
        *keys: str,
    ) -> None:
        """Press a key combination (e.g., Ctrl+A, Ctrl+Shift+V).

        Args:
            cdp_session: CDP session with send() method
            *keys: Keys to press simultaneously
        """
        import asyncio

        # Modifier mapping
        modifiers = {
            'Control': 2,
            'Ctrl': 2,
            'Alt': 1,
            'Shift': 8,
            'Meta': 4,
            'Command': 4,
        }

        modifier_value = 0
        main_key = None

        for key in keys:
            if key in modifiers:
                modifier_value |= modifiers[key]
            else:
                main_key = key

        if main_key is None:
            return

        # Press modifiers first
        for key in keys:
            if key in modifiers:
                await cdp_session.send(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyDown",
                        "key": key,
                        "modifiers": modifier_value,
                    },
                )
                await asyncio.sleep(random.uniform(0.02, 0.05))

        # Press main key
        await cdp_session.send(
            "Input.dispatchKeyEvent",
            {
                "type": "keyDown",
                "key": main_key,
                "text": main_key if len(main_key) == 1 else '',
                "modifiers": modifier_value,
            },
        )

        await asyncio.sleep(random.uniform(0.05, 0.1))

        # Release main key
        await cdp_session.send(
            "Input.dispatchKeyEvent",
            {
                "type": "keyUp",
                "key": main_key,
                "modifiers": modifier_value,
            },
        )

        # Release modifiers in reverse order
        for key in reversed(keys):
            if key in modifiers:
                await asyncio.sleep(random.uniform(0.02, 0.05))
                await cdp_session.send(
                    "Input.dispatchKeyEvent",
                    {
                        "type": "keyUp",
                        "key": key,
                    },
                )

    @classmethod
    async def clear_input(
        cls,
        cdp_session: Any,
    ) -> None:
        """Clear input field using Ctrl+A and Delete.

        Args:
            cdp_session: CDP session with send() method
        """
        await cls.press_combination(cdp_session, 'Control', 'a')
        await cls.press_key(cdp_session, 'Delete')

    @classmethod
    async def paste_text(
        cls,
        cdp_session: Any,
        text: str,
    ) -> None:
        """Paste text (simulates Ctrl+V after setting clipboard).

        Note: This uses insertText which is faster but may be detected.
        For more human-like behavior, use type_text instead.

        Args:
            cdp_session: CDP session with send() method
            text: Text to paste
        """
        await cdp_session.send(
            "Input.insertText",
            {"text": text},
        )
