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
    from kuromi_browser.llm import OpenAIProvider
    from kuromi_browser.ai import AIAgent, DOMSerializer, VisionAnalyzer

    async with Browser() as browser:
        page = await browser.new_page()

        # Simple agent
        llm = OpenAIProvider()
        agent = Agent(llm, page)
        result = await agent.run("Find the contact form and fill it out")

        # Or use high-level AIAgent
        ai = AIAgent(page, llm)
        result = await ai.run("Search for Python tutorials")
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
    create_agent,
)

from kuromi_browser.ai import (
    AIAgent,
    DOMSerializer,
    DOMSnapshot,
    SerializationFormat,
    VisionAnalyzer,
    ScreenshotAnalysis,
    AnalysisType,
    TaskParser,
    ParsedTask,
    TaskType,
    create_ai_agent,
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

from kuromi_browser.media import (
    ComparisonMethod,
    ComparisonResult,
    Download,
    DownloadManager,
    DownloadProgress,
    DownloadState,
    ImageComparator,
    ImageFormat,
    Margin,
    PageRecorder,
    PaperFormat,
    PDFExporter,
    PDFOptions,
    Screencast,
    ScreencastFrame,
    ScreenshotCapture,
    ScreenshotOptions,
    compare_images,
    download_file,
    export_to_pdf,
    record_page,
    take_screenshot,
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
    "create_agent",
    # AI integration
    "AIAgent",
    "DOMSerializer",
    "DOMSnapshot",
    "SerializationFormat",
    "VisionAnalyzer",
    "ScreenshotAnalysis",
    "AnalysisType",
    "TaskParser",
    "ParsedTask",
    "TaskType",
    "create_ai_agent",
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
    # Media handling
    "ComparisonMethod",
    "ComparisonResult",
    "Download",
    "DownloadManager",
    "DownloadProgress",
    "DownloadState",
    "ImageComparator",
    "ImageFormat",
    "Margin",
    "PageRecorder",
    "PaperFormat",
    "PDFExporter",
    "PDFOptions",
    "Screencast",
    "ScreencastFrame",
    "ScreenshotCapture",
    "ScreenshotOptions",
    "compare_images",
    "download_file",
    "export_to_pdf",
    "record_page",
    "take_screenshot",
]
