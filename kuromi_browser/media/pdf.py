"""
PDF export utilities for kuromi-browser.

Provides functionality to export pages to PDF with various options
including headers, footers, margins, and page sizing.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from kuromi_browser.cdp import CDPSession


class PaperFormat(str, Enum):
    """Standard paper formats."""

    LETTER = "letter"
    LEGAL = "legal"
    TABLOID = "tabloid"
    LEDGER = "ledger"
    A0 = "a0"
    A1 = "a1"
    A2 = "a2"
    A3 = "a3"
    A4 = "a4"
    A5 = "a5"
    A6 = "a6"


# Paper dimensions in inches
PAPER_DIMENSIONS: dict[PaperFormat, tuple[float, float]] = {
    PaperFormat.LETTER: (8.5, 11),
    PaperFormat.LEGAL: (8.5, 14),
    PaperFormat.TABLOID: (11, 17),
    PaperFormat.LEDGER: (17, 11),
    PaperFormat.A0: (33.1, 46.8),
    PaperFormat.A1: (23.4, 33.1),
    PaperFormat.A2: (16.54, 23.4),
    PaperFormat.A3: (11.7, 16.54),
    PaperFormat.A4: (8.27, 11.7),
    PaperFormat.A5: (5.83, 8.27),
    PaperFormat.A6: (4.13, 5.83),
}


@dataclass
class Margin:
    """PDF margin configuration."""

    top: str = "0.4in"
    bottom: str = "0.4in"
    left: str = "0.4in"
    right: str = "0.4in"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "top": self.top,
            "bottom": self.bottom,
            "left": self.left,
            "right": self.right,
        }


@dataclass
class PDFOptions:
    """PDF export configuration.

    Attributes:
        scale: Scale of the webpage rendering. Default 1.
        display_header_footer: Display header and footer.
        header_template: HTML template for header.
        footer_template: HTML template for footer.
        print_background: Print background graphics.
        landscape: Paper orientation.
        page_ranges: Paper ranges to print, e.g., '1-5, 8, 11-13'.
        format: Paper format.
        width: Paper width (overrides format).
        height: Paper height (overrides format).
        margin: Page margins.
        prefer_css_page_size: Prefer page size defined by CSS.
        generate_tagged_pdf: Generate tagged (accessible) PDF.
        generate_document_outline: Embed document outline.
    """

    scale: float = 1.0
    display_header_footer: bool = False
    header_template: str = ""
    footer_template: str = ""
    print_background: bool = False
    landscape: bool = False
    page_ranges: str = ""
    format: Optional[PaperFormat] = PaperFormat.LETTER
    width: Optional[str] = None
    height: Optional[str] = None
    margin: Optional[Margin] = None
    prefer_css_page_size: bool = False
    generate_tagged_pdf: bool = False
    generate_document_outline: bool = False

    def to_cdp_params(self) -> dict[str, Any]:
        """Convert to CDP parameters."""
        params: dict[str, Any] = {
            "scale": self.scale,
            "displayHeaderFooter": self.display_header_footer,
            "printBackground": self.print_background,
            "landscape": self.landscape,
            "preferCSSPageSize": self.prefer_css_page_size,
        }

        if self.header_template:
            params["headerTemplate"] = self.header_template

        if self.footer_template:
            params["footerTemplate"] = self.footer_template

        if self.page_ranges:
            params["pageRanges"] = self.page_ranges

        # Handle dimensions
        if self.width and self.height:
            params["paperWidth"] = self._parse_dimension(self.width)
            params["paperHeight"] = self._parse_dimension(self.height)
        elif self.format:
            width, height = PAPER_DIMENSIONS.get(
                self.format, PAPER_DIMENSIONS[PaperFormat.LETTER]
            )
            if self.landscape:
                width, height = height, width
            params["paperWidth"] = width
            params["paperHeight"] = height

        # Handle margins
        margin = self.margin or Margin()
        params["marginTop"] = self._parse_dimension(margin.top)
        params["marginBottom"] = self._parse_dimension(margin.bottom)
        params["marginLeft"] = self._parse_dimension(margin.left)
        params["marginRight"] = self._parse_dimension(margin.right)

        if self.generate_tagged_pdf:
            params["generateTaggedPDF"] = True

        if self.generate_document_outline:
            params["generateDocumentOutline"] = True

        return params

    @staticmethod
    def _parse_dimension(value: str) -> float:
        """Parse dimension string to inches."""
        value = value.strip().lower()

        if value.endswith("px"):
            return float(value[:-2]) / 96
        elif value.endswith("in"):
            return float(value[:-2])
        elif value.endswith("cm"):
            return float(value[:-2]) / 2.54
        elif value.endswith("mm"):
            return float(value[:-2]) / 25.4
        else:
            # Assume pixels
            try:
                return float(value) / 96
            except ValueError:
                return 0.4  # Default margin


class PDFExporter:
    """PDF export utility.

    Example:
        exporter = PDFExporter(cdp_session)

        # Basic export
        data = await exporter.export()

        # With options
        data = await exporter.export(
            options=PDFOptions(
                format=PaperFormat.A4,
                print_background=True,
                margin=Margin(top="1in", bottom="1in"),
            )
        )

        # Save to file
        await exporter.export_to_file("/tmp/page.pdf")
    """

    # Default header template
    DEFAULT_HEADER = """
    <div style="font-size: 10px; text-align: center; width: 100%;">
        <span class="title"></span>
    </div>
    """

    # Default footer template with page numbers
    DEFAULT_FOOTER = """
    <div style="font-size: 10px; text-align: center; width: 100%;">
        <span class="pageNumber"></span> / <span class="totalPages"></span>
    </div>
    """

    def __init__(self, cdp: "CDPSession") -> None:
        """Initialize PDF exporter.

        Args:
            cdp: CDP session to use for export.
        """
        self._cdp = cdp

    async def export(
        self,
        options: Optional[PDFOptions] = None,
    ) -> bytes:
        """Export current page to PDF.

        Args:
            options: PDF export options.

        Returns:
            PDF data as bytes.
        """
        options = options or PDFOptions()
        params = options.to_cdp_params()

        result = await self._cdp.send("Page.printToPDF", params)
        return base64.b64decode(result["data"])

    async def export_to_file(
        self,
        path: str | Path,
        options: Optional[PDFOptions] = None,
    ) -> Path:
        """Export current page to PDF file.

        Args:
            path: File path to save PDF.
            options: PDF export options.

        Returns:
            Path to saved file.
        """
        path = Path(path)

        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        data = await self.export(options)

        with open(path, "wb") as f:
            f.write(data)

        return path

    async def export_with_header_footer(
        self,
        *,
        header: Optional[str] = None,
        footer: Optional[str] = None,
        format: PaperFormat = PaperFormat.LETTER,
        print_background: bool = True,
        margin: Optional[Margin] = None,
    ) -> bytes:
        """Export with custom header and footer.

        Template placeholders:
        - date: Formatted print date
        - title: Document title
        - url: Document URL
        - pageNumber: Current page number
        - totalPages: Total number of pages

        Args:
            header: HTML template for header.
            footer: HTML template for footer.
            format: Paper format.
            print_background: Print background graphics.
            margin: Page margins.

        Returns:
            PDF data as bytes.
        """
        options = PDFOptions(
            display_header_footer=True,
            header_template=header or self.DEFAULT_HEADER,
            footer_template=footer or self.DEFAULT_FOOTER,
            format=format,
            print_background=print_background,
            margin=margin or Margin(top="1in", bottom="1in"),
        )

        return await self.export(options)

    async def export_landscape(
        self,
        format: PaperFormat = PaperFormat.LETTER,
        print_background: bool = False,
    ) -> bytes:
        """Export in landscape orientation.

        Args:
            format: Paper format.
            print_background: Print background graphics.

        Returns:
            PDF data as bytes.
        """
        options = PDFOptions(
            landscape=True,
            format=format,
            print_background=print_background,
        )

        return await self.export(options)

    async def export_selection(
        self,
        page_ranges: str,
        format: PaperFormat = PaperFormat.LETTER,
    ) -> bytes:
        """Export specific page ranges.

        Args:
            page_ranges: Page ranges (e.g., '1-5, 8, 11-13').
            format: Paper format.

        Returns:
            PDF data as bytes.
        """
        options = PDFOptions(
            page_ranges=page_ranges,
            format=format,
        )

        return await self.export(options)


async def export_to_pdf(
    cdp: "CDPSession",
    *,
    path: Optional[str | Path] = None,
    format: PaperFormat = PaperFormat.LETTER,
    print_background: bool = False,
    landscape: bool = False,
    scale: float = 1.0,
    margin: Optional[Margin] = None,
) -> bytes:
    """Convenience function to export page to PDF.

    Args:
        cdp: CDP session.
        path: Optional path to save PDF.
        format: Paper format.
        print_background: Print background graphics.
        landscape: Landscape orientation.
        scale: Page scale.
        margin: Page margins.

    Returns:
        PDF data as bytes.

    Example:
        # Export and return bytes
        data = await export_to_pdf(cdp)

        # Export and save to file
        data = await export_to_pdf(cdp, path="/tmp/page.pdf")
    """
    exporter = PDFExporter(cdp)

    options = PDFOptions(
        format=format,
        print_background=print_background,
        landscape=landscape,
        scale=scale,
        margin=margin,
    )

    data = await exporter.export(options)

    if path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    return data


async def html_to_pdf(
    cdp: "CDPSession",
    html: str,
    *,
    path: Optional[str | Path] = None,
    format: PaperFormat = PaperFormat.LETTER,
    print_background: bool = True,
    base_url: Optional[str] = None,
) -> bytes:
    """Convert HTML string to PDF.

    Args:
        cdp: CDP session.
        html: HTML content to convert.
        path: Optional path to save PDF.
        format: Paper format.
        print_background: Print background graphics.
        base_url: Base URL for resolving relative resources.

    Returns:
        PDF data as bytes.

    Example:
        pdf_data = await html_to_pdf(
            cdp,
            "<h1>Hello World</h1><p>This is a test.</p>",
            path="/tmp/output.pdf"
        )
    """
    # Get current frame
    frame_result = await cdp.send("Page.getFrameTree")
    frame_id = frame_result["frameTree"]["frame"]["id"]

    # Set content
    await cdp.send(
        "Page.setDocumentContent",
        {"frameId": frame_id, "html": html},
    )

    # Wait for content to load
    await cdp.send(
        "Runtime.evaluate",
        {"expression": "document.readyState === 'complete'", "awaitPromise": True},
    )

    # Export to PDF
    return await export_to_pdf(
        cdp,
        path=path,
        format=format,
        print_background=print_background,
    )


__all__ = [
    "PaperFormat",
    "PAPER_DIMENSIONS",
    "Margin",
    "PDFOptions",
    "PDFExporter",
    "export_to_pdf",
    "html_to_pdf",
]
