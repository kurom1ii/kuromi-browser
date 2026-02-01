"""
Human-like mouse movement simulation.

Generates realistic mouse paths using Bezier curves and
adds natural timing variations to simulate human behavior.
"""

import math
import random
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Point:
    """A 2D point."""

    x: float
    y: float

    def __iter__(self):
        yield self.x
        yield self.y

    def distance_to(self, other: "Point") -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class MousePath:
    """A mouse movement path with timing information."""

    points: list[Point]
    durations: list[float]  # Time between each point in seconds

    def __len__(self) -> int:
        return len(self.points)

    @property
    def total_duration(self) -> float:
        """Total duration of the path in seconds."""
        return sum(self.durations)


class HumanMouse:
    """Generate human-like mouse movements.

    Uses Bezier curves with randomized control points and
    variable speeds to simulate natural mouse movement.
    """

    # Movement speed ranges (pixels per second)
    SPEED_MIN = 300
    SPEED_MAX = 800

    # Jitter ranges (pixels)
    JITTER_MIN = 0
    JITTER_MAX = 3

    # Control point deviation range (pixels)
    CONTROL_DEVIATION_MIN = 20
    CONTROL_DEVIATION_MAX = 100

    @staticmethod
    def bezier_point(
        t: float,
        p0: Point,
        p1: Point,
        p2: Point,
        p3: Point,
    ) -> Point:
        """Calculate a point on a cubic Bezier curve.

        Args:
            t: Parameter from 0 to 1
            p0: Start point
            p1: First control point
            p2: Second control point
            p3: End point

        Returns:
            Point on the curve
        """
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt
        t2 = t * t
        t3 = t2 * t

        x = mt3 * p0.x + 3 * mt2 * t * p1.x + 3 * mt * t2 * p2.x + t3 * p3.x
        y = mt3 * p0.y + 3 * mt2 * t * p1.y + 3 * mt * t2 * p2.y + t3 * p3.y

        return Point(x, y)

    @classmethod
    def bezier_curve(
        cls,
        start: tuple[int, int],
        end: tuple[int, int],
        num_points: int = 50,
        control_deviation: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        """Generate a curved path between two points using cubic Bezier.

        Args:
            start: Starting position (x, y)
            end: Ending position (x, y)
            num_points: Number of points in the path
            control_deviation: Range for control point deviation

        Returns:
            List of (x, y) points forming the path
        """
        if control_deviation is None:
            control_deviation = (
                cls.CONTROL_DEVIATION_MIN,
                cls.CONTROL_DEVIATION_MAX,
            )

        p0 = Point(float(start[0]), float(start[1]))
        p3 = Point(float(end[0]), float(end[1]))

        # Calculate distance for proportional deviation
        distance = p0.distance_to(p3)
        deviation = min(
            max(control_deviation[0], distance * 0.2),
            control_deviation[1],
        )

        # Generate random control points
        # First control point is closer to start
        cp1_x = p0.x + (p3.x - p0.x) * random.uniform(0.2, 0.4)
        cp1_y = p0.y + (p3.y - p0.y) * random.uniform(0.2, 0.4)
        cp1_x += random.uniform(-deviation, deviation)
        cp1_y += random.uniform(-deviation, deviation)
        p1 = Point(cp1_x, cp1_y)

        # Second control point is closer to end
        cp2_x = p0.x + (p3.x - p0.x) * random.uniform(0.6, 0.8)
        cp2_y = p0.y + (p3.y - p0.y) * random.uniform(0.6, 0.8)
        cp2_x += random.uniform(-deviation, deviation)
        cp2_y += random.uniform(-deviation, deviation)
        p2 = Point(cp2_x, cp2_y)

        # Generate points along the curve
        points = []
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            point = cls.bezier_point(t, p0, p1, p2, p3)
            points.append((int(round(point.x)), int(round(point.y))))

        return points

    @classmethod
    def generate_path(
        cls,
        start: tuple[int, int],
        end: tuple[int, int],
        speed: Optional[float] = None,
        with_overshoot: bool = False,
    ) -> MousePath:
        """Generate a complete mouse path with timing.

        Args:
            start: Starting position (x, y)
            end: Ending position (x, y)
            speed: Movement speed in pixels/second (random if None)
            with_overshoot: Whether to overshoot the target slightly

        Returns:
            MousePath with points and timing
        """
        if speed is None:
            speed = random.uniform(cls.SPEED_MIN, cls.SPEED_MAX)

        # Calculate distance and number of points
        distance = math.sqrt(
            (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2
        )

        # More points for longer distances
        num_points = max(10, min(100, int(distance / 10)))

        # Generate base path
        if with_overshoot and distance > 50:
            # Overshoot by 5-15%
            overshoot_factor = random.uniform(1.05, 1.15)
            overshoot_x = int(start[0] + (end[0] - start[0]) * overshoot_factor)
            overshoot_y = int(start[1] + (end[1] - start[1]) * overshoot_factor)

            # Path to overshoot point
            points1 = cls.bezier_curve(start, (overshoot_x, overshoot_y), num_points - 5)
            # Correction path back to target
            points2 = cls.bezier_curve(
                (overshoot_x, overshoot_y),
                end,
                5,
                control_deviation=(5, 20),
            )
            raw_points = points1 + points2[1:]  # Avoid duplicate point
        else:
            raw_points = cls.bezier_curve(start, end, num_points)

        # Add jitter
        points = []
        for i, (x, y) in enumerate(raw_points):
            if i == 0 or i == len(raw_points) - 1:
                # No jitter on start and end points
                points.append(Point(float(x), float(y)))
            else:
                jx = x + random.uniform(-cls.JITTER_MAX, cls.JITTER_MAX)
                jy = y + random.uniform(-cls.JITTER_MAX, cls.JITTER_MAX)
                points.append(Point(jx, jy))

        # Calculate timing with easing
        durations = []
        for i in range(len(points) - 1):
            # Calculate distance between consecutive points
            segment_dist = points[i].distance_to(points[i + 1])

            # Apply easing: slower at start and end
            t = i / (len(points) - 1)
            # Ease in-out function
            ease = 0.5 - 0.5 * math.cos(math.pi * t)
            # Speed varies: slower at edges, faster in middle
            current_speed = speed * (0.5 + ease)

            # Calculate duration for this segment
            duration = segment_dist / current_speed if current_speed > 0 else 0.01
            # Add some randomness
            duration *= random.uniform(0.8, 1.2)
            durations.append(max(0.001, duration))

        return MousePath(points=points, durations=durations)

    @classmethod
    async def move(
        cls,
        cdp_session: Any,
        start: tuple[int, int],
        end: tuple[int, int],
        speed: Optional[float] = None,
    ) -> None:
        """Move mouse from start to end with human-like motion.

        Args:
            cdp_session: CDP session with send() method
            start: Starting position (x, y)
            end: Ending position (x, y)
            speed: Movement speed (pixels/second)
        """
        import asyncio

        path = cls.generate_path(start, end, speed)

        for i, point in enumerate(path.points):
            await cdp_session.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseMoved",
                    "x": int(point.x),
                    "y": int(point.y),
                },
            )

            if i < len(path.durations):
                await asyncio.sleep(path.durations[i])

    @classmethod
    async def click(
        cls,
        cdp_session: Any,
        x: int,
        y: int,
        button: str = "left",
        click_count: int = 1,
        move_to: bool = True,
        current_pos: Optional[tuple[int, int]] = None,
    ) -> None:
        """Perform a human-like click at the specified position.

        Args:
            cdp_session: CDP session with send() method
            x: X coordinate to click
            y: Y coordinate to click
            button: Mouse button ("left", "right", "middle")
            click_count: Number of clicks (1 for single, 2 for double)
            move_to: Whether to move mouse to position first
            current_pos: Current mouse position (for movement)
        """
        import asyncio

        if move_to and current_pos:
            await cls.move(cdp_session, current_pos, (x, y))

        # Random delay before clicking
        await asyncio.sleep(random.uniform(0.05, 0.15))

        for i in range(click_count):
            # Mouse down
            await cdp_session.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mousePressed",
                    "x": x,
                    "y": y,
                    "button": button,
                    "clickCount": i + 1,
                },
            )

            # Random hold time
            await asyncio.sleep(random.uniform(0.05, 0.12))

            # Mouse up
            await cdp_session.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseReleased",
                    "x": x,
                    "y": y,
                    "button": button,
                    "clickCount": i + 1,
                },
            )

            if i < click_count - 1:
                # Delay between clicks for double/triple click
                await asyncio.sleep(random.uniform(0.08, 0.15))

    @classmethod
    async def scroll(
        cls,
        cdp_session: Any,
        x: int,
        y: int,
        delta_x: int = 0,
        delta_y: int = 0,
        steps: int = 5,
    ) -> None:
        """Perform a human-like scroll.

        Args:
            cdp_session: CDP session with send() method
            x: X coordinate for scroll
            y: Y coordinate for scroll
            delta_x: Horizontal scroll amount
            delta_y: Vertical scroll amount
            steps: Number of scroll steps
        """
        import asyncio

        step_x = delta_x / steps if steps > 0 else delta_x
        step_y = delta_y / steps if steps > 0 else delta_y

        for _ in range(steps):
            # Add some variation to each step
            current_dx = step_x * random.uniform(0.8, 1.2)
            current_dy = step_y * random.uniform(0.8, 1.2)

            await cdp_session.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseWheel",
                    "x": x,
                    "y": y,
                    "deltaX": int(current_dx),
                    "deltaY": int(current_dy),
                },
            )

            # Random delay between scroll steps
            await asyncio.sleep(random.uniform(0.02, 0.05))

    @classmethod
    async def drag(
        cls,
        cdp_session: Any,
        start: tuple[int, int],
        end: tuple[int, int],
        button: str = "left",
    ) -> None:
        """Perform a human-like drag operation.

        Args:
            cdp_session: CDP session with send() method
            start: Starting position (x, y)
            end: Ending position (x, y)
            button: Mouse button to hold during drag
        """
        import asyncio

        # Move to start position
        await cdp_session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseMoved",
                "x": start[0],
                "y": start[1],
            },
        )

        await asyncio.sleep(random.uniform(0.05, 0.1))

        # Press mouse button
        await cdp_session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mousePressed",
                "x": start[0],
                "y": start[1],
                "button": button,
                "clickCount": 1,
            },
        )

        await asyncio.sleep(random.uniform(0.05, 0.1))

        # Generate and follow path
        path = cls.generate_path(start, end)

        for i, point in enumerate(path.points[1:], 1):
            await cdp_session.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseMoved",
                    "x": int(point.x),
                    "y": int(point.y),
                    "button": button,
                },
            )

            if i < len(path.durations):
                await asyncio.sleep(path.durations[i])

        await asyncio.sleep(random.uniform(0.05, 0.1))

        # Release mouse button
        await cdp_session.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseReleased",
                "x": end[0],
                "y": end[1],
                "button": button,
                "clickCount": 1,
            },
        )
