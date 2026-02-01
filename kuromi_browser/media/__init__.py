"""
Media handling module for kuromi-browser.

Provides comprehensive media utilities including:
- Download manager with progress tracking
- Screenshot capture (viewport, full page, element)
- PDF export
- Screen recording/screencast
- Image comparison for visual regression testing

Example usage:

    # Download with progress tracking
    from kuromi_browser.media import DownloadManager, download_file

    manager = DownloadManager(downloads_path="/tmp/downloads")
    download = await manager.download_url(
        "https://example.com/file.zip",
        on_progress=lambda p: print(f"{p.percent:.1f}%")
    )
    await manager.wait_for_download(download)

    # Screenshot capture
    from kuromi_browser.media import ScreenshotCapture, take_screenshot

    capture = ScreenshotCapture(cdp_session)
    data = await capture.capture_full_page()

    # PDF export
    from kuromi_browser.media import PDFExporter, export_to_pdf

    exporter = PDFExporter(cdp_session)
    pdf_data = await exporter.export_with_header_footer()

    # Screen recording
    from kuromi_browser.media import PageRecorder, record_page

    recorder = PageRecorder(cdp_session, "/tmp/recording.mp4")
    await recorder.start()
    # ... perform actions ...
    await recorder.stop()

    # Image comparison
    from kuromi_browser.media import compare_images, ImageComparator

    result = compare_images("expected.png", "actual.png")
    if not result.match:
        print(f"Images differ by {result.diff_percent:.2f}%")
"""

# Download manager
from kuromi_browser.media.downloader import (
    Download,
    DownloadManager,
    DownloadProgress,
    DownloadState,
    calculate_file_hash,
    download_file,
)

# Screenshot utilities
from kuromi_browser.media.screenshot import (
    ClipRegion,
    ImageFormat,
    ScreenshotCapture,
    ScreenshotOptions,
    screenshot_element,
    take_screenshot,
)

# PDF export
from kuromi_browser.media.pdf import (
    Margin,
    PAPER_DIMENSIONS,
    PaperFormat,
    PDFExporter,
    PDFOptions,
    export_to_pdf,
    html_to_pdf,
)

# Screen recording
from kuromi_browser.media.recorder import (
    PageRecorder,
    RecordingFormat,
    Screencast,
    ScreencastFormat,
    ScreencastFrame,
    ScreencastOptions,
    TracingRecorder,
    record_page,
)

# Image comparison
from kuromi_browser.media.compare import (
    ComparisonMethod,
    ComparisonResult,
    ImageComparator,
    calculate_image_hash,
    compare_images,
    images_are_equal,
)

__all__ = [
    # Download manager
    "DownloadState",
    "DownloadProgress",
    "Download",
    "DownloadManager",
    "download_file",
    "calculate_file_hash",
    # Screenshot
    "ImageFormat",
    "ClipRegion",
    "ScreenshotOptions",
    "ScreenshotCapture",
    "take_screenshot",
    "screenshot_element",
    # PDF
    "PaperFormat",
    "PAPER_DIMENSIONS",
    "Margin",
    "PDFOptions",
    "PDFExporter",
    "export_to_pdf",
    "html_to_pdf",
    # Recording
    "RecordingFormat",
    "ScreencastFormat",
    "ScreencastFrame",
    "ScreencastOptions",
    "Screencast",
    "PageRecorder",
    "TracingRecorder",
    "record_page",
    # Image comparison
    "ComparisonMethod",
    "ComparisonResult",
    "ImageComparator",
    "compare_images",
    "images_are_equal",
    "calculate_image_hash",
]
