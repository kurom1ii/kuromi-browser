"""
Browser Management module for kuromi-browser.

This module provides comprehensive browser management including:
- Tab management (create, switch, close tabs)
- Window/context management (isolated browsing sessions)
- Profile management (persistent user data)
- Multi-browser instance support
- Browser lifecycle hooks

Example:
    from kuromi_browser.browser import Browser, ProfileManager, ProfileConfig

    # Basic usage
    async with Browser() as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")

    # With profile
    profiles = ProfileManager()
    profile = await profiles.create(ProfileConfig(name="Work"))

    async with Browser(profile=profile) as browser:
        # Data persists across sessions
        page = await browser.new_page()

    # Multiple contexts (like incognito)
    async with Browser() as browser:
        context1 = await browser.new_context()
        context2 = await browser.new_context()
        # Isolated storage between contexts

    # Tab management
    async with Browser() as browser:
        tabs = browser.tabs

        tab1 = await tabs.new("https://google.com")
        tab2 = await tabs.new("https://github.com")

        await tabs.activate(tab1.id)
        await tabs.close(tab2.id)

    # Browser pool for concurrent automation
    async with BrowserPool(max_browsers=5) as pool:
        async with pool.acquire_context() as browser:
            page = await browser.new_page()
            await page.goto("https://example.com")
"""

from kuromi_browser.browser.browser import (
    Browser,
    BrowserPool,
    BrowserState,
    close_all_browsers,
    get_all_browsers,
)

from kuromi_browser.browser.tabs import (
    Tab,
    TabInfo,
    TabManager,
    TabState,
)

from kuromi_browser.browser.context import (
    BrowserContext,
    ContextInfo,
    ContextOptions,
    ContextState,
    DefaultContext,
)

from kuromi_browser.browser.profiles import (
    BrowserProfile,
    ProfileConfig,
    ProfileManager,
    ProfileMetadata,
    ProfileState,
    TemporaryProfile,
)

from kuromi_browser.browser.windows import (
    Window,
    WindowBounds,
    WindowController,
    WindowInfo,
    WindowState,
)

from kuromi_browser.browser.hooks import (
    Hook,
    HookContext,
    HookManager,
    HookPhase,
    after_load,
    before_navigate,
    get_global_hooks,
    on_error,
    on_request,
)

__all__ = [
    # Browser
    "Browser",
    "BrowserPool",
    "BrowserState",
    "close_all_browsers",
    "get_all_browsers",
    # Tabs
    "Tab",
    "TabInfo",
    "TabManager",
    "TabState",
    # Context
    "BrowserContext",
    "ContextInfo",
    "ContextOptions",
    "ContextState",
    "DefaultContext",
    # Profiles
    "BrowserProfile",
    "ProfileConfig",
    "ProfileManager",
    "ProfileMetadata",
    "ProfileState",
    "TemporaryProfile",
    # Windows
    "Window",
    "WindowBounds",
    "WindowController",
    "WindowInfo",
    "WindowState",
    # Hooks
    "Hook",
    "HookContext",
    "HookManager",
    "HookPhase",
    "after_load",
    "before_navigate",
    "get_global_hooks",
    "on_error",
    "on_request",
]
