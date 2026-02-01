"""
DOM Serializer for LLM consumption in kuromi-browser.

This module converts DOM structures into text/JSON formats optimized for
LLM understanding, including accessibility tree serialization.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from kuromi_browser.page import Page


class SerializationFormat(str, Enum):
    """Output format for DOM serialization."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    ACCESSIBILITY = "accessibility"


@dataclass
class ElementInfo:
    """Serialized information about a DOM element."""

    tag: str
    role: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    value: Optional[str] = None
    selector: Optional[str] = None
    attributes: dict[str, str] = field(default_factory=dict)
    bounding_box: Optional[dict[str, float]] = None
    is_visible: bool = True
    is_interactive: bool = False
    children: list["ElementInfo"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "tag": self.tag,
        }
        if self.role:
            result["role"] = self.role
        if self.name:
            result["name"] = self.name
        if self.text:
            result["text"] = self.text[:100]  # Truncate long text
        if self.value:
            result["value"] = self.value
        if self.selector:
            result["selector"] = self.selector
        if self.attributes:
            result["attributes"] = self.attributes
        if self.bounding_box:
            result["box"] = self.bounding_box
        if self.is_interactive:
            result["interactive"] = True
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result


@dataclass
class DOMSnapshot:
    """Complete DOM snapshot for LLM consumption."""

    url: str
    title: str
    elements: list[ElementInfo]
    forms: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)
    images: list[dict[str, str]] = field(default_factory=list)
    text_content: str = ""
    viewport: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "viewport": self.viewport,
            "elements": [e.to_dict() for e in self.elements],
            "forms": self.forms,
            "links": self.links[:50],  # Limit links
            "images": self.images[:20],  # Limit images
        }

    def to_text(self) -> str:
        """Convert to plain text description."""
        lines = [
            f"Page: {self.title}",
            f"URL: {self.url}",
            "",
            "Interactive Elements:",
        ]

        for i, el in enumerate(self.elements[:50]):  # Limit elements
            if el.is_interactive:
                desc = self._describe_element(el, i)
                lines.append(desc)

        if self.forms:
            lines.extend(["", "Forms:"])
            for form in self.forms[:5]:
                lines.append(f"  - {form.get('action', 'unknown')} ({len(form.get('fields', []))} fields)")

        if self.links:
            lines.extend(["", f"Links: {len(self.links)} total"])

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        lines = [
            f"# {self.title}",
            f"**URL:** {self.url}",
            "",
            "## Interactive Elements",
            "",
        ]

        for i, el in enumerate(self.elements[:50]):
            if el.is_interactive:
                desc = self._describe_element_md(el, i)
                lines.append(desc)

        if self.forms:
            lines.extend(["", "## Forms", ""])
            for form in self.forms[:5]:
                lines.append(f"- **{form.get('action', 'Form')}**: {len(form.get('fields', []))} fields")

        return "\n".join(lines)

    def _describe_element(self, el: ElementInfo, index: int) -> str:
        """Create a text description of an element."""
        parts = [f"[{index}]"]

        if el.role:
            parts.append(f"({el.role})")
        else:
            parts.append(f"<{el.tag}>")

        if el.name:
            parts.append(f'"{el.name}"')
        elif el.text:
            text = el.text[:50] + "..." if len(el.text) > 50 else el.text
            parts.append(f'"{text}"')

        if el.selector:
            parts.append(f"selector={el.selector}")

        return " ".join(parts)

    def _describe_element_md(self, el: ElementInfo, index: int) -> str:
        """Create a markdown description of an element."""
        role_or_tag = el.role or el.tag
        name_or_text = el.name or (el.text[:50] + "..." if el.text and len(el.text) > 50 else el.text) or ""

        return f"- `[{index}]` **{role_or_tag}**: {name_or_text} (`{el.selector or el.tag}`)"


