"""
Plugin loader for kuromi-browser.

Handles loading plugins from files, packages, and registering them
with the plugin manager.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from .base import Plugin, PluginContext, PluginMetadata, PluginState

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Error loading a plugin."""

    def __init__(self, plugin_name: str, message: str) -> None:
        self.plugin_name = plugin_name
        super().__init__(f"Failed to load plugin '{plugin_name}': {message}")


class PluginManager:
    """Manages plugin lifecycle and execution.

    Handles loading, enabling, disabling, and coordinating plugins.

    Example:
        manager = PluginManager()

        # Load plugins
        manager.load_plugin(LoggingPlugin())
        manager.load_from_module("my_plugins.custom")
        manager.load_from_directory("./plugins")

        # Initialize all plugins
        await manager.initialize(plugin_context)

        # Enable specific plugins
        await manager.enable("logging")

        # Use with browser
        async with Browser(plugin_manager=manager) as browser:
            # Plugins are active
            pass

        # Cleanup
        await manager.shutdown()
    """

    def __init__(self) -> None:
        """Initialize plugin manager."""
        self._plugins: Dict[str, Plugin] = {}
        self._load_order: List[str] = []
        self._context: Optional[PluginContext] = None
        self._initialized = False

    @property
    def plugins(self) -> Dict[str, Plugin]:
        """Get all loaded plugins."""
        return dict(self._plugins)

    @property
    def enabled_plugins(self) -> List[Plugin]:
        """Get list of enabled plugins."""
        return [p for p in self._plugins.values() if p.is_enabled]

    def load_plugin(self, plugin: Plugin) -> None:
        """Load a plugin instance.

        Args:
            plugin: Plugin instance to load.

        Raises:
            PluginLoadError: If plugin with same name exists.
        """
        name = plugin.name

        if name in self._plugins:
            raise PluginLoadError(name, "Plugin with this name already loaded")

        # Check dependencies
        for dep in plugin.metadata.dependencies:
            if dep not in self._plugins:
                raise PluginLoadError(
                    name, f"Missing dependency: {dep}"
                )

        self._plugins[name] = plugin
        self._load_order.append(name)
        logger.info(f"Loaded plugin: {name} v{plugin.version}")

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin.

        Args:
            name: Plugin name to unload.

        Returns:
            True if unloaded.
        """
        if name not in self._plugins:
            return False

        plugin = self._plugins[name]

        # Check if other plugins depend on this one
        for other_name, other_plugin in self._plugins.items():
            if name in other_plugin.metadata.dependencies:
                logger.warning(
                    f"Cannot unload {name}: plugin {other_name} depends on it"
                )
                return False

        del self._plugins[name]
        self._load_order.remove(name)
        logger.info(f"Unloaded plugin: {name}")
        return True

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name.

        Args:
            name: Plugin name.

        Returns:
            Plugin instance or None.
        """
        return self._plugins.get(name)

    def has_plugin(self, name: str) -> bool:
        """Check if a plugin is loaded.

        Args:
            name: Plugin name.

        Returns:
            True if loaded.
        """
        return name in self._plugins

    def load_from_class(self, plugin_class: Type[Plugin]) -> Plugin:
        """Load a plugin from a class.

        Args:
            plugin_class: Plugin class to instantiate.

        Returns:
            Loaded plugin instance.
        """
        plugin = plugin_class()
        self.load_plugin(plugin)
        return plugin

    def load_from_module(self, module_name: str) -> List[Plugin]:
        """Load plugins from a Python module.

        Scans the module for Plugin subclasses and loads them.

        Args:
            module_name: Module name to import.

        Returns:
            List of loaded plugins.
        """
        loaded: List[Plugin] = []

        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise PluginLoadError(module_name, f"Cannot import module: {e}")

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Plugin)
                and obj is not Plugin
                and not inspect.isabstract(obj)
            ):
                try:
                    plugin = obj()
                    self.load_plugin(plugin)
                    loaded.append(plugin)
                except Exception as e:
                    logger.error(f"Failed to load plugin {name}: {e}")

        return loaded

    def load_from_file(self, file_path: Union[str, Path]) -> List[Plugin]:
        """Load plugins from a Python file.

        Args:
            file_path: Path to Python file.

        Returns:
            List of loaded plugins.
        """
        path = Path(file_path)
        if not path.exists():
            raise PluginLoadError(str(path), "File not found")

        if not path.suffix == ".py":
            raise PluginLoadError(str(path), "Not a Python file")

        # Generate unique module name
        module_name = f"kuromi_plugins_{path.stem}_{id(path)}"

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(str(path), "Cannot create module spec")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            del sys.modules[module_name]
            raise PluginLoadError(str(path), f"Error executing module: {e}")

        loaded: List[Plugin] = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Plugin)
                and obj is not Plugin
                and not inspect.isabstract(obj)
                and obj.__module__ == module_name
            ):
                try:
                    plugin = obj()
                    self.load_plugin(plugin)
                    loaded.append(plugin)
                except Exception as e:
                    logger.error(f"Failed to load plugin {name}: {e}")

        return loaded

    def load_from_directory(
        self,
        directory: Union[str, Path],
        *,
        recursive: bool = False,
    ) -> List[Plugin]:
        """Load plugins from a directory.

        Args:
            directory: Directory path.
            recursive: Scan subdirectories.

        Returns:
            List of loaded plugins.
        """
        path = Path(directory)
        if not path.exists():
            raise PluginLoadError(str(path), "Directory not found")

        if not path.is_dir():
            raise PluginLoadError(str(path), "Not a directory")

        loaded: List[Plugin] = []
        pattern = "**/*.py" if recursive else "*.py"

        for file_path in path.glob(pattern):
            if file_path.name.startswith("_"):
                continue

            try:
                plugins = self.load_from_file(file_path)
                loaded.extend(plugins)
            except PluginLoadError as e:
                logger.warning(f"Skipping {file_path}: {e}")

        return loaded

    async def initialize(self, context: PluginContext) -> None:
        """Initialize all loaded plugins.

        Args:
            context: Plugin context to pass to plugins.
        """
        self._context = context

        # Initialize in load order (respects dependencies)
        for name in self._load_order:
            plugin = self._plugins[name]
            try:
                await plugin.initialize(context)
            except Exception as e:
                logger.error(f"Failed to initialize plugin {name}: {e}")
                plugin._state = PluginState.ERROR

        self._initialized = True

    async def enable(self, name: str) -> bool:
        """Enable a specific plugin.

        Args:
            name: Plugin name.

        Returns:
            True if enabled.
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        if plugin.state == PluginState.ERROR:
            logger.warning(f"Cannot enable plugin {name}: in error state")
            return False

        # Enable dependencies first
        for dep in plugin.metadata.dependencies:
            if dep in self._plugins and not self._plugins[dep].is_enabled:
                await self.enable(dep)

        await plugin.enable()
        return True

    async def disable(self, name: str) -> bool:
        """Disable a specific plugin.

        Args:
            name: Plugin name.

        Returns:
            True if disabled.
        """
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        # Check if other enabled plugins depend on this one
        for other_name, other_plugin in self._plugins.items():
            if (
                other_plugin.is_enabled
                and name in other_plugin.metadata.dependencies
            ):
                logger.warning(
                    f"Cannot disable {name}: plugin {other_name} depends on it"
                )
                return False

        await plugin.disable()
        return True

    async def enable_all(self) -> None:
        """Enable all plugins."""
        for name in self._load_order:
            await self.enable(name)

    async def disable_all(self) -> None:
        """Disable all plugins."""
        # Disable in reverse order
        for name in reversed(self._load_order):
            plugin = self._plugins.get(name)
            if plugin and plugin.is_enabled:
                await plugin.disable()

    async def shutdown(self) -> None:
        """Shutdown and destroy all plugins."""
        # Disable all first
        await self.disable_all()

        # Destroy in reverse order
        for name in reversed(self._load_order):
            plugin = self._plugins.get(name)
            if plugin:
                try:
                    await plugin.destroy()
                except Exception as e:
                    logger.error(f"Error destroying plugin {name}: {e}")

        self._plugins.clear()
        self._load_order.clear()
        self._initialized = False

    def get_plugins_by_tag(self, tag: str) -> List[Plugin]:
        """Get plugins with a specific tag.

        Args:
            tag: Tag to filter by.

        Returns:
            List of matching plugins.
        """
        return [
            p for p in self._plugins.values()
            if tag in p.metadata.tags
        ]

    def get_plugins_by_state(self, state: PluginState) -> List[Plugin]:
        """Get plugins in a specific state.

        Args:
            state: State to filter by.

        Returns:
            List of matching plugins.
        """
        return [
            p for p in self._plugins.values()
            if p.state == state
        ]

    def __len__(self) -> int:
        """Number of loaded plugins."""
        return len(self._plugins)

    def __contains__(self, name: str) -> bool:
        """Check if plugin is loaded."""
        return name in self._plugins

    def __iter__(self):
        """Iterate over plugins in load order."""
        for name in self._load_order:
            yield self._plugins[name]


class PluginDiscovery:
    """Discovers plugins from various sources.

    Example:
        discovery = PluginDiscovery()
        discovery.add_search_path("./plugins")
        discovery.add_package("my_plugins")

        # Find all plugins
        plugins = discovery.discover()

        # Load into manager
        for plugin_class in plugins:
            manager.load_from_class(plugin_class)
    """

    def __init__(self) -> None:
        """Initialize discovery."""
        self._search_paths: List[Path] = []
        self._packages: List[str] = []

    def add_search_path(self, path: Union[str, Path]) -> "PluginDiscovery":
        """Add a directory to search for plugins.

        Args:
            path: Directory path.

        Returns:
            Self for chaining.
        """
        self._search_paths.append(Path(path))
        return self

    def add_package(self, package_name: str) -> "PluginDiscovery":
        """Add a package to scan for plugins.

        Args:
            package_name: Package name.

        Returns:
            Self for chaining.
        """
        self._packages.append(package_name)
        return self

    def discover(self) -> List[Type[Plugin]]:
        """Discover all plugin classes.

        Returns:
            List of plugin classes.
        """
        discovered: List[Type[Plugin]] = []

        # Scan packages
        for package_name in self._packages:
            try:
                module = importlib.import_module(package_name)
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, Plugin)
                        and obj is not Plugin
                        and not inspect.isabstract(obj)
                    ):
                        discovered.append(obj)
            except ImportError as e:
                logger.warning(f"Cannot import package {package_name}: {e}")

        # Scan directories
        for search_path in self._search_paths:
            if not search_path.exists():
                continue

            for file_path in search_path.glob("**/*.py"):
                if file_path.name.startswith("_"):
                    continue

                module_name = f"kuromi_discover_{file_path.stem}_{id(file_path)}"
                spec = importlib.util.spec_from_file_location(
                    module_name, file_path
                )
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)

                try:
                    spec.loader.exec_module(module)
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, Plugin)
                            and obj is not Plugin
                            and not inspect.isabstract(obj)
                            and obj.__module__ == module_name
                        ):
                            discovered.append(obj)
                except Exception as e:
                    logger.warning(f"Error loading {file_path}: {e}")

        return discovered


__all__ = [
    "PluginManager",
    "PluginDiscovery",
    "PluginLoadError",
]
