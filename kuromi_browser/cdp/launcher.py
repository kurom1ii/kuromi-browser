"""
Browser launcher for CDP connections.

Handles launching Chrome/Chromium with the necessary flags for CDP access.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class BrowserLaunchOptions:
    """Options for launching a browser."""

    headless: bool = True
    """Run browser in headless mode."""

    executable_path: Optional[str] = None
    """Path to browser executable. Auto-detected if not provided."""

    user_data_dir: Optional[str] = None
    """User data directory. Temp directory used if not provided."""

    remote_debugging_port: int = 0
    """CDP port. 0 means auto-select an available port."""

    args: list[str] = field(default_factory=list)
    """Additional browser arguments."""

    ignore_default_args: list[str] = field(default_factory=list)
    """Default arguments to ignore."""

    env: Optional[dict[str, str]] = None
    """Environment variables for the browser process."""

    slow_mo: float = 0
    """Slow down operations by this amount (ms)."""

    timeout: float = 30.0
    """Timeout for browser launch in seconds."""

    devtools: bool = False
    """Open DevTools on launch."""

    proxy: Optional[str] = None
    """Proxy server to use."""


# Default Chrome/Chromium arguments
DEFAULT_ARGS = [
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-client-side-phishing-detection",
    "--disable-component-extensions-with-background-pages",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-features=TranslateUI",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--enable-features=NetworkService,NetworkServiceInProcess",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--no-first-run",
    "--password-store=basic",
    "--use-mock-keychain",
    "--export-tagged-pdf",
    "--hide-scrollbars",
    "--mute-audio",
]

HEADLESS_ARGS = [
    "--headless=new",
]


def find_browser_executable() -> Optional[str]:
    """Find Chrome/Chromium executable path.

    Returns:
        Path to browser executable or None if not found.
    """
    # Common executable names
    executables = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
    ]

    # Check PATH
    for exe in executables:
        path = shutil.which(exe)
        if path:
            return path

    # Platform-specific paths
    if os.name == "posix":
        # Linux paths
        linux_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            "/opt/google/chrome/chrome",
        ]
        for path in linux_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        # macOS paths
        mac_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for path in mac_paths:
            if os.path.isfile(path):
                return path

    elif os.name == "nt":
        # Windows paths
        program_files = [
            os.environ.get("PROGRAMFILES", "C:\\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        for pf in program_files:
            if pf:
                chrome_path = os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe")
                if os.path.isfile(chrome_path):
                    return chrome_path

    return None


class BrowserProcess:
    """Manages a browser subprocess with CDP enabled."""

    def __init__(
        self,
        options: Optional[BrowserLaunchOptions] = None,
    ) -> None:
        """Initialize browser process manager.

        Args:
            options: Launch options for the browser.
        """
        self._options = options or BrowserLaunchOptions()
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._ws_endpoint: Optional[str] = None
        self._temp_dir: Optional[str] = None
        self._port: int = 0

    @property
    def ws_endpoint(self) -> Optional[str]:
        """Get the WebSocket debugger URL."""
        return self._ws_endpoint

    @property
    def process(self) -> Optional[subprocess.Popen[bytes]]:
        """Get the browser subprocess."""
        return self._process

    @property
    def port(self) -> int:
        """Get the debugging port."""
        return self._port

    async def launch(self) -> str:
        """Launch the browser and return the WebSocket endpoint URL.

        Returns:
            WebSocket debugger URL.

        Raises:
            RuntimeError: If browser fails to launch.
            FileNotFoundError: If browser executable not found.
        """
        # Find executable
        executable = self._options.executable_path or find_browser_executable()
        if not executable:
            raise FileNotFoundError(
                "Browser executable not found. Please install Chrome/Chromium "
                "or specify executable_path in options."
            )

        # Build arguments
        args = self._build_args(executable)

        # Set up user data dir
        user_data_dir = self._options.user_data_dir
        if not user_data_dir:
            self._temp_dir = tempfile.mkdtemp(prefix="kuromi-browser-")
            user_data_dir = self._temp_dir
            args.append(f"--user-data-dir={user_data_dir}")

        # Determine port
        port = self._options.remote_debugging_port
        if port == 0:
            port = await self._find_free_port()
        self._port = port
        args.append(f"--remote-debugging-port={port}")

        logger.debug(f"Launching browser: {executable}")
        logger.debug(f"Browser args: {args}")

        # Launch process
        env = self._options.env or os.environ.copy()
        self._process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Wait for CDP endpoint
        self._ws_endpoint = await self._wait_for_ws_endpoint(port)
        logger.debug(f"Browser launched, WebSocket endpoint: {self._ws_endpoint}")

        return self._ws_endpoint

    def _build_args(self, executable: str) -> list[str]:
        """Build browser launch arguments.

        Args:
            executable: Path to browser executable.

        Returns:
            List of command line arguments.
        """
        args = [executable]

        # Add default args (excluding ignored ones)
        for arg in DEFAULT_ARGS:
            if arg not in self._options.ignore_default_args:
                args.append(arg)

        # Add headless args
        if self._options.headless:
            for arg in HEADLESS_ARGS:
                if arg not in self._options.ignore_default_args:
                    args.append(arg)

        # Add devtools
        if self._options.devtools:
            args.append("--auto-open-devtools-for-tabs")

        # Add proxy
        if self._options.proxy:
            args.append(f"--proxy-server={self._options.proxy}")

        # Add custom args
        args.extend(self._options.args)

        return args

    async def _find_free_port(self) -> int:
        """Find an available port.

        Returns:
            Available port number.
        """
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    async def _wait_for_ws_endpoint(self, port: int) -> str:
        """Wait for browser to expose WebSocket endpoint.

        Args:
            port: CDP port number.

        Returns:
            WebSocket debugger URL.

        Raises:
            RuntimeError: If timeout waiting for endpoint.
        """
        if httpx is None:
            raise ImportError(
                "httpx package is required for browser launching. "
                "Install it with: pip install httpx"
            )

        url = f"http://localhost:{port}/json/version"
        timeout = self._options.timeout
        deadline = asyncio.get_event_loop().time() + timeout

        async with httpx.AsyncClient() as client:
            while asyncio.get_event_loop().time() < deadline:
                try:
                    response = await client.get(url, timeout=2.0)
                    if response.status_code == 200:
                        data = response.json()
                        ws_url = data.get("webSocketDebuggerUrl")
                        if ws_url:
                            return ws_url
                except (httpx.RequestError, json.JSONDecodeError):
                    pass

                # Check if process died
                if self._process and self._process.poll() is not None:
                    stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                    raise RuntimeError(
                        f"Browser process exited unexpectedly. stderr: {stderr}"
                    )

                await asyncio.sleep(0.1)

        raise RuntimeError(f"Timeout waiting for browser to start (port {port})")

    async def close(self) -> None:
        """Close the browser process."""
        if self._process:
            try:
                # Try graceful shutdown first
                if os.name == "posix":
                    self._process.send_signal(signal.SIGTERM)
                else:
                    self._process.terminate()

                try:
                    await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, self._process.wait
                        ),
                        timeout=5.0,
                    )
                except asyncio.TimeoutError:
                    # Force kill
                    self._process.kill()
                    self._process.wait()

            except (OSError, ProcessLookupError):
                pass
            finally:
                self._process = None

        # Clean up temp directory
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir: {e}")
            self._temp_dir = None

        self._ws_endpoint = None

    async def __aenter__(self) -> "BrowserProcess":
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


async def launch_browser(
    options: Optional[BrowserLaunchOptions] = None,
) -> BrowserProcess:
    """Launch a browser and return the process manager.

    Args:
        options: Launch options.

    Returns:
        BrowserProcess instance with browser running.

    Example:
        browser = await launch_browser()
        print(browser.ws_endpoint)
        await browser.close()
    """
    process = BrowserProcess(options)
    await process.launch()
    return process
