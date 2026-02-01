"""
Configuration module for kuromi-browser.

This module provides a comprehensive configuration system with support for:
- Strongly-typed option classes (BrowserOptions, SessionOptions, PageOptions)
- Configuration file loading (JSON, YAML, INI, TOML)
- Environment variable support
- Built-in profiles (stealth, debug, fast, mobile)
- Validation and type checking via Pydantic

Example usage:
    from kuromi_browser.config import (
        KuromiConfig,
        BrowserOptions,
        SessionOptions,
        load_config,
    )

    # Load from file with environment overrides
    config = load_config("kuromi.config.json")

    # Create programmatically
    config = KuromiConfig(
        browser=BrowserOptions(
            headless=True,
            stealth=True,
            proxy="http://proxy:8080",
        ),
        session=SessionOptions(
            timeout=60.0,
            verify_ssl=False,
        ),
    )

    # Use built-in profile
    from kuromi_browser.config import load_config_with_profile
    config = load_config_with_profile("stealth")

Environment variables:
    KUROMI_BROWSER_HEADLESS=true
    KUROMI_BROWSER_PROXY=http://proxy:8080
    KUROMI_SESSION_TIMEOUT=60
    KUROMI_PAGE_MODE=session
"""

from .defaults import (
    DEFAULT_BROWSER_TYPE,
    DEFAULT_CHROMIUM_ARGS,
    DEFAULT_HEADERS,
    DEFAULT_HEADLESS,
    DEFAULT_IGNORE_ARGS,
    DEFAULT_LOCALE,
    DEFAULT_SESSION_TIMEOUT,
    DEFAULT_STEALTH,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    ENV_PREFIX,
    STEALTH_CHROMIUM_ARGS,
    get_default_browser_config,
    get_default_page_config,
    get_default_session_config,
)
from .env import (
    ENV_MAPPINGS,
    EnvConfigLoader,
    get_env,
    get_env_bool,
    get_env_dict,
    get_env_float,
    get_env_int,
    get_env_key,
    get_env_list,
    get_env_str,
    load_env_config,
)
from .loader import (
    PROFILES,
    ConfigLoader,
    ConfigurationError,
    find_config_file,
    load_config,
    load_config_with_profile,
    load_file,
    load_profile,
    merge_configs,
    save_config,
)
from .options import (
    BrowserOptions,
    BrowserType,
    ColorScheme,
    ForcedColors,
    GeolocationOptions,
    HttpCredentials,
    KuromiConfig,
    PageMode,
    PageOptions,
    ProxyOptions,
    ProxyType,
    ReducedMotion,
    RetryOptions,
    SessionOptions,
    VideoOptions,
    ViewportOptions,
    WaitUntil,
)

__all__ = [
    # Main configuration class
    "KuromiConfig",
    # Option classes
    "BrowserOptions",
    "SessionOptions",
    "PageOptions",
    "ProxyOptions",
    "ViewportOptions",
    "GeolocationOptions",
    "HttpCredentials",
    "VideoOptions",
    "RetryOptions",
    # Enums
    "BrowserType",
    "PageMode",
    "ProxyType",
    "ColorScheme",
    "ReducedMotion",
    "ForcedColors",
    "WaitUntil",
    # Loader functions
    "load_config",
    "load_config_with_profile",
    "load_file",
    "load_profile",
    "save_config",
    "find_config_file",
    "merge_configs",
    "ConfigLoader",
    "ConfigurationError",
    "PROFILES",
    # Environment functions
    "get_env",
    "get_env_bool",
    "get_env_int",
    "get_env_float",
    "get_env_str",
    "get_env_list",
    "get_env_dict",
    "get_env_key",
    "load_env_config",
    "EnvConfigLoader",
    "ENV_MAPPINGS",
    "ENV_PREFIX",
    # Default values
    "DEFAULT_BROWSER_TYPE",
    "DEFAULT_HEADLESS",
    "DEFAULT_STEALTH",
    "DEFAULT_TIMEOUT",
    "DEFAULT_VIEWPORT_WIDTH",
    "DEFAULT_VIEWPORT_HEIGHT",
    "DEFAULT_LOCALE",
    "DEFAULT_USER_AGENT",
    "DEFAULT_SESSION_TIMEOUT",
    "DEFAULT_HEADERS",
    "DEFAULT_CHROMIUM_ARGS",
    "DEFAULT_IGNORE_ARGS",
    "STEALTH_CHROMIUM_ARGS",
    "get_default_browser_config",
    "get_default_session_config",
    "get_default_page_config",
]
