"""Tests for elements module."""

import pytest

from kuromi_browser.elements import (
    Locator,
    LocatorType,
    ParsedLocator,
    SessionElement,
    NoneElement,
    NONE_ELEMENT,
    none_element,
)


class TestLocatorParse:
    """Tests for Locator.parse() method."""

    def test_parse_id_selector(self):
        """Test parsing ID selector."""
        result = Locator.parse("#submit")
        assert result == ("css", "#submit")

    def test_parse_class_selector(self):
        """Test parsing class selector."""
        result = Locator.parse(".button")
        assert result == ("css", ".button")

    def test_parse_tag_selector(self):
        """Test parsing tag selector."""
        result = Locator.parse("div")
        assert result == ("css", "div")

    def test_parse_attribute_selector(self):
        """Test parsing attribute selector."""
        result = Locator.parse("@name=email")
        assert result == ("css", '[name="email"]')

    def test_parse_attribute_exists(self):
        """Test parsing attribute exists selector."""
        result = Locator.parse("@disabled")
        assert result == ("css", "[disabled]")

    def test_parse_text_contains(self):
        """Test parsing text contains selector."""
        result = Locator.parse("text:Login")
        assert result == ("xpath", '//*[contains(text(), "Login")]')

    def test_parse_text_exact(self):
        """Test parsing exact text selector."""
        result = Locator.parse("text=Submit")
        assert result == ("xpath", '//*[text()="Submit"]')

    def test_parse_explicit_xpath(self):
        """Test parsing explicit XPath selector."""
        result = Locator.parse("x://div[@id='test']")
        assert result == ("xpath", "//div[@id='test']")

    def test_parse_auto_xpath(self):
        """Test parsing auto-detected XPath."""
        result = Locator.parse("//div/span")
        assert result == ("xpath", "//div/span")

    def test_parse_explicit_css(self):
        """Test parsing explicit CSS selector."""
        result = Locator.parse("css:div.class")
        assert result == ("css", "div.class")


