"""
Configuration file loader for kuromi-browser.

This module provides functions to load configuration from various file formats
including JSON, YAML, INI, and TOML.
"""

import json
import os
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Optional, Union

from .defaults import (
    DEFAULT_CONFIG_EXTENSIONS,
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_CONFIG_SEARCH_PATHS,
)
from .env import load_env_config
from .options import KuromiConfig


class ConfigurationError(Exception):
    """Configuration loading or parsing error."""

    pass


def _load_json(path: Path) -> dict[str, Any]:
    """Load configuration from JSON file.

    Args:
        path: Path to JSON file

    Returns:
        Configuration dictionary
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        path: Path to YAML file

    Returns:
        Configuration dictionary
    """
    try:
        import yaml
    except ImportError:
        raise ConfigurationError(
            "PyYAML is required to load YAML config files. "
            "Install with: pip install pyyaml"
        )

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_toml(path: Path) -> dict[str, Any]:
    """Load configuration from TOML file.

    Args:
        path: Path to TOML file

    Returns:
        Configuration dictionary
    """
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            raise ConfigurationError(
                "tomli is required to load TOML config files on Python < 3.11. "
                "Install with: pip install tomli"
            )

    with open(path, "rb") as f:
        return tomllib.load(f)


def _load_ini(path: Path) -> dict[str, Any]:
    """Load configuration from INI file.

    Args:
        path: Path to INI file

    Returns:
        Configuration dictionary
    """
    parser = ConfigParser()
    parser.read(path, encoding="utf-8")

    result: dict[str, Any] = {}

    for section in parser.sections():
        result[section] = {}
        for key, value in parser.items(section):
            # Attempt type conversion
            result[section][key] = _convert_ini_value(value)

    return result


def _convert_ini_value(value: str) -> Any:
    """Convert INI string value to appropriate type.

    Args:
        value: String value from INI file

    Returns:
        Converted value
    """
    value = value.strip()

    # Boolean
    if value.lower() in ("true", "yes", "on", "1"):
        return True
    if value.lower() in ("false", "no", "off", "0"):
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # List (comma-separated)
    if "," in value:
        return [item.strip() for item in value.split(",")]

    return value


def load_file(path: Union[str, Path]) -> dict[str, Any]:
    """Load configuration from file based on extension.

    Args:
        path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        ConfigurationError: If file format is not supported or file not found
    """
    path = Path(path)

    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".json":
        return _load_json(path)
    elif suffix in (".yaml", ".yml"):
        return _load_yaml(path)
    elif suffix == ".toml":
        return _load_toml(path)
    elif suffix == ".ini":
        return _load_ini(path)
    else:
        raise ConfigurationError(f"Unsupported configuration format: {suffix}")


def find_config_file(
    filename: str = DEFAULT_CONFIG_FILENAME,
    search_paths: Optional[list[str]] = None,
    extensions: Optional[list[str]] = None,
) -> Optional[Path]:
    """Find configuration file in search paths.

    Args:
        filename: Base filename without extension
        search_paths: Directories to search
        extensions: File extensions to try

    Returns:
        Path to config file or None if not found
    """
    if search_paths is None:
        search_paths = DEFAULT_CONFIG_SEARCH_PATHS

    if extensions is None:
        extensions = DEFAULT_CONFIG_EXTENSIONS

    for search_path in search_paths:
        # Expand user home directory
        search_dir = Path(search_path).expanduser()

        for ext in extensions:
            config_path = search_dir / f"{filename}{ext}"
            if config_path.exists():
                return config_path

    return None


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Deep merge multiple configuration dictionaries.

    Later configs take precedence over earlier ones.

    Args:
        *configs: Configuration dictionaries to merge

    Returns:
        Merged configuration dictionary
    """
    result: dict[str, Any] = {}

    for config in configs:
        _deep_merge(result, config)

    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Deep merge override into base dictionary in-place.

    Args:
        base: Base dictionary to merge into
        override: Dictionary with override values
    """
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


