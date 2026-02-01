"""
Download manager with progress tracking for kuromi-browser.

Provides functionality to download files with progress callbacks,
resume support, and concurrent downloads.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING
from urllib.parse import unquote, urlparse

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPSession


class DownloadState(str, Enum):
    """Download state enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Download progress information."""

    download_id: str
    url: str
    filename: str
    total_bytes: int
    received_bytes: int
    state: DownloadState
    speed: float = 0.0  # bytes per second
    elapsed_time: float = 0.0
    error: Optional[str] = None

    @property
    def percent(self) -> float:
        """Get download percentage."""
        if self.total_bytes <= 0:
            return 0.0
        return min(100.0, (self.received_bytes / self.total_bytes) * 100)

    @property
    def remaining_bytes(self) -> int:
        """Get remaining bytes to download."""
        return max(0, self.total_bytes - self.received_bytes)

    @property
    def eta_seconds(self) -> Optional[float]:
        """Estimate time remaining in seconds."""
        if self.speed <= 0:
            return None
        return self.remaining_bytes / self.speed


@dataclass
class Download:
    """Represents an active download."""

    id: str
    url: str
    path: Path
    state: DownloadState = DownloadState.PENDING
    total_bytes: int = 0
    received_bytes: int = 0
    speed: float = 0.0
    start_time: float = 0.0
    error: Optional[str] = None
    guid: Optional[str] = None
    suggested_filename: Optional[str] = None
    _progress_callbacks: list[Callable[[DownloadProgress], Any]] = field(
        default_factory=list
    )
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        if not hasattr(self, "_progress_callbacks"):
            self._progress_callbacks = []
        if not hasattr(self, "_cancel_event"):
            self._cancel_event = asyncio.Event()

    @property
    def filename(self) -> str:
        """Get the filename."""
        return self.path.name

    def get_progress(self) -> DownloadProgress:
        """Get current progress information."""
        elapsed = time.time() - self.start_time if self.start_time > 0 else 0.0
        return DownloadProgress(
            download_id=self.id,
            url=self.url,
            filename=self.filename,
            total_bytes=self.total_bytes,
            received_bytes=self.received_bytes,
            state=self.state,
            speed=self.speed,
            elapsed_time=elapsed,
            error=self.error,
        )

    def on_progress(self, callback: Callable[[DownloadProgress], Any]) -> None:
        """Register a progress callback."""
        self._progress_callbacks.append(callback)

    async def _notify_progress(self) -> None:
        """Notify all progress callbacks."""
        progress = self.get_progress()
        for callback in self._progress_callbacks:
            try:
                result = callback(progress)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    def cancel(self) -> None:
        """Request download cancellation."""
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if download is cancelled."""
        return self._cancel_event.is_set()