class TestLocatorParseFull:
    """Tests for Locator.parse_full() method."""

    def test_parse_full_id(self):
        """Test parse_full with ID selector."""
        result = Locator.parse_full("#submit")
        assert result.type == LocatorType.ID
        assert result.value == "submit"
        assert result.index is None

    def test_parse_full_class(self):
        """Test parse_full with class selector."""
        result = Locator.parse_full(".button")
        assert result.type == LocatorType.CLASS
        assert result.value == "button"

    def test_parse_full_tag(self):
        """Test parse_full with tag selector."""
        result = Locator.parse_full("div")
        assert result.type == LocatorType.TAG
        assert result.value == "div"

    def test_parse_full_text(self):
        """Test parse_full with text selector."""
        result = Locator.parse_full("text:Login")
        assert result.type == LocatorType.TEXT
        assert result.value == "Login"

    def test_parse_full_text_exact(self):
        """Test parse_full with exact text selector."""
        result = Locator.parse_full("text=Submit")
        assert result.type == LocatorType.TEXT_EXACT
        assert result.value == "Submit"

    def test_parse_full_attr(self):
        """Test parse_full with attribute selector."""
        result = Locator.parse_full("@name=email")
        assert result.type == LocatorType.ATTR
        assert result.value == '[name="email"]'

    def test_parse_full_with_index(self):
        """Test parse_full with index suffix."""
        result = Locator.parse_full("button@i=2")
        assert result.type == LocatorType.TAG
        assert result.value == "button"
        assert result.index == 2

    def test_parse_full_combined_css(self):
        """Test parse_full with combined CSS selector."""
        result = Locator.parse_full("#id.class")
        assert result.type == LocatorType.CSS
        assert result.value == "#id.class"

    def test_parse_full_empty_raises(self):
        """Test that empty selector raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            Locator.parse_full("")


class TestParsedLocator:
    """Tests for ParsedLocator conversions."""

    def test_to_css_from_id(self):
        """Test to_css from ID locator."""
        locator = ParsedLocator(
            type=LocatorType.ID,
            value="submit",
            original="#submit",
        )
        assert locator.to_css() == "#submit"

    def test_to_css_from_class(self):
        """Test to_css from class locator."""
        locator = ParsedLocator(
            type=LocatorType.CLASS,
            value="button",
            original=".button",
        )
        assert locator.to_css() == ".button"

    def test_to_xpath_from_text(self):
        """Test to_xpath from text locator."""
        locator = ParsedLocator(
            type=LocatorType.TEXT,
            value="Login",
            original="text:Login",
        )
        assert locator.to_xpath() == '//*[contains(text(), "Login")]'

    def test_to_xpath_from_text_exact(self):
        """Test to_xpath from exact text locator."""
        locator = ParsedLocator(
            type=LocatorType.TEXT_EXACT,
            value="Submit",
            original="text=Submit",
        )
        assert locator.to_xpath() == '//*[text()="Submit"]'


class TestLocatorCssToXpath:
    """Tests for Locator.css_to_xpath() method."""

    def test_id_to_xpath(self):
        """Test converting ID selector to XPath."""
        result = Locator.css_to_xpath("#submit")
        assert result == '//*[@id="submit"]'

    def test_class_to_xpath(self):
        """Test converting class selector to XPath."""
        result = Locator.css_to_xpath(".button")
        assert result == '//*[contains(@class, "button")]'

    def test_tag_to_xpath(self):
        """Test converting tag selector to XPath."""
        result = Locator.css_to_xpath("div")
        assert result == "//div"

    def test_attr_to_xpath(self):
        """Test converting attribute selector to XPath."""
        result = Locator.css_to_xpath('[name="email"]')
        assert result == '//*[@name="email"]'


class TestLocatorCombine:
    """Tests for Locator.combine() method."""

    def test_combine_css_selectors(self):
        """Test combining CSS selectors."""
        result = Locator.combine("#parent", ".child")
        assert result == "#parent .child"

    def test_combine_with_xpath(self):
        """Test combining with XPath selector."""
        result = Locator.combine("#parent", "text:child")
        # Should convert to XPath when either is XPath
        assert "//" in result


class TestNoneElement:
    """Tests for NoneElement class."""

    def test_singleton(self):
        """Test NoneElement is singleton."""
        none1 = NoneElement()
        none2 = NoneElement()
        assert none1 is none2

    def test_none_element_function(self):
        """Test none_element() function returns singleton."""
        result = none_element()
        assert result is NONE_ELEMENT

    def test_exists_is_false(self):
        """Test exists property is False."""
        assert NONE_ELEMENT.exists is False

    def test_bool_is_false(self):
        """Test NoneElement is falsy."""
        assert bool(NONE_ELEMENT) is False

    def test_tag_is_empty(self):
        """Test tag returns empty string."""
        assert NONE_ELEMENT.tag == ""

    def test_text_is_empty(self):
        """Test text returns empty string."""
        assert NONE_ELEMENT.text == ""

    def test_attrs_is_empty(self):
        """Test attrs returns empty dict."""
        assert NONE_ELEMENT.attrs == {}

    def test_ele_returns_none_element(self):
        """Test ele() returns NoneElement."""
        result = NONE_ELEMENT.ele("#test")
        assert result is NONE_ELEMENT

    def test_eles_returns_empty_list(self):
        """Test eles() returns empty list."""
        result = NONE_ELEMENT.eles("#test")
        assert result == []

    def test_children_returns_empty_list(self):
        """Test children returns empty list."""
        assert NONE_ELEMENT.children == []

    def test_parent_returns_none_element(self):
        """Test parent returns NoneElement."""
        assert NONE_ELEMENT.parent is NONE_ELEMENT

    def test_next_returns_none_element(self):
        """Test next() returns NoneElement."""
        assert NONE_ELEMENT.next() is NONE_ELEMENT

    def test_prev_returns_none_element(self):
        """Test prev() returns NoneElement."""
        assert NONE_ELEMENT.prev() is NONE_ELEMENT

    def test_is_displayed_is_false(self):
        """Test is_displayed returns False."""
        assert NONE_ELEMENT.is_displayed() is False

    def test_links_returns_empty(self):
        """Test links() returns empty list."""
        assert NONE_ELEMENT.links() == []

    def test_images_returns_empty(self):
        """Test images() returns empty list."""
        assert NONE_ELEMENT.images() == []

    def test_iteration_is_empty(self):
        """Test iteration yields nothing."""
        items = list(NONE_ELEMENT)
        assert items == []

    def test_len_is_zero(self):
        """Test len() returns 0."""
        assert len(NONE_ELEMENT) == 0

    def test_equals_none(self):
        """Test NoneElement equals None."""
        assert NONE_ELEMENT == None  # noqa: E711
        assert NONE_ELEMENT == NoneElement()

    def test_attr_returns_default(self):
        """Test attr() returns default value."""
        assert NONE_ELEMENT.attr("href") is None
        assert NONE_ELEMENT.attr("href", "default") == "default"


class TestSessionElement:
    """Tests for SessionElement class."""

    @pytest.fixture
    def sample_html(self):
        """Sample HTML for testing."""
        return """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <div id="container" class="main-content wrapper">
                <h1>Title</h1>
                <p class="text">Some text content</p>
                <a href="/page1">Link 1</a>
                <a href="/page2">Link 2</a>
                <img src="/img1.png"/>
                <img src="/img2.jpg"/>
                <form id="myform">
                    <input name="email" value="test@example.com"/>
                    <input type="checkbox" name="agree" checked/>
                    <select name="country">
                        <option value="us">United States</option>
                        <option value="uk" selected>United Kingdom</option>
                    </select>
                </form>
            </div>
            <div id="sibling">Sibling content</div>
        </body>
        </html>
        """

    @pytest.fixture
    def doc(self, sample_html):
        """Create SessionElement from sample HTML."""
        return SessionElement.from_html(sample_html, base_url="https://example.com")

    def test_from_html(self, doc):
        """Test creating SessionElement from HTML."""
        assert doc.tag == "html"

    def test_ele_by_id(self, doc):
        """Test finding element by ID."""
        result = doc.ele("#container")
        assert result is not None
        assert result.tag == "div"
        assert result.id == "container"

    def test_ele_by_class(self, doc):
        """Test finding element by class."""
        result = doc.ele(".text")
        assert result is not None
        assert result.tag == "p"
        assert result.text == "Some text content"

    def test_ele_by_tag(self, doc):
        """Test finding element by tag."""
        result = doc.ele("h1")
        assert result is not None
        assert result.text == "Title"

    def test_ele_by_text(self, doc):
        """Test finding element by text content."""
        result = doc.ele("text:Title")
        assert result is not None
        assert result.tag == "h1"

    def test_eles_returns_list(self, doc):
        """Test eles() returns list of elements."""
        results = doc.eles("a")
        assert len(results) == 2
        assert all(el.tag == "a" for el in results)

    def test_ele_not_found(self, doc):
        """Test ele() returns None when not found."""
        result = doc.ele("#nonexistent")
        assert result is None

    def test_text_property(self, doc):
        """Test text property."""
        result = doc.ele("h1")
        assert result.text == "Title"

    def test_html_property(self, doc):
        """Test html property."""
        result = doc.ele("h1")
        assert "<h1>" in result.html
        assert "Title" in result.html

    def test_inner_html_property(self, doc):
        """Test inner_html property."""
        result = doc.ele("#container")
        assert "<h1>" in result.inner_html
        assert "Title" in result.inner_html

    def test_attrs_property(self, doc):
        """Test attrs property."""
        result = doc.ele("#container")
        assert result.attrs["id"] == "container"
        assert "main-content" in result.attrs["class"]

    def test_attr_method(self, doc):
        """Test attr() method."""
        result = doc.ele("#container")
        assert result.attr("id") == "container"
        assert result.attr("nonexistent") is None
        assert result.attr("nonexistent", "default") == "default"

    def test_classes_property(self, doc):
        """Test classes property."""
        result = doc.ele("#container")
        assert "main-content" in result.classes
        assert "wrapper" in result.classes

    def test_has_class(self, doc):
        """Test has_class() method."""
        result = doc.ele("#container")
        assert result.has_class("main-content") is True
        assert result.has_class("nonexistent") is False

    def test_parent_property(self, doc):
        """Test parent property."""
        result = doc.ele("h1")
        parent = result.parent
        assert parent is not None
        assert parent.id == "container"

    def test_children_property(self, doc):
        """Test children property."""
        result = doc.ele("#container")
        children = result.children
        assert len(children) > 0
        tags = [child.tag for child in children]
        assert "h1" in tags

    def test_next_sibling(self, doc):
        """Test next() method."""
        result = doc.ele("#container")
        sibling = result.next()
        assert sibling is not None
        assert sibling.id == "sibling"

    def test_prev_sibling(self, doc):
        """Test prev() method."""
        result = doc.ele("#sibling")
        sibling = result.prev()
        assert sibling is not None
        assert sibling.id == "container"

    def test_links(self, doc):
        """Test links() method."""
        container = doc.ele("#container")
        links = container.links()
        assert len(links) == 2
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links

    def test_images(self, doc):
        """Test images() method."""
        container = doc.ele("#container")
        images = container.images()
        assert len(images) == 2
        assert "https://example.com/img1.png" in images
        assert "https://example.com/img2.jpg" in images

    def test_link_property(self, doc):
        """Test link property on anchor element."""
        link = doc.ele("a")
        assert link.link == "https://example.com/page1"

    def test_src_property(self, doc):
        """Test src property on image element."""
        img = doc.ele("img")
        assert img.src == "https://example.com/img1.png"

    def test_form_data(self, doc):
        """Test form_data() method."""
        form = doc.ele("#myform")
        data = form.form_data()
        assert data["email"] == "test@example.com"
        assert data["agree"] == "on"
        assert data["country"] == "uk"

    def test_xpath_direct(self, doc):
        """Test xpath() method."""
        results = doc.xpath("//a")
        assert len(results) == 2

    def test_css_direct(self, doc):
        """Test css() method (with XPath fallback)."""
        results = doc.css("a")
        assert len(results) == 2

    def test_iteration(self, doc):
        """Test iteration over children."""
        container = doc.ele("#container")
        children = list(container)
        assert len(children) > 0

    def test_len(self, doc):
        """Test len() returns child count."""
        container = doc.ele("#container")
        assert len(container) > 0

    def test_bool_is_true(self, doc):
        """Test element is truthy."""
        result = doc.ele("#container")
        assert bool(result) is True

    def test_is_displayed(self, doc):
        """Test is_displayed() basic check."""
        result = doc.ele("#container")
        assert result.is_displayed() is True

    def test_from_fragment(self):
        """Test from_fragment() method."""
        html = "<div>A</div><div>B</div>"
        elements = SessionElement.from_fragment(html)
        assert len(elements) == 2
        assert elements[0].text == "A"
        assert elements[1].text == "B"

    def test_selector_with_index(self, doc):
        """Test selector with index suffix."""
        # Get second link
        result = doc.ele("a@i=1")
        assert result is not None
        assert result.link == "https://example.com/page2"

    def test_nested_query(self, doc):
        """Test nested element query."""
        container = doc.ele("#container")
        h1 = container.ele("h1")
        assert h1 is not None
        assert h1.text == "Title"


class TestLocatorEscapeText:
    """Tests for Locator.escape_text() method."""

    def test_escape_simple_text(self):
        """Test escaping simple text."""
        result = Locator.escape_text("Hello")
        assert result == "'Hello'"

    def test_escape_text_with_single_quote(self):
        """Test escaping text with single quote."""
        result = Locator.escape_text("It's good")
        assert '"' in result  # Should use double quotes

    def test_escape_text_with_double_quote(self):
        """Test escaping text with double quote."""
        result = Locator.escape_text('Say "Hello"')
        assert "'" in result  # Should use single quotes

    def test_escape_text_with_both_quotes(self):
        """Test escaping text with both quote types."""
        result = Locator.escape_text("It's \"complex\"")
        assert "concat" in result  # Should use concat


class TestLocatorIsXpath:
    """Tests for Locator.is_xpath() method."""

    def test_is_xpath_with_prefix(self):
        """Test is_xpath with x: prefix."""
        assert Locator.is_xpath("x://div") is True
        assert Locator.is_xpath("xpath://div") is True

    def test_is_xpath_with_text_prefix(self):
        """Test is_xpath with text: prefix."""
        assert Locator.is_xpath("text:Login") is True
        assert Locator.is_xpath("tx:Login") is True
        assert Locator.is_xpath("text=Login") is True

    def test_is_xpath_auto_detect(self):
        """Test is_xpath with auto-detected XPath."""
        assert Locator.is_xpath("/html/body") is True
        assert Locator.is_xpath("//div") is True
        assert Locator.is_xpath("(//div)[1]") is True

    def test_is_not_xpath(self):
        """Test is_xpath returns False for CSS."""
        assert Locator.is_xpath("#id") is False
        assert Locator.is_xpath(".class") is False
        assert Locator.is_xpath("div") is False