class DOMSerializer:
    """Serializes DOM content for LLM consumption.

    Supports multiple output formats optimized for different LLM use cases:
    - TEXT: Simple text list of elements
    - JSON: Structured data for function calling
    - MARKDOWN: Readable format for chat models
    - ACCESSIBILITY: Based on accessibility tree

    Example:
        serializer = DOMSerializer(page)
        snapshot = await serializer.serialize()
        llm_input = snapshot.to_markdown()
    """

    # Interactive element tags
    INTERACTIVE_TAGS = {
        "a", "button", "input", "select", "textarea",
        "details", "summary", "dialog",
    }

    # Interactive roles
    INTERACTIVE_ROLES = {
        "button", "link", "textbox", "combobox", "listbox",
        "checkbox", "radio", "switch", "slider", "spinbutton",
        "searchbox", "menu", "menuitem", "tab", "treeitem",
    }

    # Attributes to capture
    IMPORTANT_ATTRS = {
        "id", "name", "type", "placeholder", "value",
        "href", "src", "alt", "title", "aria-label",
        "aria-labelledby", "aria-describedby", "role",
        "data-testid", "data-cy", "data-test",
    }

    def __init__(
        self,
        page: "Page",
        *,
        max_elements: int = 100,
        include_hidden: bool = False,
        max_depth: int = 10,
    ) -> None:
        """Initialize DOM serializer.

        Args:
            page: Browser page to serialize.
            max_elements: Maximum number of elements to include.
            include_hidden: Whether to include hidden elements.
            max_depth: Maximum DOM tree depth to traverse.
        """
        self._page = page
        self._max_elements = max_elements
        self._include_hidden = include_hidden
        self._max_depth = max_depth

    async def serialize(
        self,
        format: SerializationFormat = SerializationFormat.MARKDOWN,
    ) -> DOMSnapshot:
        """Serialize the current page DOM.

        Args:
            format: Output format (affects internal processing).

        Returns:
            DOMSnapshot with serialized page content.
        """
        # Get basic page info
        url = self._page.url
        title = self._page.title

        # Get viewport size
        viewport = await self._page.evaluate(
            "() => ({ width: window.innerWidth, height: window.innerHeight })"
        ) or {"width": 0, "height": 0}

        # Get interactive elements
        elements = await self._get_interactive_elements()

        # Get forms
        forms = await self._get_forms()

        # Get links
        links = await self._get_links()

        # Get images
        images = await self._get_images()

        return DOMSnapshot(
            url=url,
            title=title,
            elements=elements,
            forms=forms,
            links=links,
            images=images,
            viewport=viewport,
        )

    async def serialize_accessibility_tree(self) -> str:
        """Serialize the accessibility tree.

        Returns:
            Text representation of the accessibility tree.
        """
        # Use CDP to get accessibility tree
        tree = await self._page.evaluate("""
            () => {
                function serializeNode(node, depth = 0) {
                    if (depth > 10) return '';

                    const indent = '  '.repeat(depth);
                    const lines = [];

                    // Get computed accessibility properties
                    const role = node.getAttribute('role') ||
                                getImplicitRole(node) || node.tagName.toLowerCase();
                    const name = getAccessibleName(node);

                    // Only include meaningful nodes
                    if (isInteractive(node) || name) {
                        let line = `${indent}[${role}]`;
                        if (name) line += ` "${name}"`;

                        // Add value for inputs
                        if (node.value !== undefined && node.value !== '') {
                            line += ` value="${node.value}"`;
                        }

                        // Add state
                        if (node.disabled) line += ' (disabled)';
                        if (node.checked) line += ' (checked)';
                        if (node.selected) line += ' (selected)';

                        lines.push(line);
                    }

                    // Process children
                    for (const child of node.children) {
                        const childText = serializeNode(child, depth + 1);
                        if (childText) lines.push(childText);
                    }

                    return lines.join('\\n');
                }

                function getImplicitRole(el) {
                    const tag = el.tagName.toLowerCase();
                    const type = el.type?.toLowerCase();

                    const roleMap = {
                        'a': el.href ? 'link' : null,
                        'button': 'button',
                        'input': {
                            'button': 'button',
                            'checkbox': 'checkbox',
                            'radio': 'radio',
                            'range': 'slider',
                            'search': 'searchbox',
                            'text': 'textbox',
                            'email': 'textbox',
                            'password': 'textbox',
                            'tel': 'textbox',
                            'url': 'textbox',
                        }[type] || 'textbox',
                        'select': 'combobox',
                        'textarea': 'textbox',
                        'img': 'img',
                        'nav': 'navigation',
                        'main': 'main',
                        'header': 'banner',
                        'footer': 'contentinfo',
                        'aside': 'complementary',
                        'form': 'form',
                        'table': 'table',
                        'ul': 'list',
                        'ol': 'list',
                        'li': 'listitem',
                    };

                    return typeof roleMap[tag] === 'object' ? roleMap[tag] : roleMap[tag];
                }

                function getAccessibleName(el) {
                    // aria-label takes precedence
                    if (el.getAttribute('aria-label')) {
                        return el.getAttribute('aria-label');
                    }

                    // aria-labelledby
                    const labelledBy = el.getAttribute('aria-labelledby');
                    if (labelledBy) {
                        const label = document.getElementById(labelledBy);
                        if (label) return label.textContent.trim();
                    }

                    // For inputs, check associated label
                    if (el.id) {
                        const label = document.querySelector(`label[for="${el.id}"]`);
                        if (label) return label.textContent.trim();
                    }

                    // Placeholder for inputs
                    if (el.placeholder) return el.placeholder;

                    // alt for images
                    if (el.alt) return el.alt;

                    // title
                    if (el.title) return el.title;

                    // Text content for buttons and links
                    const tag = el.tagName.toLowerCase();
                    if (['button', 'a', 'label'].includes(tag)) {
                        return el.textContent.trim().slice(0, 50);
                    }

                    return null;
                }

                function isInteractive(el) {
                    const tag = el.tagName.toLowerCase();
                    const interactiveTags = ['a', 'button', 'input', 'select', 'textarea'];
                    if (interactiveTags.includes(tag)) return true;

                    const role = el.getAttribute('role');
                    const interactiveRoles = ['button', 'link', 'textbox', 'checkbox', 'radio', 'combobox'];
                    if (role && interactiveRoles.includes(role)) return true;

                    if (el.onclick || el.getAttribute('onclick')) return true;
                    if (el.tabIndex >= 0) return true;

                    return false;
                }

                return serializeNode(document.body);
            }
        """)

        return tree or ""

    async def get_element_by_index(self, index: int) -> Optional[str]:
        """Get a selector for an element by its index in the serialized output.

        Args:
            index: Element index from serialized output.

        Returns:
            CSS selector for the element or None.
        """
        elements = await self._get_interactive_elements()
        if 0 <= index < len(elements):
            return elements[index].selector
        return None

    async def _get_interactive_elements(self) -> list[ElementInfo]:
        """Get all interactive elements from the page."""
        elements_data = await self._page.evaluate(f"""
            () => {{
                const elements = [];
                const seen = new Set();
                let index = 0;
                const maxElements = {self._max_elements};

                function processElement(el) {{
                    if (index >= maxElements) return;
                    if (seen.has(el)) return;
                    seen.add(el);

                    // Check visibility
                    const style = window.getComputedStyle(el);
                    const isVisible = style.display !== 'none' &&
                                    style.visibility !== 'hidden' &&
                                    style.opacity !== '0' &&
                                    el.offsetWidth > 0 &&
                                    el.offsetHeight > 0;

                    if (!isVisible && !{str(self._include_hidden).lower()}) return;

                    const tag = el.tagName.toLowerCase();
                    const role = el.getAttribute('role');

                    // Check if interactive
                    const interactiveTags = ['a', 'button', 'input', 'select', 'textarea', 'details', 'summary'];
                    const interactiveRoles = ['button', 'link', 'textbox', 'combobox', 'listbox', 'checkbox', 'radio', 'switch', 'slider', 'spinbutton', 'searchbox', 'menu', 'menuitem', 'tab', 'treeitem'];

                    const isInteractive = interactiveTags.includes(tag) ||
                                        (role && interactiveRoles.includes(role)) ||
                                        el.onclick !== null ||
                                        el.getAttribute('onclick') !== null ||
                                        el.tabIndex >= 0;

                    if (!isInteractive) return;

                    // Build selector
                    let selector = tag;
                    if (el.id) {{
                        selector = `#${{el.id}}`;
                    }} else if (el.getAttribute('data-testid')) {{
                        selector = `[${{el.getAttribute('data-testid')}}]`;
                    }} else if (el.name) {{
                        selector = `${{tag}}[name="${{el.name}}"]`;
                    }} else if (el.className && typeof el.className === 'string') {{
                        const classes = el.className.trim().split(/\\s+/).slice(0, 2).join('.');
                        if (classes) selector = `${{tag}}.${{classes}}`;
                    }}

                    // Get bounding box
                    const rect = el.getBoundingClientRect();

                    // Get accessible name
                    let name = el.getAttribute('aria-label') ||
                              el.getAttribute('title') ||
                              el.placeholder ||
                              el.alt;

                    if (!name && el.id) {{
                        const label = document.querySelector(`label[for="${{el.id}}"]`);
                        if (label) name = label.textContent.trim();
                    }}

                    if (!name && ['button', 'a'].includes(tag)) {{
                        name = el.textContent.trim().slice(0, 50);
                    }}

                    // Get text content
                    let text = null;
                    if (!name) {{
                        text = el.textContent?.trim().slice(0, 100);
                    }}

                    // Get value
                    let value = null;
                    if (el.value !== undefined && el.value !== '') {{
                        value = String(el.value).slice(0, 100);
                    }}

                    // Get important attributes
                    const attrs = {{}};
                    const importantAttrs = ['id', 'name', 'type', 'placeholder', 'href', 'src', 'alt', 'aria-label', 'data-testid'];
                    for (const attr of importantAttrs) {{
                        const val = el.getAttribute(attr);
                        if (val) attrs[attr] = val.slice(0, 100);
                    }}

                    elements.push({{
                        tag: tag,
                        role: role,
                        name: name,
                        text: text,
                        value: value,
                        selector: selector,
                        attributes: attrs,
                        bounding_box: {{
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height,
                        }},
                        is_visible: isVisible,
                        is_interactive: true,
                    }});

                    index++;
                }}

                // Process all elements
                document.querySelectorAll('*').forEach(processElement);

                return elements;
            }}
        """)

        if not elements_data:
            return []

        return [
            ElementInfo(
                tag=el.get("tag", ""),
                role=el.get("role"),
                name=el.get("name"),
                text=el.get("text"),
                value=el.get("value"),
                selector=el.get("selector"),
                attributes=el.get("attributes", {}),
                bounding_box=el.get("bounding_box"),
                is_visible=el.get("is_visible", True),
                is_interactive=el.get("is_interactive", True),
            )
            for el in elements_data
        ]

    async def _get_forms(self) -> list[dict[str, Any]]:
        """Get all forms from the page."""
        forms = await self._page.evaluate("""
            () => {
                const forms = [];
                document.querySelectorAll('form').forEach((form, i) => {
                    const fields = [];
                    form.querySelectorAll('input, select, textarea').forEach(el => {
                        fields.push({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || null,
                            name: el.name || null,
                            id: el.id || null,
                            placeholder: el.placeholder || null,
                            required: el.required || false,
                        });
                    });

                    forms.push({
                        index: i,
                        id: form.id || null,
                        action: form.action || null,
                        method: form.method || 'get',
                        fields: fields,
                    });
                });
                return forms;
            }
        """)

        return forms or []

    async def _get_links(self) -> list[dict[str, str]]:
        """Get all links from the page."""
        links = await self._page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const text = a.textContent.trim().slice(0, 50);
                    if (text || a.getAttribute('aria-label')) {
                        links.push({
                            text: text || a.getAttribute('aria-label') || '',
                            href: a.href,
                            title: a.title || null,
                        });
                    }
                });
                return links.slice(0, 100);
            }
        """)

        return links or []

    async def _get_images(self) -> list[dict[str, str]]:
        """Get all images from the page."""
        images = await self._page.evaluate("""
            () => {
                const images = [];
                document.querySelectorAll('img[src]').forEach(img => {
                    images.push({
                        src: img.src,
                        alt: img.alt || null,
                        title: img.title || null,
                    });
                });
                return images.slice(0, 50);
            }
        """)

        return images or []


async def serialize_page_for_llm(
    page: "Page",
    *,
    format: SerializationFormat = SerializationFormat.MARKDOWN,
    max_elements: int = 100,
) -> str:
    """Convenience function to serialize a page for LLM input.

    Args:
        page: Browser page to serialize.
        format: Output format.
        max_elements: Maximum elements to include.

    Returns:
        Serialized page content as string.
    """
    serializer = DOMSerializer(page, max_elements=max_elements)
    snapshot = await serializer.serialize(format)

    if format == SerializationFormat.TEXT:
        return snapshot.to_text()
    elif format == SerializationFormat.MARKDOWN:
        return snapshot.to_markdown()
    elif format == SerializationFormat.JSON:
        import json
        return json.dumps(snapshot.to_dict(), indent=2)
    elif format == SerializationFormat.ACCESSIBILITY:
        return await serializer.serialize_accessibility_tree()
    else:
        return snapshot.to_text()


__all__ = [
    "SerializationFormat",
    "ElementInfo",
    "DOMSnapshot",
    "DOMSerializer",
    "serialize_page_for_llm",
]
