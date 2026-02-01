"""
Environment variable support for kuromi-browser configuration.

This module provides functions to load configuration values from environment
variables with support for type conversion and nested keys.
"""

import os
from typing import Any, Optional, TypeVar, Union, get_args, get_origin

from .defaults import ENV_PREFIX

T = TypeVar("T")


def get_env_key(key: str, prefix: str = ENV_PREFIX) -> str:
    """Convert a configuration key to environment variable name.

    Args:
        key: Configuration key (e.g., "browser.headless")
        prefix: Environment variable prefix

    Returns:
        Environment variable name (e.g., "KUROMI_BROWSER_HEADLESS")
    """
    return f"{prefix}{key.upper().replace('.', '_').replace('-', '_')}"


def parse_bool(value: str) -> bool:
    """Parse string to boolean.

    Args:
        value: String value

    Returns:
        Boolean value
    """
    return value.lower() in ("true", "1", "yes", "on", "enabled")


def parse_int(value: str) -> int:
    """Parse string to integer.

    Args:
        value: String value

    Returns:
        Integer value
    """
    return int(value)


def parse_float(value: str) -> float:
    """Parse string to float.

    Args:
        value: String value

    Returns:
        Float value
    """
    return float(value)


def parse_list(value: str, item_type: type = str) -> list[Any]:
    """Parse string to list.

    Args:
        value: Comma-separated string value
        item_type: Type of list items

    Returns:
        List of parsed values
    """
    if not value:
        return []

    items = [item.strip() for item in value.split(",")]

    if item_type == int:
        return [int(item) for item in items]
    elif item_type == float:
        return [float(item) for item in items]
    elif item_type == bool:
        return [parse_bool(item) for item in items]

    return items


def parse_dict(value: str) -> dict[str, str]:
    """Parse string to dictionary.

    Format: "key1=value1,key2=value2"

    Args:
        value: String value in key=value format

    Returns:
        Dictionary of key-value pairs
    """
    if not value:
        return {}

    result = {}
    for pair in value.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()

    return result


def parse_value(value: str, target_type: type) -> Any:
    """Parse string value to target type.

    Args:
        value: String value
        target_type: Target type

    Returns:
        Parsed value
    """
    origin = get_origin(target_type)

    if origin is Union:
        # Handle Optional types
        args = get_args(target_type)
        non_none_types = [t for t in args if t is not type(None)]
        if non_none_types:
            return parse_value(value, non_none_types[0])
        return value

    if origin is list:
        item_type = get_args(target_type)[0] if get_args(target_type) else str
        return parse_list(value, item_type)

    if origin is dict:
        return parse_dict(value)

    if target_type == bool:
        return parse_bool(value)

    if target_type == int:
        return parse_int(value)

    if target_type == float:
        return parse_float(value)

    return value


def get_env(
    key: str,
    default: Optional[T] = None,
    target_type: Optional[type] = None,
    prefix: str = ENV_PREFIX,
) -> Optional[Union[T, str]]:
    """Get configuration value from environment variable.

    Args:
        key: Configuration key (e.g., "browser.headless")
        default: Default value if not set
        target_type: Target type for parsing
        prefix: Environment variable prefix

    Returns:
        Parsed value or default
    """
    env_key = get_env_key(key, prefix)
    value = os.environ.get(env_key)

    if value is None:
        return default

    if target_type is not None:
        return parse_value(value, target_type)

    # Infer type from default
    if default is not None:
        return parse_value(value, type(default))

    return value


def get_env_bool(key: str, default: bool = False, prefix: str = ENV_PREFIX) -> bool:
    """Get boolean value from environment variable.

    Args:
        key: Configuration key
        default: Default value
        prefix: Environment variable prefix

    Returns:
        Boolean value
    """
    result = get_env(key, default, bool, prefix)
    return result if isinstance(result, bool) else default


def get_env_int(key: str, default: int = 0, prefix: str = ENV_PREFIX) -> int:
    """Get integer value from environment variable.

    Args:
        key: Configuration key
        default: Default value
        prefix: Environment variable prefix

    Returns:
        Integer value
    """
    result = get_env(key, default, int, prefix)
    return result if isinstance(result, int) else default


def get_env_float(key: str, default: float = 0.0, prefix: str = ENV_PREFIX) -> float:
    """Get float value from environment variable.

    Args:
        key: Configuration key
        default: Default value
        prefix: Environment variable prefix

    Returns:
        Float value
    """
    result = get_env(key, default, float, prefix)
    return result if isinstance(result, (int, float)) else default


def get_env_str(
    key: str, default: Optional[str] = None, prefix: str = ENV_PREFIX
) -> Optional[str]:
    """Get string value from environment variable.

    Args:
        key: Configuration key
        default: Default value
        prefix: Environment variable prefix

    Returns:
        String value or None
    """
    env_key = get_env_key(key, prefix)
    return os.environ.get(env_key, default)


