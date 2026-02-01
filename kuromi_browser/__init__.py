"""
kuromi-browser: Stealthy Python browser automation library.

A powerful browser automation library with anti-detection features,
AI/LLM integration, and a hybrid approach combining CDP control
with lightweight HTTP sessions.

Basic usage:
    from kuromi_browser import Browser, Page, StealthPage

    async with Browser() as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        content = await page.content()

With stealth mode:
    from kuromi_browser import Browser, Fingerprint

    fingerprint = Fingerprint.generate(browser="chrome", os="windows")
    async with Browser(stealth=True, fingerprint=fingerprint) as browser:
        page = await browser.new_page()
        await page.goto("https://bot-detection-site.com")

AI Agent usage:
    from kuromi_browser import Browser, Agent

    async with Browser() as browser:
        page = await browser.new_page()
        agent = Agent(page)
        result = await agent.run("Find the contact form and fill it out")
"""

__version__ = "0.1.0"
__author__ = "Kuromi"
__license__ = "MIT"

from kuromi_browser.models import (
    BrowserConfig,
    BrowserType,
    Cookie,
    Fingerprint,
    NavigatorProperties,
    NetworkRequest,
    NetworkResponse,
    PageConfig,
    PageMode,
    ProxyConfig,
    ScreenProperties,
    WebGLProperties,
)

from kuromi_browser.interfaces import (
    BaseAgent,
    BaseBrowser,
    BaseBrowserContext,
    BaseCDPSession,
    BaseElement,
    BasePage,
    BaseSession,
)

from kuromi_browser.page import (
    Element,
    HybridPage,
    Page,
    StealthPage,
)

from kuromi_browser.cdp import (
    CDPConnection,
    CDPSession,
)

from kuromi_browser.dom import (
    DOMElement,
    DOMParser,
)

from kuromi_browser.session import (
    Session,
    SessionPool,
)

from kuromi_browser.events import (
    Event,
    EventBus,
    EventEmitter,
    EventType,
)

from kuromi_browser.stealth import (
    FingerprintGenerator,
    StealthConfig,
    StealthPatches,
    apply_stealth,
)

from kuromi_browser.agent import (
    Agent,
    AgentActions,
    AgentConfig,
)

from kuromi_browser.browser import (
    Browser,
    BrowserContext,
    BrowserPool,
    BrowserProfile,
    BrowserState,
    ContextOptions,
    ProfileConfig,
    ProfileManager,
    Tab,
    TabManager,
    TabState,
)

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "BrowserConfig",
    "BrowserType",
    "Cookie",
    "Fingerprint",
    "NavigatorProperties",
    "NetworkRequest",
    "NetworkResponse",
    "PageConfig",
    "PageMode",
    "ProxyConfig",
    "ScreenProperties",
    "WebGLProperties",
    "BaseAgent",
    "BaseBrowser",
    "BaseBrowserContext",
    "BaseCDPSession",
    "BaseElement",
    "BasePage",
    "BaseSession",
    "Element",
    "HybridPage",
    "Page",
    "StealthPage",
    "CDPConnection",
    "CDPSession",
    "DOMElement",
    "DOMParser",
    "Session",
    "SessionPool",
    "Event",
    "EventBus",
    "EventEmitter",
    "EventType",
    "FingerprintGenerator",
    "StealthConfig",
    "StealthPatches",
    "apply_stealth",
    "Agent",
    "AgentActions",
    "AgentConfig",
    # Browser management
    "Browser",
    "BrowserContext",
    "BrowserPool",
    "BrowserProfile",
    "BrowserState",
    "ContextOptions",
    "ProfileConfig",
    "ProfileManager",
    "Tab",
    "TabManager",
    "TabState",
]
