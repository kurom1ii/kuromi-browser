"""
Screen recording and screencast utilities for kuromi-browser.

Provides functionality to record page interactions as video or
capture screencasts frame by frame.
"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPSession


class RecordingFormat(str, Enum):
    """Recording output formats."""

    WEBM = "webm"
    MP4 = "mp4"
    GIF = "gif"


class ScreencastFormat(str, Enum):
    """Screencast frame formats."""

    JPEG = "jpeg"
    PNG = "png"


@dataclass
class ScreencastFrame:
    """A single screencast frame."""

    data: bytes
    timestamp: float
    session_id: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreencastOptions:
    """Screencast configuration.

    Attributes:
        format: Frame format (jpeg or png).
        quality: JPEG quality (0-100).
        max_width: Maximum width in pixels.
        max_height: Maximum height in pixels.
        every_nth_frame: Capture every nth frame.
    """

    format: ScreencastFormat = ScreencastFormat.JPEG
    quality: int = 80
    max_width: Optional[int] = None
    max_height: Optional[int] = None
    every_nth_frame: int = 1

    def to_cdp_params(self) -> dict[str, Any]:
        """Convert to CDP parameters."""
        params: dict[str, Any] = {
            "format": self.format.value,
            "quality": self.quality,
            "everyNthFrame": self.every_nth_frame,
        }

        if self.max_width:
            params["maxWidth"] = self.max_width
        if self.max_height:
            params["maxHeight"] = self.max_height

        return params


class Screencast:
    """Capture page screencast frames.

    Screencast provides a stream of frames from the page, useful for
    creating videos or GIFs of page interactions.

    Example:
        screencast = Screencast(cdp_session)

        # Start capturing
        await screencast.start()

        # ... perform actions ...

        # Stop and get frames
        frames = await screencast.stop()

        # Save as GIF
        await screencast.save_as_gif("/tmp/recording.gif")
    """

    def __init__(
        self,
        cdp: "CDPSession",
        options: Optional[ScreencastOptions] = None,
    ) -> None:
        """Initialize screencast.

        Args:
            cdp: CDP session.
            options: Screencast options.
        """
        self._cdp = cdp
        self._options = options or ScreencastOptions()
        self._frames: list[ScreencastFrame] = []
        self._recording = False
        self._start_time: float = 0
        self._frame_callback: Optional[Callable[[ScreencastFrame], Any]] = None

    @property
    def is_recording(self) -> bool:
        """Check if screencast is active."""
        return self._recording

    @property
    def frames(self) -> list[ScreencastFrame]:
        """Get captured frames."""
        return list(self._frames)

    @property
    def frame_count(self) -> int:
        """Get number of captured frames."""
        return len(self._frames)

    @property
    def duration(self) -> float:
        """Get recording duration in seconds."""
        if not self._frames:
            return 0.0
        return self._frames[-1].timestamp - self._frames[0].timestamp

    def on_frame(self, callback: Callable[[ScreencastFrame], Any]) -> None:
        """Register frame callback.

        Args:
            callback: Function called for each frame.
        """
        self._frame_callback = callback

    async def start(self) -> None:
        """Start screencast capture."""
        if self._recording:
            return

        self._frames.clear()
        self._start_time = time.time()
        self._recording = True

        # Set up frame handler
        self._cdp.on("Page.screencastFrame", self._on_frame)

        # Start screencast
        await self._cdp.send(
            "Page.startScreencast",
            self._options.to_cdp_params(),
        )

    async def stop(self) -> list[ScreencastFrame]:
        """Stop screencast capture.

        Returns:
            List of captured frames.
        """
        if not self._recording:
            return self._frames

        self._recording = False

        # Stop screencast
        try:
            await self._cdp.send("Page.stopScreencast")
        except Exception:
            pass

        return self._frames

    def _on_frame(self, params: dict[str, Any]) -> None:
        """Handle screencast frame event."""
        if not self._recording:
            return

        data = base64.b64decode(params.get("data", ""))
        timestamp = time.time() - self._start_time
        session_id = params.get("sessionId", 0)
        metadata = params.get("metadata", {})

        frame = ScreencastFrame(
            data=data,
            timestamp=timestamp,
            session_id=session_id,
            metadata=metadata,
        )

        self._frames.append(frame)

        # Acknowledge frame
        asyncio.create_task(
            self._cdp.send(
                "Page.screencastFrameAck",
                {"sessionId": session_id},
            )
        )

        # Call frame callback
        if self._frame_callback:
            try:
                result = self._frame_callback(frame)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass

    async def save_frames(
        self,
        directory: str | Path,
        prefix: str = "frame",
    ) -> list[Path]:
        """Save frames as individual images.

        Args:
            directory: Directory to save frames.
            prefix: Filename prefix.

        Returns:
            List of saved file paths.
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        ext = "jpg" if self._options.format == ScreencastFormat.JPEG else "png"
        paths: list[Path] = []

        for i, frame in enumerate(self._frames):
            path = directory / f"{prefix}_{i:05d}.{ext}"
            with open(path, "wb") as f:
                f.write(frame.data)
            paths.append(path)

        return paths

    async def save_as_gif(
        self,
        path: str | Path,
        *,
        fps: int = 10,
        loop: int = 0,
        optimize: bool = True,
    ) -> Path:
        """Save frames as animated GIF.

        Requires Pillow.

        Args:
            path: Output file path.
            fps: Frames per second.
            loop: Number of loops (0 = infinite).
            optimize: Optimize GIF size.

        Returns:
            Path to saved file.
        """
        try:
            from PIL import Image
        except ImportError:
            raise ImportError("Pillow is required for GIF export: pip install Pillow")

        if not self._frames:
            raise ValueError("No frames to save")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert frames to PIL images
        import io

        images: list[Image.Image] = []
        for frame in self._frames:
            img = Image.open(io.BytesIO(frame.data))
            images.append(img.convert("P", palette=Image.ADAPTIVE))

        # Calculate frame duration
        duration = int(1000 / fps)

        # Save GIF
        images[0].save(
            path,
            save_all=True,
            append_images=images[1:],
            duration=duration,
            loop=loop,
            optimize=optimize,
        )

        return path

    async def save_as_video(
        self,
        path: str | Path,
        *,
        fps: int = 30,
        codec: str = "libx264",
        crf: int = 23,
    ) -> Path:
        """Save frames as video file.

        Requires ffmpeg to be installed.

        Args:
            path: Output file path.
            fps: Frames per second.
            codec: Video codec.
            crf: Constant Rate Factor (quality, lower = better).

        Returns:
            Path to saved file.
        """
        import subprocess
        import tempfile

        if not self._frames:
            raise ValueError("No frames to save")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save frames to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            frame_paths = await self.save_frames(tmpdir)

            # Build ffmpeg command
            ext = "jpg" if self._options.format == ScreencastFormat.JPEG else "png"
            input_pattern = f"{tmpdir}/frame_%05d.{ext}"

            cmd = [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                input_pattern,
                "-c:v",
                codec,
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                str(path),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"ffmpeg error: {stderr.decode()}")

        return path

    def clear(self) -> None:
        """Clear captured frames."""
        self._frames.clear()