def get_env_list(
    key: str,
    default: Optional[list[str]] = None,
    item_type: type = str,
    prefix: str = ENV_PREFIX,
) -> list[Any]:
    """Get list value from environment variable.

    Args:
        key: Configuration key
        default: Default value
        item_type: Type of list items
        prefix: Environment variable prefix

    Returns:
        List value
    """
    env_key = get_env_key(key, prefix)
    value = os.environ.get(env_key)

    if value is None:
        return default if default is not None else []

    return parse_list(value, item_type)


def get_env_dict(
    key: str,
    default: Optional[dict[str, str]] = None,
    prefix: str = ENV_PREFIX,
) -> dict[str, str]:
    """Get dictionary value from environment variable.

    Args:
        key: Configuration key
        default: Default value
        prefix: Environment variable prefix

    Returns:
        Dictionary value
    """
    env_key = get_env_key(key, prefix)
    value = os.environ.get(env_key)

    if value is None:
        return default if default is not None else {}

    return parse_dict(value)


class EnvConfigLoader:
    """Load configuration from environment variables.

    This class provides methods to load entire configuration sections
    from environment variables with a consistent prefix.
    """

    def __init__(self, prefix: str = ENV_PREFIX):
        """Initialize environment config loader.

        Args:
            prefix: Environment variable prefix
        """
        self.prefix = prefix

    def get(
        self,
        key: str,
        default: Optional[T] = None,
        target_type: Optional[type] = None,
    ) -> Optional[Union[T, str]]:
        """Get configuration value from environment.

        Args:
            key: Configuration key
            default: Default value
            target_type: Target type for parsing

        Returns:
            Parsed value or default
        """
        return get_env(key, default, target_type, self.prefix)

    def load_section(self, section: str) -> dict[str, Any]:
        """Load all environment variables for a section.

        Args:
            section: Configuration section (e.g., "browser")

        Returns:
            Dictionary of configuration values
        """
        section_prefix = f"{self.prefix}{section.upper()}_"
        result = {}

        for key, value in os.environ.items():
            if key.startswith(section_prefix):
                # Convert KUROMI_BROWSER_HEADLESS to headless
                config_key = key[len(section_prefix):].lower()
                result[config_key] = value

        return result

    def load_all(self) -> dict[str, dict[str, Any]]:
        """Load all configuration from environment variables.

        Returns:
            Dictionary with sections (browser, session, page)
        """
        return {
            "browser": self.load_section("browser"),
            "session": self.load_section("session"),
            "page": self.load_section("page"),
        }


# Predefined environment variable mappings
ENV_MAPPINGS = {
    # Browser options
    "browser.headless": ("KUROMI_BROWSER_HEADLESS", bool),
    "browser.stealth": ("KUROMI_BROWSER_STEALTH", bool),
    "browser.devtools": ("KUROMI_BROWSER_DEVTOOLS", bool),
    "browser.timeout": ("KUROMI_BROWSER_TIMEOUT", int),
    "browser.slow_mo": ("KUROMI_BROWSER_SLOW_MO", int),
    "browser.proxy": ("KUROMI_BROWSER_PROXY", str),
    "browser.user_data_dir": ("KUROMI_BROWSER_USER_DATA_DIR", str),
    "browser.executable_path": ("KUROMI_BROWSER_EXECUTABLE_PATH", str),
    "browser.locale": ("KUROMI_BROWSER_LOCALE", str),
    "browser.timezone_id": ("KUROMI_BROWSER_TIMEZONE_ID", str),
    # Session options
    "session.timeout": ("KUROMI_SESSION_TIMEOUT", float),
    "session.connect_timeout": ("KUROMI_SESSION_CONNECT_TIMEOUT", float),
    "session.read_timeout": ("KUROMI_SESSION_READ_TIMEOUT", float),
    "session.verify_ssl": ("KUROMI_SESSION_VERIFY_SSL", bool),
    "session.http2": ("KUROMI_SESSION_HTTP2", bool),
    "session.proxy": ("KUROMI_SESSION_PROXY", str),
    "session.user_agent": ("KUROMI_SESSION_USER_AGENT", str),
    "session.impersonate": ("KUROMI_SESSION_IMPERSONATE", str),
    # Page options
    "page.mode": ("KUROMI_PAGE_MODE", str),
    "page.timeout": ("KUROMI_PAGE_TIMEOUT", int),
    "page.wait_until": ("KUROMI_PAGE_WAIT_UNTIL", str),
    "page.java_script_enabled": ("KUROMI_PAGE_JAVASCRIPT_ENABLED", bool),
    "page.offline": ("KUROMI_PAGE_OFFLINE", bool),
}


def load_env_config() -> dict[str, Any]:
    """Load configuration from predefined environment variables.

    Returns:
        Nested dictionary of configuration values
    """
    result: dict[str, Any] = {"browser": {}, "session": {}, "page": {}}

    for key, (env_var, target_type) in ENV_MAPPINGS.items():
        value = os.environ.get(env_var)
        if value is not None:
            section, option = key.split(".", 1)
            result[section][option] = parse_value(value, target_type)

    return result
