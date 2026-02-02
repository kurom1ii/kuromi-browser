"""
Abstract base interfaces for kuromi-browser.

This module defines the abstract base classes that all implementations must follow.
These interfaces ensure consistent behavior across different page modes and backends.
"""

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Optional,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    from kuromi_browser.models import (
        BrowserConfig,
        Cookie,
        Fingerprint,
        FrameInfo,
        NetworkRequest,
        NetworkResponse,
        PageConfig,
    )

T = TypeVar("T")
ElementType = TypeVar("ElementType", bound="BaseElement")


class BaseElement(ABC):
    """Abstract base class for DOM elements.

    Provides a consistent interface for interacting with elements
    regardless of the underlying implementation (CDP, HTTP parsing, etc.)
    """

    @property
    @abstractmethod
    def tag_name(self) -> str:
        """Get the element's tag name."""
        ...

    @abstractmethod
    async def get_attribute(self, name: str) -> Optional[str]:
        """Get an attribute value from the element."""
        ...

    @abstractmethod
    async def get_property(self, name: str) -> Any:
        """Get a JavaScript property from the element."""
        ...

    @abstractmethod
    async def text_content(self) -> Optional[str]:
        """Get the text content of the element."""
        ...

    @abstractmethod
    async def inner_text(self) -> str:
        """Get the inner text of the element."""
        ...

    @abstractmethod
    async def inner_html(self) -> str:
        """Get the inner HTML of the element."""
        ...

    @abstractmethod
    async def outer_html(self) -> str:
        """Get the outer HTML of the element."""
        ...

    @abstractmethod
    async def bounding_box(self) -> Optional[dict[str, float]]:
        """Get the element's bounding box (x, y, width, height)."""
        ...

    @abstractmethod
    async def is_visible(self) -> bool:
        """Check if the element is visible in the viewport."""
        ...

    @abstractmethod
    async def is_enabled(self) -> bool:
        """Check if the element is enabled."""
        ...

    @abstractmethod
    async def is_checked(self) -> bool:
        """Check if the element (checkbox/radio) is checked."""
        ...

    @abstractmethod
    async def click(
        self,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Click the element."""
        ...

    @abstractmethod
    async def dblclick(
        self,
        *,
        button: str = "left",
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Double-click the element."""
        ...

    @abstractmethod
    async def hover(
        self,
        *,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over the element."""
        ...

    @abstractmethod
    async def fill(
        self,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill the element with text (for input fields)."""
        ...

    @abstractmethod
    async def type(
        self,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text into the element character by character."""
        ...

    @abstractmethod
    async def press(
        self,
        key: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Press a key while focused on the element."""
        ...

    @abstractmethod
    async def select_option(
        self,
        *values: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Select options in a <select> element."""
        ...

    @abstractmethod
    async def check(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Check a checkbox or radio button."""
        ...

    @abstractmethod
    async def uncheck(
        self,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Uncheck a checkbox."""
        ...

    @abstractmethod
    async def focus(self) -> None:
        """Focus the element."""
        ...

    @abstractmethod
    async def scroll_into_view(self) -> None:
        """Scroll the element into view."""
        ...

    @abstractmethod
    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False,
    ) -> bytes:
        """Take a screenshot of the element."""
        ...

    @abstractmethod
    async def query_selector(self, selector: str) -> Optional["BaseElement"]:
        """Find a child element matching the selector."""
        ...

    @abstractmethod
    async def query_selector_all(self, selector: str) -> list["BaseElement"]:
        """Find all child elements matching the selector."""
        ...

    @abstractmethod
    async def evaluate(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript in the context of the element."""
        ...


class BasePage(ABC):
    """Abstract base class for page interactions.

    Provides a unified interface for browser automation that works across
    different page modes (BROWSER, SESSION, HYBRID).
    """

    @property
    @abstractmethod
    def url(self) -> str:
        """Get the current page URL."""
        ...

    @property
    @abstractmethod
    def title(self) -> str:
        """Get the page title."""
        ...

    @abstractmethod
    async def goto(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
        referer: Optional[str] = None,
    ) -> Optional["NetworkResponse"]:
        """Navigate to a URL."""
        ...

    @abstractmethod
    async def reload(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Reload the page."""
        ...

    @abstractmethod
    async def go_back(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate back in history."""
        ...

    @abstractmethod
    async def go_forward(
        self,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> Optional["NetworkResponse"]:
        """Navigate forward in history."""
        ...

    @abstractmethod
    async def content(self) -> str:
        """Get the page HTML content."""
        ...

    @abstractmethod
    async def set_content(
        self,
        html: str,
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Set the page HTML content."""
        ...

    @abstractmethod
    async def query_selector(self, selector: str) -> Optional[BaseElement]:
        """Find an element matching the selector."""
        ...

    @abstractmethod
    async def query_selector_all(self, selector: str) -> list[BaseElement]:
        """Find all elements matching the selector."""
        ...

    @abstractmethod
    async def wait_for_selector(
        self,
        selector: str,
        *,
        state: str = "visible",
        timeout: Optional[float] = None,
    ) -> Optional[BaseElement]:
        """Wait for an element to appear."""
        ...

    @abstractmethod
    async def wait_for_load_state(
        self,
        state: str = "load",
        *,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait for the page to reach a load state."""
        ...

    @abstractmethod
    async def wait_for_url(
        self,
        url: Union[str, Callable[[str], bool]],
        *,
        timeout: Optional[float] = None,
        wait_until: str = "load",
    ) -> None:
        """Wait for navigation to a URL."""
        ...

    @abstractmethod
    async def wait_for_timeout(self, timeout: float) -> None:
        """Wait for a specified time in milliseconds."""
        ...

    @abstractmethod
    async def click(
        self,
        selector: str,
        *,
        button: str = "left",
        click_count: int = 1,
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Click an element."""
        ...

    @abstractmethod
    async def dblclick(
        self,
        selector: str,
        *,
        button: str = "left",
        delay: float = 0,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Double-click an element."""
        ...

    @abstractmethod
    async def fill(
        self,
        selector: str,
        value: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Fill an input field."""
        ...

    @abstractmethod
    async def type(
        self,
        selector: str,
        text: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Type text character by character."""
        ...

    @abstractmethod
    async def press(
        self,
        selector: str,
        key: str,
        *,
        delay: float = 0,
        timeout: Optional[float] = None,
    ) -> None:
        """Press a key."""
        ...

    @abstractmethod
    async def hover(
        self,
        selector: str,
        *,
        force: bool = False,
        modifiers: Optional[list[str]] = None,
        position: Optional[dict[str, float]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """Hover over an element."""
        ...

    @abstractmethod
    async def select_option(
        self,
        selector: str,
        *values: str,
        timeout: Optional[float] = None,
    ) -> list[str]:
        """Select options in a <select> element."""
        ...

    @abstractmethod
    async def check(
        self,
        selector: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Check a checkbox or radio button."""
        ...

    @abstractmethod
    async def uncheck(
        self,
        selector: str,
        *,
        force: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        """Uncheck a checkbox."""
        ...

    @abstractmethod
    async def evaluate(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript in the page."""
        ...

    @abstractmethod
    async def evaluate_handle(
        self,
        expression: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript and return a handle to the result."""
        ...

    @abstractmethod
    async def add_script_tag(
        self,
        *,
        url: Optional[str] = None,
        path: Optional[str] = None,
        content: Optional[str] = None,
        type: str = "",
    ) -> BaseElement:
        """Add a <script> tag to the page."""
        ...

    @abstractmethod
    async def add_style_tag(
        self,
        *,
        url: Optional[str] = None,
        path: Optional[str] = None,
        content: Optional[str] = None,
    ) -> BaseElement:
        """Add a <style> tag to the page."""
        ...

    @abstractmethod
    async def screenshot(
        self,
        *,
        path: Optional[str] = None,
        full_page: bool = False,
        clip: Optional[dict[str, float]] = None,
        type: str = "png",
        quality: Optional[int] = None,
        omit_background: bool = False,
    ) -> bytes:
        """Take a screenshot of the page."""
        ...

    @abstractmethod
    async def pdf(
        self,
        *,
        path: Optional[str] = None,
        scale: float = 1,
        display_header_footer: bool = False,
        header_template: str = "",
        footer_template: str = "",
        print_background: bool = False,
        landscape: bool = False,
        page_ranges: str = "",
        format: str = "Letter",
        width: Optional[str] = None,
        height: Optional[str] = None,
        margin: Optional[dict[str, str]] = None,
        prefer_css_page_size: bool = False,
    ) -> bytes:
        """Generate a PDF of the page."""
        ...

    @abstractmethod
    async def get_cookies(
        self,
        *urls: str,
    ) -> list["Cookie"]:
        """Get cookies."""
        ...

    @abstractmethod
    async def set_cookies(
        self,
        *cookies: "Cookie",
    ) -> None:
        """Set cookies."""
        ...

    @abstractmethod
    async def delete_cookies(
        self,
        *names: str,
    ) -> None:
        """Delete cookies by name."""
        ...

    @abstractmethod
    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        ...

    @abstractmethod
    async def set_extra_http_headers(
        self,
        headers: dict[str, str],
    ) -> None:
        """Set extra HTTP headers."""
        ...

    @abstractmethod
    async def set_viewport(
        self,
        width: int,
        height: int,
        *,
        device_scale_factor: float = 1,
        is_mobile: bool = False,
        has_touch: bool = False,
    ) -> None:
        """Set the viewport size."""
        ...

    @abstractmethod
    async def expose_function(
        self,
        name: str,
        callback: Callable[..., Any],
    ) -> None:
        """Expose a Python function to JavaScript."""
        ...

    @abstractmethod
    async def route(
        self,
        url: Union[str, Callable[[str], bool]],
        handler: Callable[["NetworkRequest"], Awaitable[Optional["NetworkResponse"]]],
    ) -> None:
        """Intercept network requests."""
        ...

    @abstractmethod
    async def unroute(
        self,
        url: Union[str, Callable[[str], bool]],
    ) -> None:
        """Remove a route handler."""
        ...

    @abstractmethod
    def on(
        self,
        event: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register an event handler."""
        ...

    @abstractmethod
    def off(
        self,
        event: str,
        handler: Callable[..., Any],
    ) -> None:
        """Remove an event handler."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the page."""
        ...


class BaseSession(ABC):
    """Abstract base class for HTTP sessions.

    Provides a lightweight HTTP client interface with fingerprint spoofing
    via curl_cffi for scenarios where full browser automation isn't needed.
    """

    @property
    @abstractmethod
    def cookies(self) -> dict[str, str]:
        """Get current session cookies."""
        ...

    @abstractmethod
    async def get(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform a GET request."""
        ...

    @abstractmethod
    async def post(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform a POST request."""
        ...

    @abstractmethod
    async def put(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform a PUT request."""
        ...

    @abstractmethod
    async def patch(
        self,
        url: str,
        *,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform a PATCH request."""
        ...

    @abstractmethod
    async def delete(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform a DELETE request."""
        ...

    @abstractmethod
    async def head(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform a HEAD request."""
        ...

    @abstractmethod
    async def options(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform an OPTIONS request."""
        ...

    @abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[Union[dict[str, Any], str, bytes]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        follow_redirects: bool = True,
    ) -> "NetworkResponse":
        """Perform an arbitrary HTTP request."""
        ...

    @abstractmethod
    async def set_fingerprint(self, fingerprint: "Fingerprint") -> None:
        """Set the fingerprint for TLS/JA3 spoofing."""
        ...

    @abstractmethod
    async def set_proxy(self, proxy: str) -> None:
        """Set the proxy for requests."""
        ...

    @abstractmethod
    async def set_cookies(self, cookies: dict[str, str]) -> None:
        """Set session cookies."""
        ...

    @abstractmethod
    async def clear_cookies(self) -> None:
        """Clear all session cookies."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the session."""
        ...


class BaseBrowser(ABC):
    """Abstract base class for browser control.

    Manages the browser process and provides methods to create new pages/contexts.
    """

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the browser is connected."""
        ...

    @property
    @abstractmethod
    def contexts(self) -> list["BaseBrowserContext"]:
        """Get all browser contexts."""
        ...

    @abstractmethod
    async def new_context(
        self,
        *,
        config: Optional["PageConfig"] = None,
        fingerprint: Optional["Fingerprint"] = None,
    ) -> "BaseBrowserContext":
        """Create a new browser context."""
        ...

    @abstractmethod
    async def new_page(
        self,
        *,
        config: Optional["PageConfig"] = None,
        fingerprint: Optional["Fingerprint"] = None,
    ) -> BasePage:
        """Create a new page in the default context."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the browser."""
        ...

    @abstractmethod
    async def version(self) -> str:
        """Get the browser version."""
        ...


class BaseBrowserContext(ABC):
    """Abstract base class for browser contexts.

    A browser context is an isolated session within a browser with its own
    cookies, storage, and settings.
    """

    @property
    @abstractmethod
    def browser(self) -> BaseBrowser:
        """Get the parent browser."""
        ...

    @property
    @abstractmethod
    def pages(self) -> list[BasePage]:
        """Get all pages in this context."""
        ...

    @abstractmethod
    async def new_page(
        self,
        *,
        config: Optional["PageConfig"] = None,
    ) -> BasePage:
        """Create a new page in this context."""
        ...

    @abstractmethod
    async def get_cookies(
        self,
        *urls: str,
    ) -> list["Cookie"]:
        """Get cookies for the context."""
        ...

    @abstractmethod
    async def set_cookies(
        self,
        *cookies: "Cookie",
    ) -> None:
        """Set cookies for the context."""
        ...

    @abstractmethod
    async def clear_cookies(self) -> None:
        """Clear all cookies in the context."""
        ...

    @abstractmethod
    async def add_init_script(
        self,
        script: str,
    ) -> None:
        """Add a script to run on every new page."""
        ...

    @abstractmethod
    async def expose_function(
        self,
        name: str,
        callback: Callable[..., Any],
    ) -> None:
        """Expose a function to all pages in this context."""
        ...

    @abstractmethod
    async def route(
        self,
        url: Union[str, Callable[[str], bool]],
        handler: Callable[["NetworkRequest"], Awaitable[Optional["NetworkResponse"]]],
    ) -> None:
        """Intercept network requests for all pages."""
        ...

    @abstractmethod
    async def unroute(
        self,
        url: Union[str, Callable[[str], bool]],
    ) -> None:
        """Remove a route handler."""
        ...

    @abstractmethod
    async def set_geolocation(
        self,
        latitude: float,
        longitude: float,
        *,
        accuracy: float = 0,
    ) -> None:
        """Set geolocation for the context."""
        ...

    @abstractmethod
    async def set_permissions(
        self,
        permissions: list[str],
        *,
        origin: Optional[str] = None,
    ) -> None:
        """Set permissions for the context."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the context and all its pages."""
        ...


class BaseCDPSession(ABC):
    """Abstract base class for Chrome DevTools Protocol sessions.

    Provides low-level access to CDP commands for advanced automation scenarios.
    """

    @abstractmethod
    async def send(
        self,
        method: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Send a CDP command and wait for response."""
        ...

    @abstractmethod
    def on(
        self,
        event: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Register a CDP event handler."""
        ...

    @abstractmethod
    def off(
        self,
        event: str,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Remove a CDP event handler."""
        ...

    @abstractmethod
    async def detach(self) -> None:
        """Detach from the CDP session."""
        ...


class BaseAgent(ABC):
    """Abstract base class for AI-powered browser agents.

    Provides an interface for LLM-driven browser automation.
    """

    @abstractmethod
    async def run(
        self,
        task: str,
        *,
        max_steps: int = 100,
        timeout: Optional[float] = None,
    ) -> Any:
        """Run an AI agent to complete a task."""
        ...

    @abstractmethod
    async def step(
        self,
        instruction: str,
    ) -> Any:
        """Execute a single step based on an instruction."""
        ...

    @abstractmethod
    async def observe(self) -> dict[str, Any]:
        """Observe the current state of the page."""
        ...

    @abstractmethod
    async def act(
        self,
        action: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Perform an action on the page."""
        ...

    @abstractmethod
    async def plan(
        self,
        goal: str,
    ) -> list[str]:
        """Generate a plan to achieve a goal."""
        ...

    @abstractmethod
    async def reflect(
        self,
        observation: dict[str, Any],
        action: str,
        result: Any,
    ) -> str:
        """Reflect on an action's result."""
        ...