class DownloadManager:
    """Manages file downloads with progress tracking.

    Provides functionality to:
    - Download files with progress callbacks
    - Track multiple concurrent downloads
    - Resume interrupted downloads
    - Cancel/pause downloads
    - Browser download interception via CDP

    Example:
        manager = DownloadManager(cdp_session, downloads_path="/tmp/downloads")
        await manager.enable()

        download = await manager.download_url(
            "https://example.com/file.zip",
            on_progress=lambda p: print(f"{p.percent:.1f}%")
        )
        await download.wait()
    """

    def __init__(
        self,
        cdp: Optional["CDPSession"] = None,
        downloads_path: Optional[str | Path] = None,
        max_concurrent: int = 3,
    ) -> None:
        """Initialize download manager.

        Args:
            cdp: CDP session for browser download interception.
            downloads_path: Default directory for downloads.
            max_concurrent: Maximum concurrent downloads.
        """
        self._cdp = cdp
        self._downloads_path = Path(downloads_path) if downloads_path else Path.cwd()
        self._max_concurrent = max_concurrent
        self._downloads: dict[str, Download] = {}
        self._enabled = False
        self._download_counter = 0
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @property
    def downloads_path(self) -> Path:
        """Get the downloads directory."""
        return self._downloads_path

    @downloads_path.setter
    def downloads_path(self, path: str | Path) -> None:
        """Set the downloads directory."""
        self._downloads_path = Path(path)

    @property
    def active_downloads(self) -> list[Download]:
        """Get list of active downloads."""
        return [
            d
            for d in self._downloads.values()
            if d.state in (DownloadState.PENDING, DownloadState.IN_PROGRESS)
        ]

    @property
    def completed_downloads(self) -> list[Download]:
        """Get list of completed downloads."""
        return [
            d for d in self._downloads.values() if d.state == DownloadState.COMPLETED
        ]

    async def enable(self) -> None:
        """Enable browser download interception via CDP."""
        if not self._cdp:
            return

        # Ensure downloads directory exists
        self._downloads_path.mkdir(parents=True, exist_ok=True)

        # Enable download behavior
        await self._cdp.send(
            "Browser.setDownloadBehavior",
            {
                "behavior": "allowAndName",
                "downloadPath": str(self._downloads_path.absolute()),
                "eventsEnabled": True,
            },
        )

        # Set up download event handlers
        self._cdp.on("Browser.downloadWillBegin", self._on_download_will_begin)
        self._cdp.on("Browser.downloadProgress", self._on_download_progress)

        self._enabled = True

    async def disable(self) -> None:
        """Disable browser download interception."""
        if not self._cdp:
            return

        await self._cdp.send(
            "Browser.setDownloadBehavior",
            {"behavior": "default"},
        )
        self._enabled = False

    def _generate_download_id(self) -> str:
        """Generate a unique download ID."""
        self._download_counter += 1
        return f"download_{self._download_counter}_{int(time.time() * 1000)}"

    def _on_download_will_begin(self, params: dict[str, Any]) -> None:
        """Handle download start event from CDP."""
        guid = params.get("guid", "")
        url = params.get("url", "")
        suggested_filename = params.get("suggestedFilename", "")

        download_id = self._generate_download_id()
        download_path = self._downloads_path / suggested_filename

        download = Download(
            id=download_id,
            url=url,
            path=download_path,
            state=DownloadState.IN_PROGRESS,
            guid=guid,
            suggested_filename=suggested_filename,
            start_time=time.time(),
        )
        self._downloads[guid] = download

    def _on_download_progress(self, params: dict[str, Any]) -> None:
        """Handle download progress event from CDP."""
        guid = params.get("guid", "")
        download = self._downloads.get(guid)

        if not download:
            return

        state = params.get("state", "")
        received_bytes = params.get("receivedBytes", 0)
        total_bytes = params.get("totalBytes", 0)

        download.received_bytes = received_bytes
        download.total_bytes = total_bytes

        # Calculate speed
        elapsed = time.time() - download.start_time
        if elapsed > 0:
            download.speed = received_bytes / elapsed

        # Update state
        if state == "completed":
            download.state = DownloadState.COMPLETED
        elif state == "canceled":
            download.state = DownloadState.CANCELLED
        elif state == "inProgress":
            download.state = DownloadState.IN_PROGRESS

        # Notify progress callbacks
        asyncio.create_task(download._notify_progress())

    async def download_url(
        self,
        url: str,
        *,
        path: Optional[str | Path] = None,
        filename: Optional[str] = None,
        on_progress: Optional[Callable[[DownloadProgress], Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        resume: bool = False,
    ) -> Download:
        """Download a file from URL using HTTP.

        Args:
            url: URL to download.
            path: Destination path. If not provided, uses downloads_path.
            filename: Override filename. If not provided, extracted from URL.
            on_progress: Progress callback function.
            headers: Additional HTTP headers.
            timeout: Download timeout in seconds.
            resume: Attempt to resume partial download.

        Returns:
            Download object for tracking progress.
        """
        import aiohttp

        # Determine filename
        if not filename:
            parsed = urlparse(url)
            filename = unquote(parsed.path.split("/")[-1]) or "download"

        # Determine full path
        if path:
            download_path = Path(path)
        else:
            download_path = self._downloads_path / filename

        # Ensure directory exists
        download_path.parent.mkdir(parents=True, exist_ok=True)

        # Create download object
        download_id = self._generate_download_id()
        download = Download(
            id=download_id,
            url=url,
            path=download_path,
            state=DownloadState.PENDING,
            start_time=time.time(),
        )

        if on_progress:
            download.on_progress(on_progress)

        self._downloads[download_id] = download

        # Start download task
        asyncio.create_task(
            self._download_with_http(
                download,
                headers=headers,
                timeout=timeout,
                resume=resume,
            )
        )

        return download

    async def _download_with_http(
        self,
        download: Download,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        resume: bool = False,
    ) -> None:
        """Perform HTTP download with progress tracking."""
        import aiohttp

        async with self._semaphore:
            download.state = DownloadState.IN_PROGRESS
            download.start_time = time.time()

            request_headers = dict(headers or {})

            # Handle resume
            start_byte = 0
            if resume and download.path.exists():
                start_byte = download.path.stat().st_size
                download.received_bytes = start_byte
                request_headers["Range"] = f"bytes={start_byte}-"

            try:
                client_timeout = aiohttp.ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(timeout=client_timeout) as session:
                    async with session.get(
                        download.url, headers=request_headers
                    ) as response:
                        if response.status not in (200, 206):
                            download.state = DownloadState.FAILED
                            download.error = f"HTTP {response.status}"
                            await download._notify_progress()
                            return

                        # Get total size
                        total = response.content_length or 0
                        if "Content-Range" in response.headers:
                            # Parse range response
                            range_header = response.headers["Content-Range"]
                            total = int(range_header.split("/")[-1])
                        download.total_bytes = total

                        # Download in chunks
                        mode = "ab" if resume and start_byte > 0 else "wb"
                        chunk_size = 64 * 1024  # 64KB chunks
                        last_progress_time = time.time()

                        with open(download.path, mode) as f:
                            async for chunk in response.content.iter_chunked(
                                chunk_size
                            ):
                                if download.is_cancelled:
                                    download.state = DownloadState.CANCELLED
                                    await download._notify_progress()
                                    return

                                f.write(chunk)
                                download.received_bytes += len(chunk)

                                # Update speed
                                elapsed = time.time() - download.start_time
                                if elapsed > 0:
                                    download.speed = download.received_bytes / elapsed

                                # Throttle progress notifications
                                now = time.time()
                                if now - last_progress_time >= 0.1:
                                    await download._notify_progress()
                                    last_progress_time = now

                        download.state = DownloadState.COMPLETED
                        await download._notify_progress()

            except asyncio.CancelledError:
                download.state = DownloadState.CANCELLED
                await download._notify_progress()
            except Exception as e:
                download.state = DownloadState.FAILED
                download.error = str(e)
                await download._notify_progress()

    async def wait_for_download(
        self,
        download: Download,
        *,
        timeout: Optional[float] = None,
    ) -> Download:
        """Wait for a download to complete.

        Args:
            download: Download to wait for.
            timeout: Maximum wait time in seconds.

        Returns:
            Completed download.

        Raises:
            TimeoutError: If timeout is reached.
            RuntimeError: If download fails.
        """
        start = time.time()

        while True:
            if download.state == DownloadState.COMPLETED:
                return download
            if download.state == DownloadState.FAILED:
                raise RuntimeError(f"Download failed: {download.error}")
            if download.state == DownloadState.CANCELLED:
                raise RuntimeError("Download was cancelled")

            if timeout and (time.time() - start) >= timeout:
                raise TimeoutError("Download timed out")

            await asyncio.sleep(0.1)

    async def cancel_download(self, download: Download) -> None:
        """Cancel a download.

        Args:
            download: Download to cancel.
        """
        download.cancel()

        # If browser download, cancel via CDP
        if self._cdp and download.guid:
            try:
                await self._cdp.send(
                    "Browser.cancelDownload",
                    {"guid": download.guid},
                )
            except Exception:
                pass

    async def cancel_all(self) -> None:
        """Cancel all active downloads."""
        for download in self.active_downloads:
            await self.cancel_download(download)

    def get_download(self, download_id: str) -> Optional[Download]:
        """Get download by ID.

        Args:
            download_id: Download ID.

        Returns:
            Download or None if not found.
        """
        return self._downloads.get(download_id)

    def clear_completed(self) -> None:
        """Remove completed downloads from tracking."""
        self._downloads = {
            k: v
            for k, v in self._downloads.items()
            if v.state not in (DownloadState.COMPLETED, DownloadState.CANCELLED)
        }


async def download_file(
    url: str,
    path: str | Path,
    *,
    on_progress: Optional[Callable[[DownloadProgress], Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: Optional[float] = None,
    resume: bool = False,
) -> Path:
    """Convenience function to download a file.

    Args:
        url: URL to download.
        path: Destination path.
        on_progress: Progress callback.
        headers: Additional HTTP headers.
        timeout: Download timeout.
        resume: Attempt to resume partial download.

    Returns:
        Path to downloaded file.

    Example:
        path = await download_file(
            "https://example.com/file.zip",
            "/tmp/file.zip",
            on_progress=lambda p: print(f"{p.percent:.1f}%")
        )
    """
    manager = DownloadManager(downloads_path=Path(path).parent)
    download = await manager.download_url(
        url,
        path=path,
        on_progress=on_progress,
        headers=headers,
        timeout=timeout,
        resume=resume,
    )
    await manager.wait_for_download(download)
    return download.path


def calculate_file_hash(
    path: str | Path,
    algorithm: str = "sha256",
    chunk_size: int = 8192,
) -> str:
    """Calculate hash of a file.

    Args:
        path: File path.
        algorithm: Hash algorithm (md5, sha1, sha256, sha512).
        chunk_size: Read chunk size.

    Returns:
        Hex digest of file hash.
    """
    hasher = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = [
    "DownloadState",
    "DownloadProgress",
    "Download",
    "DownloadManager",
    "download_file",
    "calculate_file_hash",
]