class PageRecorder:
    """High-level page recording interface.

    Provides a simple interface for recording page interactions
    as video files.

    Example:
        recorder = PageRecorder(cdp_session, output_path="/tmp/recording.mp4")

        await recorder.start()
        # ... perform page actions ...
        await recorder.stop()
    """

    def __init__(
        self,
        cdp: "CDPSession",
        output_path: str | Path,
        *,
        format: RecordingFormat = RecordingFormat.MP4,
        fps: int = 30,
        quality: int = 80,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> None:
        """Initialize page recorder.

        Args:
            cdp: CDP session.
            output_path: Output file path.
            format: Recording format.
            fps: Frames per second.
            quality: Frame quality (0-100).
            max_width: Maximum width.
            max_height: Maximum height.
        """
        self._cdp = cdp
        self._output_path = Path(output_path)
        self._format = format
        self._fps = fps

        self._screencast = Screencast(
            cdp,
            ScreencastOptions(
                format=ScreencastFormat.JPEG,
                quality=quality,
                max_width=max_width,
                max_height=max_height,
            ),
        )

    @property
    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._screencast.is_recording

    @property
    def frame_count(self) -> int:
        """Get number of recorded frames."""
        return self._screencast.frame_count

    @property
    def duration(self) -> float:
        """Get recording duration."""
        return self._screencast.duration

    async def start(self) -> None:
        """Start recording."""
        await self._screencast.start()

    async def stop(self) -> Path:
        """Stop recording and save file.

        Returns:
            Path to saved file.
        """
        await self._screencast.stop()

        if self._format == RecordingFormat.GIF:
            return await self._screencast.save_as_gif(
                self._output_path,
                fps=self._fps,
            )
        else:
            return await self._screencast.save_as_video(
                self._output_path,
                fps=self._fps,
            )

    async def pause(self) -> None:
        """Pause recording."""
        await self._screencast.stop()

    async def resume(self) -> None:
        """Resume recording."""
        await self._screencast.start()


class TracingRecorder:
    """Record browser tracing data.

    Captures detailed timing information about page loading,
    rendering, and JavaScript execution.
    """

    def __init__(self, cdp: "CDPSession") -> None:
        """Initialize tracing recorder.

        Args:
            cdp: CDP session.
        """
        self._cdp = cdp
        self._recording = False
        self._chunks: list[str] = []

    @property
    def is_recording(self) -> bool:
        """Check if tracing is active."""
        return self._recording

    async def start(
        self,
        *,
        categories: Optional[list[str]] = None,
        transfer_mode: str = "ReportEvents",
    ) -> None:
        """Start tracing.

        Args:
            categories: Trace categories to capture.
            transfer_mode: Transfer mode (ReportEvents or ReturnAsStream).
        """
        if self._recording:
            return

        self._chunks.clear()
        self._recording = True

        # Default categories
        if categories is None:
            categories = [
                "devtools.timeline",
                "disabled-by-default-devtools.timeline",
                "disabled-by-default-devtools.timeline.frame",
            ]

        # Set up data handler
        self._cdp.on("Tracing.dataCollected", self._on_data_collected)

        await self._cdp.send(
            "Tracing.start",
            {
                "categories": ",".join(categories),
                "transferMode": transfer_mode,
            },
        )

    async def stop(self) -> str:
        """Stop tracing and return data.

        Returns:
            Trace data as JSON string.
        """
        if not self._recording:
            return "[]"

        self._recording = False

        # Create completion event
        complete = asyncio.Event()

        def on_complete(params: dict[str, Any]) -> None:
            complete.set()

        self._cdp.on("Tracing.tracingComplete", on_complete)

        await self._cdp.send("Tracing.end")
        await complete.wait()

        # Combine chunks
        return "[" + ",".join(self._chunks) + "]"

    async def save(self, path: str | Path) -> Path:
        """Stop tracing and save to file.

        Args:
            path: Output file path.

        Returns:
            Path to saved file.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = await self.stop()

        with open(path, "w") as f:
            f.write(data)

        return path

    def _on_data_collected(self, params: dict[str, Any]) -> None:
        """Handle tracing data event."""
        import json

        value = params.get("value", [])
        for item in value:
            self._chunks.append(json.dumps(item))


async def record_page(
    cdp: "CDPSession",
    path: str | Path,
    *,
    duration: float,
    format: RecordingFormat = RecordingFormat.MP4,
    fps: int = 30,
) -> Path:
    """Convenience function to record page for specified duration.

    Args:
        cdp: CDP session.
        path: Output file path.
        duration: Recording duration in seconds.
        format: Recording format.
        fps: Frames per second.

    Returns:
        Path to saved file.

    Example:
        # Record 5 seconds of page activity
        path = await record_page(cdp, "/tmp/recording.mp4", duration=5.0)
    """
    recorder = PageRecorder(cdp, path, format=format, fps=fps)

    await recorder.start()
    await asyncio.sleep(duration)
    return await recorder.stop()


__all__ = [
    "RecordingFormat",
    "ScreencastFormat",
    "ScreencastFrame",
    "ScreencastOptions",
    "Screencast",
    "PageRecorder",
    "TracingRecorder",
    "record_page",
]
