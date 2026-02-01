"""
Fingerprint generation module.

Generates realistic browser fingerprints using statistical data
from real browser populations. Supports browserforge integration.
"""

import hashlib
import random
import string
from typing import Any, Optional

from kuromi_browser.models import (
    AudioProperties,
    CanvasProperties,
    Fingerprint,
    NavigatorProperties,
    ScreenProperties,
    WebGLProperties,
)


# Common screen resolutions with their relative frequency
SCREEN_RESOLUTIONS = [
    ((1920, 1080), 35.0),  # Full HD - most common
    ((1366, 768), 20.0),   # HD
    ((1536, 864), 10.0),
    ((1440, 900), 8.0),
    ((1280, 720), 7.0),    # HD
    ((2560, 1440), 6.0),   # QHD
    ((1600, 900), 5.0),
    ((1280, 800), 3.0),
    ((3840, 2160), 3.0),   # 4K
    ((1680, 1050), 2.0),
    ((1920, 1200), 1.0),
]

# Common user agents by browser/OS
USER_AGENTS = {
    ("chrome", "windows"): [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    ],
    ("chrome", "macos"): [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ],
    ("chrome", "linux"): [
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ],
    ("firefox", "windows"): [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    ],
    ("firefox", "macos"): [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    ],
    ("firefox", "linux"): [
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    ],
}

# Platform strings by OS
PLATFORMS = {
    "windows": "Win32",
    "macos": "MacIntel",
    "linux": "Linux x86_64",
}

# Vendor strings by browser
VENDORS = {
    "chrome": "Google Inc.",
    "firefox": "",
    "safari": "Apple Computer, Inc.",
    "edge": "Google Inc.",
}

