"""
Screenshot utilities for kuromi-browser.

Provides advanced screenshot functionality including:
- Full page screenshots
- Element screenshots
- Viewport screenshots
- Multiple format support (PNG, JPEG, WebP)
- Scroll stitching for full page capture
"""

from __future__ import annotations

import asyncio
import base64
import io
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPSession
    from kuromi_browser.page import Element


class ImageFormat(str, Enum):
    """Supported image formats."""

    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


@dataclass
class ClipRegion:
    """Region to clip from screenshot."""

    x: float
    y: float
    width: float
    height: float
    scale: float = 1.0

    def to_dict(self) -> dict[str, float]:
        """Convert to CDP clip format."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "scale": self.scale,
        }


@dataclass
class ScreenshotOptions:
    """Screenshot configuration options."""

    format: ImageFormat = ImageFormat.PNG
    quality: int = 80
    full_page: bool = False
    clip: Optional[ClipRegion] = None
    omit_background: bool = False
    optimize_for_speed: bool = False
    from_surface: bool = True
    capture_beyond_viewport: bool = False

    def to_cdp_params(self) -> dict[str, Any]:
        """Convert to CDP parameters."""
        params: dict[str, Any] = {
            "format": self.format.value,
            "fromSurface": self.from_surface,
            "captureBeyondViewport": self.capture_beyond_viewport or self.full_page,
        }

        if self.format in (ImageFormat.JPEG, ImageFormat.WEBP):
            params["quality"] = self.quality

        if self.clip:
            params["clip"] = self.clip.to_dict()

        if self.omit_background:
            params["omitBackground"] = True

        if self.optimize_for_speed:
            params["optimizeForSpeed"] = True

        return params


class ScreenshotCapture:
    """Screenshot capture utility.

    Provides various methods for capturing screenshots with different
    configurations and optimizations.

    Example:
        capture = ScreenshotCapture(cdp_session)

        # Viewport screenshot
        data = await capture.capture_viewport()

        # Full page screenshot
        data = await capture.capture_full_page()

        # Element screenshot
        data = await capture.capture_element(element)

        # Save to file
        await capture.capture_to_file("/tmp/screenshot.png", full_page=True)
    """

    def __init__(self, cdp: "CDPSession") -> None:
        """Initialize screenshot capture.

        Args:
            cdp: CDP session to use for capturing.
        """
        self._cdp = cdp

    async def capture_viewport(
        self,
        *,
        format: ImageFormat = ImageFormat.PNG,
        quality: int = 80,
        omit_background: bool = False,
    ) -> bytes:
        """Capture the current viewport.

        Args:
            format: Image format.
            quality: JPEG/WebP quality (0-100).
            omit_background: Make background transparent.

        Returns:
            Screenshot image data.
        """
        options = ScreenshotOptions(
            format=format,
            quality=quality,
            omit_background=omit_background,
        )

        result = await self._cdp.send(
            "Page.captureScreenshot",
            options.to_cdp_params(),
        )

        return base64.b64decode(result["data"])

    async def capture_full_page(
        self,
        *,
        format: ImageFormat = ImageFormat.PNG,
        quality: int = 80,
        omit_background: bool = False,
    ) -> bytes:
        """Capture the full scrollable page.

        Args:
            format: Image format.
            quality: JPEG/WebP quality (0-100).
            omit_background: Make background transparent.

        Returns:
            Screenshot image data.
        """
        # Get page dimensions
        metrics = await self._get_page_metrics()

        options = ScreenshotOptions(
            format=format,
            quality=quality,
            omit_background=omit_background,
            full_page=True,
            capture_beyond_viewport=True,
            clip=ClipRegion(
                x=0,
                y=0,
                width=metrics["contentWidth"],
                height=metrics["contentHeight"],
            ),
        )

        result = await self._cdp.send(
            "Page.captureScreenshot",
            options.to_cdp_params(),
        )

        return base64.b64decode(result["data"])

    async def capture_element(
        self,
        element: "Element",
        *,
        format: ImageFormat = ImageFormat.PNG,
        quality: int = 80,
        omit_background: bool = False,
        padding: int = 0,
    ) -> bytes:
        """Capture a specific element.

        Args:
            element: Element to capture.
            format: Image format.
            quality: JPEG/WebP quality (0-100).
            omit_background: Make background transparent.
            padding: Padding around element in pixels.

        Returns:
            Screenshot image data.
        """
        # Get element bounding box
        box = await element.bounding_box()
        if not box:
            raise RuntimeError("Element has no bounding box")

        # Apply padding
        clip = ClipRegion(
            x=max(0, box["x"] - padding),
            y=max(0, box["y"] - padding),
            width=box["width"] + 2 * padding,
            height=box["height"] + 2 * padding,
        )

        options = ScreenshotOptions(
            format=format,
            quality=quality,
            omit_background=omit_background,
            clip=clip,
        )

        result = await self._cdp.send(
            "Page.captureScreenshot",
            options.to_cdp_params(),
        )

        return base64.b64decode(result["data"])

    async def capture_region(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        format: ImageFormat = ImageFormat.PNG,
        quality: int = 80,
        omit_background: bool = False,
    ) -> bytes:
        """Capture a specific region of the page.

        Args:
            x: X coordinate.
            y: Y coordinate.
            width: Region width.
            height: Region height.
            format: Image format.
            quality: JPEG/WebP quality (0-100).
            omit_background: Make background transparent.

        Returns:
            Screenshot image data.
        """
        options = ScreenshotOptions(
            format=format,
            quality=quality,
            omit_background=omit_background,
            clip=ClipRegion(x=x, y=y, width=width, height=height),
        )

        result = await self._cdp.send(
            "Page.captureScreenshot",
            options.to_cdp_params(),
        )

        return base64.b64decode(result["data"])

    async def capture_to_file(
        self,
        path: str | Path,
        *,
        full_page: bool = False,
        quality: int = 80,
        omit_background: bool = False,
        clip: Optional[ClipRegion] = None,
    ) -> Path:
        """Capture screenshot and save to file.

        The format is determined by the file extension.

        Args:
            path: File path to save to.
            full_page: Capture full scrollable page.
            quality: JPEG/WebP quality (0-100).
            omit_background: Make background transparent.
            clip: Region to clip.

        Returns:
            Path to saved file.
        """
        path = Path(path)

        # Determine format from extension
        ext = path.suffix.lower()
        format_map = {
            ".png": ImageFormat.PNG,
            ".jpg": ImageFormat.JPEG,
            ".jpeg": ImageFormat.JPEG,
            ".webp": ImageFormat.WEBP,
        }
        format = format_map.get(ext, ImageFormat.PNG)

        if full_page:
            data = await self.capture_full_page(
                format=format,
                quality=quality,
                omit_background=omit_background,
            )
        elif clip:
            data = await self.capture_region(
                clip.x,
                clip.y,
                clip.width,
                clip.height,
                format=format,
                quality=quality,
                omit_background=omit_background,
            )
        else:
            data = await self.capture_viewport(
                format=format,
                quality=quality,
                omit_background=omit_background,
            )

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(path, "wb") as f:
            f.write(data)

        return path

    async def capture_stitched_full_page(
        self,
        *,
        format: ImageFormat = ImageFormat.PNG,
        quality: int = 80,
        omit_background: bool = False,
        scroll_delay: float = 0.1,
    ) -> bytes:
        """Capture full page by scrolling and stitching.

        Alternative method for full page capture that works better with
        lazy-loaded content.

        Args:
            format: Image format.
            quality: JPEG/WebP quality (0-100).
            omit_background: Make background transparent.
            scroll_delay: Delay between scroll and capture.

        Returns:
            Stitched screenshot image data.
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImportError(
                "Pillow is required for stitched screenshots: pip install Pillow"
            )

        # Get viewport and page dimensions
        viewport = await self._get_viewport_size()
        metrics = await self._get_page_metrics()

        viewport_width = viewport["width"]
        viewport_height = viewport["height"]
        page_height = int(metrics["contentHeight"])
        page_width = int(metrics["contentWidth"])

        # Calculate number of screenshots needed
        screenshots: list[tuple[int, bytes]] = []
        current_y = 0

        while current_y < page_height:
            # Scroll to position
            await self._scroll_to(0, current_y)
            await asyncio.sleep(scroll_delay)

            # Capture viewport
            data = await self.capture_viewport(
                format=ImageFormat.PNG,  # Use PNG for stitching
                omit_background=omit_background,
            )

            screenshots.append((current_y, data))
            current_y += viewport_height

        # Scroll back to top
        await self._scroll_to(0, 0)

        # Stitch images together
        final_image = Image.new("RGBA", (page_width, page_height))

        for y_offset, data in screenshots:
            img = Image.open(io.BytesIO(data))
            # Crop if this is the last screenshot and overlaps
            if y_offset + img.height > page_height:
                crop_height = page_height - y_offset
                img = img.crop((0, 0, img.width, crop_height))
            final_image.paste(img, (0, y_offset))

        # Convert to desired format
        output = io.BytesIO()
        if format == ImageFormat.JPEG:
            final_image = final_image.convert("RGB")
            final_image.save(output, format="JPEG", quality=quality)
        elif format == ImageFormat.WEBP:
            final_image.save(output, format="WEBP", quality=quality)
        else:
            final_image.save(output, format="PNG")

        return output.getvalue()

    async def _get_page_metrics(self) -> dict[str, Any]:
        """Get page content metrics."""
        result = await self._cdp.send("Page.getLayoutMetrics")
        return result.get("contentSize", {})

    async def _get_viewport_size(self) -> dict[str, int]:
        """Get viewport size."""
        result = await self._cdp.send(
            "Runtime.evaluate",
            {
                "expression": "({width: window.innerWidth, height: window.innerHeight})",
                "returnByValue": True,
            },
        )
        return result.get("result", {}).get("value", {"width": 1920, "height": 1080})

    async def _scroll_to(self, x: int, y: int) -> None:
        """Scroll to position."""
        await self._cdp.send(
            "Runtime.evaluate",
            {"expression": f"window.scrollTo({x}, {y})"},
        )


