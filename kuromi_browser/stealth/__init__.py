"""
Stealth module for kuromi-browser.

This module provides anti-detection and fingerprint spoofing capabilities:
- CDPPatches: CDP-level JavaScript patches for browser API spoofing
- FingerprintGenerator: Generate realistic browser fingerprints
- HumanMouse: Human-like mouse movement simulation
- HumanKeyboard: Human-like keyboard input simulation
- TLSClient: TLS fingerprint impersonation using curl_cffi
"""

from typing import Any, Optional

from kuromi_browser.models import Fingerprint

# Import submodules
from kuromi_browser.stealth.cdp import CDPPatches
from kuromi_browser.stealth.fingerprint import (
    FingerprintGenerator,
    SCREEN_RESOLUTIONS,
    USER_AGENTS,
    WEBGL_RENDERERS,
    TIMEZONES,
)
from kuromi_browser.stealth.behavior import HumanMouse, MousePath, HumanKeyboard
from kuromi_browser.stealth.tls import TLSClient, TLSConfig


class StealthConfig:
    """Configuration for stealth features.

    Controls which anti-detection measures are applied.
    """

    def __init__(
        self,
        *,
        webdriver: bool = True,
        chrome_app: bool = True,
        chrome_csi: bool = True,
        chrome_load_times: bool = True,
        chrome_runtime: bool = True,
        iframe_content_window: bool = True,
        media_codecs: bool = True,
        navigator_hardware_concurrency: bool = True,
        navigator_languages: bool = True,
        navigator_permissions: bool = True,
        navigator_platform: bool = True,
        navigator_plugins: bool = True,
        navigator_user_agent: bool = True,
        navigator_vendor: bool = True,
        navigator_webdriver: bool = True,
        webgl_vendor: bool = True,
        window_outerdimensions: bool = True,
        canvas_fingerprint: bool = True,
        audio_fingerprint: bool = True,
        font_fingerprint: bool = True,
        timezone: bool = True,
        geolocation: bool = True,
    ) -> None:
        self.webdriver = webdriver
        self.chrome_app = chrome_app
        self.chrome_csi = chrome_csi
        self.chrome_load_times = chrome_load_times
        self.chrome_runtime = chrome_runtime
        self.iframe_content_window = iframe_content_window
        self.media_codecs = media_codecs
        self.navigator_hardware_concurrency = navigator_hardware_concurrency
        self.navigator_languages = navigator_languages
        self.navigator_permissions = navigator_permissions
        self.navigator_platform = navigator_platform
        self.navigator_plugins = navigator_plugins
        self.navigator_user_agent = navigator_user_agent
        self.navigator_vendor = navigator_vendor
        self.navigator_webdriver = navigator_webdriver
        self.webgl_vendor = webgl_vendor
        self.window_outerdimensions = window_outerdimensions
        self.canvas_fingerprint = canvas_fingerprint
        self.audio_fingerprint = audio_fingerprint
        self.font_fingerprint = font_fingerprint
        self.timezone = timezone
        self.geolocation = geolocation