class ConfigLoader:
    """Configuration loader with support for multiple sources.

    This class provides a unified interface for loading configuration from
    files, environment variables, and programmatic overrides.
    """

    def __init__(
        self,
        config_file: Optional[Union[str, Path]] = None,
        search_paths: Optional[list[str]] = None,
        load_env: bool = True,
        auto_find: bool = True,
    ):
        """Initialize configuration loader.

        Args:
            config_file: Explicit path to configuration file
            search_paths: Directories to search for config files
            load_env: Whether to load environment variables
            auto_find: Whether to auto-find config files
        """
        self.config_file = Path(config_file) if config_file else None
        self.search_paths = search_paths or DEFAULT_CONFIG_SEARCH_PATHS
        self.load_env = load_env
        self.auto_find = auto_find
        self._file_config: Optional[dict[str, Any]] = None
        self._env_config: Optional[dict[str, Any]] = None

    def load(self, overrides: Optional[dict[str, Any]] = None) -> KuromiConfig:
        """Load configuration from all sources.

        Priority (highest to lowest):
        1. Programmatic overrides
        2. Environment variables
        3. Configuration file
        4. Default values

        Args:
            overrides: Programmatic configuration overrides

        Returns:
            Loaded configuration
        """
        configs = []

        # Load from file
        file_config = self._load_file_config()
        if file_config:
            configs.append(file_config)

        # Load from environment
        if self.load_env:
            env_config = self._load_env_config()
            if env_config:
                configs.append(env_config)

        # Apply overrides
        if overrides:
            configs.append(overrides)

        # Merge all configs
        merged = merge_configs(*configs) if configs else {}

        return KuromiConfig.from_dict(merged)

    def _load_file_config(self) -> Optional[dict[str, Any]]:
        """Load configuration from file.

        Returns:
            Configuration dictionary or None
        """
        if self._file_config is not None:
            return self._file_config

        config_path = self.config_file

        if config_path is None and self.auto_find:
            config_path = find_config_file(search_paths=self.search_paths)

        if config_path is not None:
            try:
                self._file_config = load_file(config_path)
            except ConfigurationError:
                self._file_config = {}

        return self._file_config

    def _load_env_config(self) -> Optional[dict[str, Any]]:
        """Load configuration from environment variables.

        Returns:
            Configuration dictionary or None
        """
        if self._env_config is not None:
            return self._env_config

        self._env_config = load_env_config()
        return self._env_config

    def reload(self) -> KuromiConfig:
        """Reload configuration from all sources.

        Returns:
            Reloaded configuration
        """
        self._file_config = None
        self._env_config = None
        return self.load()


def load_config(
    config_file: Optional[Union[str, Path]] = None,
    overrides: Optional[dict[str, Any]] = None,
    load_env: bool = True,
) -> KuromiConfig:
    """Convenience function to load configuration.

    Args:
        config_file: Path to configuration file
        overrides: Programmatic overrides
        load_env: Whether to load environment variables

    Returns:
        Loaded configuration
    """
    loader = ConfigLoader(config_file=config_file, load_env=load_env)
    return loader.load(overrides=overrides)


def save_config(
    config: KuromiConfig,
    path: Union[str, Path],
    format: str = "json",
) -> None:
    """Save configuration to file.

    Args:
        config: Configuration to save
        path: Output file path
        format: Output format (json, yaml, toml)

    Raises:
        ConfigurationError: If format is not supported
    """
    path = Path(path)
    data = config.to_dict()

    if format == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    elif format in ("yaml", "yml"):
        try:
            import yaml
        except ImportError:
            raise ConfigurationError(
                "PyYAML is required to save YAML config files. "
                "Install with: pip install pyyaml"
            )
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)

    elif format == "toml":
        try:
            import tomli_w
        except ImportError:
            raise ConfigurationError(
                "tomli_w is required to save TOML config files. "
                "Install with: pip install tomli-w"
            )
        with open(path, "wb") as f:
            tomli_w.dump(data, f)

    else:
        raise ConfigurationError(f"Unsupported output format: {format}")


# Built-in configuration profiles
PROFILES = {
    "stealth": {
        "browser": {
            "stealth": True,
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        },
        "session": {
            "impersonate": "chrome120",
        },
    },
    "debug": {
        "browser": {
            "headless": False,
            "devtools": True,
            "slow_mo": 100,
        },
    },
    "fast": {
        "browser": {
            "timeout": 10000,
            "stealth": False,
        },
        "session": {
            "timeout": 10.0,
            "http2": True,
        },
        "page": {
            "timeout": 10000,
            "wait_until": "domcontentloaded",
        },
    },
    "mobile": {
        "browser": {
            "viewport": {"width": 375, "height": 812},
        },
        "page": {
            "is_mobile": True,
            "has_touch": True,
            "device_scale_factor": 3.0,
        },
    },
}


def load_profile(name: str) -> dict[str, Any]:
    """Load a built-in configuration profile.

    Args:
        name: Profile name (stealth, debug, fast, mobile)

    Returns:
        Profile configuration dictionary

    Raises:
        ConfigurationError: If profile not found
    """
    if name not in PROFILES:
        raise ConfigurationError(
            f"Unknown profile: {name}. "
            f"Available profiles: {', '.join(PROFILES.keys())}"
        )

    return PROFILES[name].copy()


def load_config_with_profile(
    profile: str,
    config_file: Optional[Union[str, Path]] = None,
    overrides: Optional[dict[str, Any]] = None,
) -> KuromiConfig:
    """Load configuration with a profile as base.

    Args:
        profile: Profile name
        config_file: Additional config file
        overrides: Programmatic overrides

    Returns:
        Loaded configuration
    """
    profile_config = load_profile(profile)

    loader = ConfigLoader(config_file=config_file, load_env=True)
    base_config = loader.load()

    # Merge: defaults < profile < file < env < overrides
    merged = merge_configs(
        base_config.to_dict(),
        profile_config,
        overrides or {},
    )

    return KuromiConfig.from_dict(merged)
