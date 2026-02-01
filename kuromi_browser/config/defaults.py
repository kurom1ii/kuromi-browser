"""
Default configuration values for kuromi-browser.

This module contains all default values used throughout the configuration system.
"""

from typing import Any

# Browser defaults
DEFAULT_BROWSER_TYPE = "chromium"
DEFAULT_HEADLESS = False
DEFAULT_STEALTH = True
DEFAULT_DEVTOOLS = False
DEFAULT_SLOW_MO = 0
DEFAULT_TIMEOUT = 30000
DEFAULT_VIEWPORT_WIDTH = 1920
DEFAULT_VIEWPORT_HEIGHT = 1080
DEFAULT_LOCALE = "en-US"
DEFAULT_ACCEPT_DOWNLOADS = True
DEFAULT_OFFLINE = False
DEFAULT_IGNORE_HTTPS_ERRORS = False
DEFAULT_JAVASCRIPT_ENABLED = True
DEFAULT_BYPASS_CSP = False
DEFAULT_RECORD_VIDEO = False

# Session defaults
DEFAULT_SESSION_TIMEOUT = 30.0
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 30.0
DEFAULT_MAX_REDIRECTS = 10
DEFAULT_VERIFY_SSL = True
DEFAULT_HTTP2 = True
DEFAULT_FOLLOW_REDIRECTS = True
DEFAULT_MAX_CONNECTIONS = 100
DEFAULT_MAX_KEEPALIVE_CONNECTIONS = 20
DEFAULT_KEEPALIVE_EXPIRY = 5.0
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_BACKOFF = 0.5

# Page defaults
DEFAULT_PAGE_MODE = "browser"
DEFAULT_WAIT_UNTIL = "load"
DEFAULT_HAS_TOUCH = False
DEFAULT_IS_MOBILE = False
DEFAULT_DEVICE_SCALE_FACTOR = 1.0

# Network defaults
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Proxy defaults
DEFAULT_PROXY_TYPE = "http"
DEFAULT_PROXY_BYPASS: list[str] = []

# Fingerprint defaults
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_TIMEZONE_OFFSET = -300

# Default HTTP headers
DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Default browser arguments
DEFAULT_CHROMIUM_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-sync",
    "--disable-translate",
    "--metrics-recording-only",
    "--no-first-run",
    "--safebrowsing-disable-auto-update",
]

# Arguments to ignore by default
DEFAULT_IGNORE_ARGS: list[str] = [
    "--enable-automation",
    "--enable-blink-features=IdleDetection",
]

# Stealth mode additional arguments
STEALTH_CHROMIUM_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
]

# File config defaults
DEFAULT_CONFIG_FILENAME = "kuromi.config"
DEFAULT_CONFIG_EXTENSIONS = [".json", ".yaml", ".yml", ".ini", ".toml"]
DEFAULT_CONFIG_SEARCH_PATHS = [
    ".",
    "~/.config/kuromi-browser",
    "/etc/kuromi-browser",
]

# Environment variable prefix
ENV_PREFIX = "KUROMI_"


def get_default_browser_config() -> dict[str, Any]:
    """Get default browser configuration as a dictionary."""
    return {
        "browser_type": DEFAULT_BROWSER_TYPE,
        "headless": DEFAULT_HEADLESS,
        "stealth": DEFAULT_STEALTH,
        "devtools": DEFAULT_DEVTOOLS,
        "slow_mo": DEFAULT_SLOW_MO,
        "timeout": DEFAULT_TIMEOUT,
        "viewport_width": DEFAULT_VIEWPORT_WIDTH,
        "viewport_height": DEFAULT_VIEWPORT_HEIGHT,
        "locale": DEFAULT_LOCALE,
        "accept_downloads": DEFAULT_ACCEPT_DOWNLOADS,
        "offline": DEFAULT_OFFLINE,
        "ignore_https_errors": DEFAULT_IGNORE_HTTPS_ERRORS,
        "java_script_enabled": DEFAULT_JAVASCRIPT_ENABLED,
        "bypass_csp": DEFAULT_BYPASS_CSP,
        "record_video": DEFAULT_RECORD_VIDEO,
        "args": DEFAULT_CHROMIUM_ARGS.copy(),
        "ignore_default_args": DEFAULT_IGNORE_ARGS.copy(),
    }


def get_default_session_config() -> dict[str, Any]:
    """Get default session configuration as a dictionary."""
    return {
        "timeout": DEFAULT_SESSION_TIMEOUT,
        "connect_timeout": DEFAULT_CONNECT_TIMEOUT,
        "read_timeout": DEFAULT_READ_TIMEOUT,
        "max_redirects": DEFAULT_MAX_REDIRECTS,
        "verify_ssl": DEFAULT_VERIFY_SSL,
        "http2": DEFAULT_HTTP2,
        "follow_redirects": DEFAULT_FOLLOW_REDIRECTS,
        "max_connections": DEFAULT_MAX_CONNECTIONS,
        "max_keepalive_connections": DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
        "keepalive_expiry": DEFAULT_KEEPALIVE_EXPIRY,
        "retry_count": DEFAULT_RETRY_COUNT,
        "retry_backoff": DEFAULT_RETRY_BACKOFF,
        "headers": DEFAULT_HEADERS.copy(),
        "user_agent": DEFAULT_USER_AGENT,
    }


def get_default_page_config() -> dict[str, Any]:
    """Get default page configuration as a dictionary."""
    return {
        "mode": DEFAULT_PAGE_MODE,
        "timeout": DEFAULT_TIMEOUT,
        "wait_until": DEFAULT_WAIT_UNTIL,
        "java_script_enabled": DEFAULT_JAVASCRIPT_ENABLED,
        "has_touch": DEFAULT_HAS_TOUCH,
        "is_mobile": DEFAULT_IS_MOBILE,
        "device_scale_factor": DEFAULT_DEVICE_SCALE_FACTOR,
        "ignore_https_errors": DEFAULT_IGNORE_HTTPS_ERRORS,
        "offline": DEFAULT_OFFLINE,
        "bypass_csp": DEFAULT_BYPASS_CSP,
    }