class StealthPatches:
    """JavaScript patches for browser API spoofing.

    Generates and applies JavaScript code to override browser APIs
    and hide automation indicators.

    This class wraps CDPPatches for backward compatibility.
    For new code, use CDPPatches directly.
    """

    def __init__(
        self,
        fingerprint: Optional[Fingerprint] = None,
        config: Optional[StealthConfig] = None,
    ) -> None:
        self._fingerprint = fingerprint
        self._config = config or StealthConfig()
        self._cdp_patches = CDPPatches(fingerprint)

    def generate_patches(self) -> str:
        """Generate all stealth patches as JavaScript code."""
        return self._cdp_patches.get_combined_patch()

    def patch_webdriver(self) -> str:
        """Generate patch to hide webdriver property."""
        from kuromi_browser.stealth.cdp.patches import WEBDRIVER_PATCH
        return WEBDRIVER_PATCH

    def patch_chrome_runtime(self) -> str:
        """Generate patch for chrome.runtime."""
        from kuromi_browser.stealth.cdp.patches import CHROME_PATCHES
        return CHROME_PATCHES

    def patch_navigator_plugins(self) -> str:
        """Generate patch for navigator.plugins."""
        from kuromi_browser.stealth.cdp.patches import PLUGINS_PATCH
        return PLUGINS_PATCH

    def patch_webgl(self) -> str:
        """Generate patch for WebGL fingerprint."""
        from kuromi_browser.stealth.cdp.patches import WEBGL_PATCH
        if self._fingerprint and self._fingerprint.webgl.vendor:
            return WEBGL_PATCH.replace(
                "{vendor}", f"'{self._fingerprint.webgl.vendor}'"
            ).replace(
                "{renderer}", f"'{self._fingerprint.webgl.renderer}'"
            )
        return ""

    def patch_canvas(self) -> str:
        """Generate patch to add noise to canvas fingerprint."""
        from kuromi_browser.stealth.cdp.patches import CANVAS_NOISE_PATCH
        seed = "Date.now()"
        if self._fingerprint and self._fingerprint.canvas.noise_seed:
            seed = str(self._fingerprint.canvas.noise_seed)
        return CANVAS_NOISE_PATCH.replace("{seed}", seed)

    def patch_audio(self) -> str:
        """Generate patch to add noise to audio fingerprint."""
        from kuromi_browser.stealth.cdp.patches import AUDIO_NOISE_PATCH
        seed = "Date.now()"
        if self._fingerprint and self._fingerprint.canvas.noise_seed:
            seed = str(self._fingerprint.canvas.noise_seed)
        return AUDIO_NOISE_PATCH.replace("{seed}", seed)

    def patch_fonts(self) -> str:
        """Generate patch for font detection."""
        # Font detection is handled by providing consistent font list
        return ""

    def get_init_script(self) -> str:
        """Get the full initialization script to inject."""
        return self.generate_patches()


async def apply_stealth(
    cdp_session: Any,
    fingerprint: Optional[Fingerprint] = None,
    config: Optional[StealthConfig] = None,
) -> None:
    """Apply stealth patches to a CDP session.

    This is the main entry point for enabling stealth mode on a page.
    Should be called after creating a new page/context but before navigation.

    Args:
        cdp_session: CDP session object with a send() method
        fingerprint: Optional fingerprint to use for customizing patches
        config: Optional stealth configuration (currently unused, reserved for future)

    Example:
        async with browser.new_page() as page:
            await apply_stealth(page.cdp_session, fingerprint)
            await page.goto("https://example.com")
    """
    patches = CDPPatches(fingerprint)
    await patches.apply_to_page(cdp_session)

    # Set user agent if fingerprint provided
    if fingerprint:
        await cdp_session.send(
            "Emulation.setUserAgentOverride",
            {
                "userAgent": fingerprint.user_agent,
                "platform": fingerprint.navigator.platform,
                "acceptLanguage": ",".join(fingerprint.navigator.languages),
            },
        )

        # Set timezone if configured
        if config is None or config.timezone:
            await cdp_session.send(
                "Emulation.setTimezoneOverride",
                {"timezoneId": fingerprint.timezone},
            )

        # Set locale
        await cdp_session.send(
            "Emulation.setLocaleOverride",
            {"locale": fingerprint.locale},
        )


async def apply_stealth_basic(cdp_session: Any) -> None:
    """Apply basic stealth patches without fingerprint customization.

    This is a lightweight version that only applies essential patches
    to hide automation indicators.

    Args:
        cdp_session: CDP session object with a send() method
    """
    await CDPPatches.apply_basic_patches(cdp_session)


__all__ = [
    # Main classes
    "StealthConfig",
    "StealthPatches",
    "FingerprintGenerator",
    # CDP Patches
    "CDPPatches",
    # Behavior simulation
    "HumanMouse",
    "MousePath",
    "HumanKeyboard",
    # TLS impersonation
    "TLSClient",
    "TLSConfig",
    # Data constants
    "SCREEN_RESOLUTIONS",
    "USER_AGENTS",
    "WEBGL_RENDERERS",
    "TIMEZONES",
    # Functions
    "apply_stealth",
    "apply_stealth_basic",
]
