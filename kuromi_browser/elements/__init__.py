"""
Element System for kuromi-browser.

This module provides a unified interface for working with DOM elements
across different contexts:

- **BrowserElement**: CDP-based live DOM elements for browser automation
- **SessionElement**: lxml-based elements for HTTP response parsing
- **NoneElement**: Null object pattern for safe chaining
- **ShadowDOM**: Utilities for Shadow DOM traversal
- **Iframe**: Cross-iframe element finding

Example usage:

    # Browser automation
    from kuromi_browser import Browser

    async with Browser() as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")

        # Find elements
        button = await page.ele('#submit')
        await button.click()

        # Chained queries
        text = await page.ele('.container').find('.item').text_content()

    # HTTP response parsing
    from kuromi_browser.elements import SessionElement

    response = await session.get("https://example.com")
    doc = SessionElement.from_html(response.text, base_url=response.url)

    # Query elements
    title = doc.ele('title').text
    links = doc.links()

Selector Syntax:

    The Locator parser supports various selector formats:

    - `#id` -> CSS ID selector
    - `.class` -> CSS class selector
    - `tag` -> Tag name
    - `@attr=value` -> Attribute selector
    - `text:content` -> Text contains (XPath)
    - `text=content` -> Exact text match
    - `x:xpath` -> Explicit XPath
    - `css:selector` -> Explicit CSS
    - `/xpath` -> Auto-detected XPath
    - `selector@i=N` -> Nth element

"""

from kuromi_browser.elements.base import ActionableElement, BaseElement
from kuromi_browser.elements.browser_element import BrowserElement
from kuromi_browser.elements.iframe import FrameContext, FrameInfo, IframeHelper
from kuromi_browser.elements.locator import Locator, LocatorType, ParsedLocator
from kuromi_browser.elements.none_element import (
    NONE_ELEMENT,
    NoneElement,
    none_element,
)
from kuromi_browser.elements.session_element import HTMLElement, SessionElement
from kuromi_browser.elements.shadow import ShadowDOMHelper, ShadowRoot

__all__ = [
    # Base classes
    "BaseElement",
    "ActionableElement",
    # Element implementations
    "BrowserElement",
    "SessionElement",
    "HTMLElement",  # Alias for SessionElement
    # Null object pattern
    "NoneElement",
    "NONE_ELEMENT",
    "none_element",
    # Locator
    "Locator",
    "LocatorType",
    "ParsedLocator",
    # Shadow DOM
    "ShadowRoot",
    "ShadowDOMHelper",
    # Iframe
    "FrameInfo",
    "FrameContext",
    "IframeHelper",
]