async def take_screenshot(
    cdp: "CDPSession",
    *,
    path: Optional[str | Path] = None,
    full_page: bool = False,
    format: ImageFormat = ImageFormat.PNG,
    quality: int = 80,
    omit_background: bool = False,
) -> bytes:
    """Convenience function to take a screenshot.

    Args:
        cdp: CDP session.
        path: Optional path to save screenshot.
        full_page: Capture full page.
        format: Image format.
        quality: JPEG/WebP quality.
        omit_background: Make background transparent.

    Returns:
        Screenshot image data.

    Example:
        # Capture and return bytes
        data = await take_screenshot(cdp)

        # Capture and save to file
        data = await take_screenshot(cdp, path="/tmp/screenshot.png")
    """
    capture = ScreenshotCapture(cdp)

    if full_page:
        data = await capture.capture_full_page(
            format=format,
            quality=quality,
            omit_background=omit_background,
        )
    else:
        data = await capture.capture_viewport(
            format=format,
            quality=quality,
            omit_background=omit_background,
        )

    if path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    return data


async def screenshot_element(
    element: "Element",
    *,
    path: Optional[str | Path] = None,
    format: ImageFormat = ImageFormat.PNG,
    quality: int = 80,
    omit_background: bool = False,
    padding: int = 0,
) -> bytes:
    """Convenience function to screenshot an element.

    Args:
        element: Element to capture.
        path: Optional path to save screenshot.
        format: Image format.
        quality: JPEG/WebP quality.
        omit_background: Make background transparent.
        padding: Padding around element.

    Returns:
        Screenshot image data.
    """
    capture = ScreenshotCapture(element._page._cdp)
    data = await capture.capture_element(
        element,
        format=format,
        quality=quality,
        omit_background=omit_background,
        padding=padding,
    )

    if path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    return data


__all__ = [
    "ImageFormat",
    "ClipRegion",
    "ScreenshotOptions",
    "ScreenshotCapture",
    "take_screenshot",
    "screenshot_element",
]