# WebGL renderers by GPU vendor
WEBGL_RENDERERS = {
    "nvidia": [
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
    ],
    "amd": [
        "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (AMD, AMD Radeon RX 5700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
    ],
    "intel": [
        "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    ],
    "apple": [
        "ANGLE (Apple, Apple M1, OpenGL 4.1)",
        "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
        "ANGLE (Apple, Apple M2, OpenGL 4.1)",
    ],
}

# Timezone data
TIMEZONES = [
    ("America/New_York", -300),
    ("America/Chicago", -360),
    ("America/Denver", -420),
    ("America/Los_Angeles", -480),
    ("Europe/London", 0),
    ("Europe/Paris", 60),
    ("Europe/Berlin", 60),
    ("Asia/Tokyo", 540),
    ("Asia/Shanghai", 480),
    ("Australia/Sydney", 660),
]

# Common fonts by OS
FONTS_BY_OS = {
    "windows": [
        "Arial", "Arial Black", "Calibri", "Cambria", "Cambria Math",
        "Comic Sans MS", "Consolas", "Courier New", "Georgia", "Impact",
        "Lucida Console", "Microsoft Sans Serif", "Palatino Linotype",
        "Segoe UI", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
    ],
    "macos": [
        "Arial", "Arial Black", "Comic Sans MS", "Courier New", "Georgia",
        "Helvetica", "Helvetica Neue", "Impact", "Lucida Grande", "Monaco",
        "Palatino", "Times", "Times New Roman", "Trebuchet MS", "Verdana",
    ],
    "linux": [
        "Arial", "Courier New", "DejaVu Sans", "DejaVu Sans Mono",
        "DejaVu Serif", "Droid Sans", "FreeMono", "FreeSans", "FreeSerif",
        "Liberation Mono", "Liberation Sans", "Liberation Serif", "Noto Sans",
        "Roboto", "Times New Roman", "Ubuntu", "Ubuntu Mono",
    ],
}

# Standard Chrome plugins
CHROME_PLUGINS = [
    {"name": "Chrome PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
    {"name": "Chromium PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
    {"name": "Microsoft Edge PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
    {"name": "PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
    {"name": "WebKit built-in PDF", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
]


def _weighted_choice(choices: list[tuple[Any, float]]) -> Any:
    """Select a random item based on weights."""
    total = sum(weight for _, weight in choices)
    r = random.uniform(0, total)
    cumulative = 0.0
    for item, weight in choices:
        cumulative += weight
        if r <= cumulative:
            return item
    return choices[-1][0]


def _generate_canvas_noise_seed() -> int:
    """Generate a random seed for canvas noise."""
    return random.randint(1, 2**31 - 1)


def _generate_audio_context_hash(seed: Optional[int] = None) -> float:
    """Generate a consistent audio context hash based on seed."""
    if seed is None:
        seed = random.randint(1, 2**31 - 1)
    random.seed(seed)
    # Generate a value similar to real audio fingerprints
    base = 124.04347527516074
    noise = random.uniform(-0.0001, 0.0001)
    return base + noise


class FingerprintGenerator:
    """Generate realistic browser fingerprints.

    Creates consistent and believable fingerprint profiles that
    pass common detection tests.
    """

    @staticmethod
    def generate(
        *,
        browser: str = "chrome",
        os: str = "linux",
        device: str = "desktop",
        locale: str = "en-US",
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> Fingerprint:
        """Generate a random fingerprint matching the specified profile.

        Args:
            browser: Browser type ("chrome", "firefox", "safari", "edge")
            os: Operating system ("windows", "macos", "linux")
            device: Device type ("desktop", "mobile", "tablet")
            locale: Locale string (e.g., "en-US")
            screen_width: Override screen width
            screen_height: Override screen height
            seed: Random seed for reproducible fingerprints

        Returns:
            A complete Fingerprint object
        """
        if seed is not None:
            random.seed(seed)

        # Select screen resolution
        if screen_width and screen_height:
            resolution = (screen_width, screen_height)
        else:
            resolution = _weighted_choice(SCREEN_RESOLUTIONS)

        # Select user agent
        ua_key = (browser.lower(), os.lower())
        if ua_key in USER_AGENTS:
            user_agent = random.choice(USER_AGENTS[ua_key])
        else:
            user_agent = random.choice(USER_AGENTS[("chrome", "linux")])

        # Select platform
        platform = PLATFORMS.get(os.lower(), "Linux x86_64")

        # Select vendor
        vendor = VENDORS.get(browser.lower(), "Google Inc.")

        # Generate hardware concurrency (typical values)
        hardware_concurrency = random.choice([2, 4, 6, 8, 12, 16])

        # Generate device memory (typical values in GB)
        device_memory = random.choice([2, 4, 8, 16, 32])

        # Select WebGL renderer
        gpu_vendor = random.choice(["nvidia", "amd", "intel"])
        if os.lower() == "macos":
            gpu_vendor = "apple"
        webgl_renderer = random.choice(WEBGL_RENDERERS[gpu_vendor])

        # Select timezone
        timezone, timezone_offset = random.choice(TIMEZONES)

        # Select fonts
        fonts = FONTS_BY_OS.get(os.lower(), FONTS_BY_OS["linux"])

        # Build navigator properties
        navigator = NavigatorProperties(
            platform=platform,
            vendor=vendor,
            language=locale,
            languages=[locale, locale.split("-")[0]],
            hardware_concurrency=hardware_concurrency,
            device_memory=float(device_memory),
            max_touch_points=0 if device == "desktop" else 5,
            do_not_track=random.choice([None, "1"]),
        )

        # Build screen properties
        screen = ScreenProperties(
            width=resolution[0],
            height=resolution[1],
            avail_width=resolution[0],
            avail_height=resolution[1] - random.randint(30, 80),  # Taskbar
            color_depth=24,
            pixel_depth=24,
            device_pixel_ratio=1.0 if device == "desktop" else random.choice([1.0, 1.5, 2.0]),
        )

        # Build WebGL properties
        webgl = WebGLProperties(
            vendor="Google Inc. (NVIDIA)" if "NVIDIA" in webgl_renderer else "Google Inc.",
            renderer=webgl_renderer,
        )

        # Build audio properties
        audio = AudioProperties(
            sample_rate=44100,
            max_channel_count=2,
        )

        # Build canvas properties
        canvas = CanvasProperties(
            noise_enabled=True,
            noise_seed=_generate_canvas_noise_seed(),
            noise_level=0.1,
        )

        return Fingerprint(
            user_agent=user_agent,
            navigator=navigator,
            screen=screen,
            webgl=webgl,
            audio=audio,
            canvas=canvas,
            timezone=timezone,
            timezone_offset=timezone_offset,
            locale=locale,
            fonts=fonts,
            plugins=CHROME_PLUGINS if browser.lower() in ("chrome", "edge") else [],
        )

    @staticmethod
    def generate_consistent(identifier: str, **kwargs: Any) -> Fingerprint:
        """Generate a fingerprint that's consistent for a given identifier.

        This is useful for maintaining the same fingerprint across sessions.

        Args:
            identifier: A unique string to derive the seed from
            **kwargs: Additional arguments passed to generate()

        Returns:
            A Fingerprint that will be the same for the same identifier
        """
        # Create a deterministic seed from the identifier
        hash_bytes = hashlib.sha256(identifier.encode()).digest()
        seed = int.from_bytes(hash_bytes[:4], "big")
        return FingerprintGenerator.generate(seed=seed, **kwargs)

    @staticmethod
    def from_browserforge() -> Fingerprint:
        """Generate fingerprint using browserforge library.

        Requires browserforge to be installed:
            pip install browserforge

        Returns:
            A Fingerprint generated by browserforge
        """
        try:
            from browserforge.fingerprints import FingerprintGenerator as BFGenerator
            from browserforge.headers import HeaderGenerator
        except ImportError:
            raise ImportError(
                "browserforge is required for this method. "
                "Install it with: pip install browserforge"
            )

        # Generate fingerprint using browserforge
        fg = BFGenerator()
        bf_fp = fg.generate()

        # Generate headers
        hg = HeaderGenerator()
        headers = hg.generate()

        # Convert to our Fingerprint model
        navigator = NavigatorProperties(
            platform=bf_fp.navigator.platform,
            vendor=bf_fp.navigator.vendor or "Google Inc.",
            language=bf_fp.navigator.language,
            languages=bf_fp.navigator.languages or ["en-US", "en"],
            hardware_concurrency=bf_fp.navigator.hardwareConcurrency,
            device_memory=bf_fp.navigator.deviceMemory,
            max_touch_points=bf_fp.navigator.maxTouchPoints or 0,
        )

        screen = ScreenProperties(
            width=bf_fp.screen.width,
            height=bf_fp.screen.height,
            avail_width=bf_fp.screen.availWidth,
            avail_height=bf_fp.screen.availHeight,
            color_depth=bf_fp.screen.colorDepth,
            pixel_depth=bf_fp.screen.pixelDepth,
        )

        webgl = WebGLProperties(
            vendor=bf_fp.videoCard.vendor if bf_fp.videoCard else None,
            renderer=bf_fp.videoCard.renderer if bf_fp.videoCard else None,
        )

        return Fingerprint(
            user_agent=headers.get("User-Agent", ""),
            navigator=navigator,
            screen=screen,
            webgl=webgl,
        )

    @staticmethod
    def validate(fingerprint: Fingerprint) -> list[str]:
        """Validate fingerprint consistency, return list of issues.

        Checks for common inconsistencies that could be detected
        by anti-bot systems.

        Args:
            fingerprint: The fingerprint to validate

        Returns:
            A list of validation issues (empty if valid)
        """
        issues = []

        # Check user agent consistency
        ua = fingerprint.user_agent.lower()

        # Platform vs UA check
        if "windows" in ua and fingerprint.navigator.platform != "Win32":
            issues.append(
                f"Platform mismatch: UA contains 'windows' but platform is '{fingerprint.navigator.platform}'"
            )
        if "mac" in ua and fingerprint.navigator.platform != "MacIntel":
            issues.append(
                f"Platform mismatch: UA contains 'mac' but platform is '{fingerprint.navigator.platform}'"
            )
        if "linux" in ua and "linux" not in fingerprint.navigator.platform.lower():
            issues.append(
                f"Platform mismatch: UA contains 'linux' but platform is '{fingerprint.navigator.platform}'"
            )

        # Vendor check
        if "chrome" in ua and fingerprint.navigator.vendor != "Google Inc.":
            issues.append(
                f"Vendor mismatch: Chrome UA but vendor is '{fingerprint.navigator.vendor}'"
            )
        if "firefox" in ua and fingerprint.navigator.vendor != "":
            issues.append(
                f"Vendor mismatch: Firefox UA but vendor is '{fingerprint.navigator.vendor}'"
            )

        # Screen resolution check
        if fingerprint.screen.avail_height > fingerprint.screen.height:
            issues.append(
                f"Screen mismatch: availHeight ({fingerprint.screen.avail_height}) > height ({fingerprint.screen.height})"
            )
        if fingerprint.screen.avail_width > fingerprint.screen.width:
            issues.append(
                f"Screen mismatch: availWidth ({fingerprint.screen.avail_width}) > width ({fingerprint.screen.width})"
            )

        # Hardware concurrency check
        if fingerprint.navigator.hardware_concurrency not in [1, 2, 4, 6, 8, 12, 16, 24, 32, 64]:
            issues.append(
                f"Unusual hardware_concurrency value: {fingerprint.navigator.hardware_concurrency}"
            )

        # Device memory check
        if fingerprint.navigator.device_memory and fingerprint.navigator.device_memory not in [
            0.25, 0.5, 1, 2, 4, 8, 16, 32, 64, 128
        ]:
            issues.append(
                f"Unusual device_memory value: {fingerprint.navigator.device_memory}"
            )

        # Touch points check for desktop
        if "mobile" not in ua.lower() and fingerprint.navigator.max_touch_points > 0:
            # This is actually okay for some laptops with touchscreens
            pass

        return issues


__all__ = [
    "FingerprintGenerator",
    "SCREEN_RESOLUTIONS",
    "USER_AGENTS",
    "WEBGL_RENDERERS",
    "TIMEZONES",
]
