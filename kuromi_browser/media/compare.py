"""
Image comparison utilities for kuromi-browser.

Provides functionality to compare screenshots for visual regression testing
and other image comparison tasks.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import io


class ComparisonMethod(str, Enum):
    """Image comparison methods."""

    PIXEL = "pixel"
    SSIM = "ssim"
    HASH = "hash"
    HISTOGRAM = "histogram"


@dataclass
class ComparisonResult:
    """Result of image comparison.

    Attributes:
        match: Whether images match within threshold.
        similarity: Similarity score (0.0 to 1.0, 1.0 = identical).
        difference: Difference score (0.0 to 1.0, 0.0 = identical).
        diff_pixels: Number of different pixels (for pixel comparison).
        total_pixels: Total pixels compared.
        diff_image: Difference visualization image (if generated).
        method: Comparison method used.
        threshold: Threshold used for matching.
    """

    match: bool
    similarity: float
    difference: float
    diff_pixels: int = 0
    total_pixels: int = 0
    diff_image: Optional[bytes] = None
    method: ComparisonMethod = ComparisonMethod.PIXEL
    threshold: float = 0.0

    @property
    def diff_percent(self) -> float:
        """Get difference as percentage."""
        return self.difference * 100

    @property
    def similarity_percent(self) -> float:
        """Get similarity as percentage."""
        return self.similarity * 100


class ImageComparator:
    """Compare images for visual regression testing.

    Supports multiple comparison methods:
    - Pixel: Direct pixel-by-pixel comparison
    - SSIM: Structural Similarity Index
    - Hash: Perceptual hashing
    - Histogram: Color histogram comparison

    Example:
        comparator = ImageComparator()

        # Compare two images
        result = comparator.compare(image1, image2)
        print(f"Match: {result.match}, Similarity: {result.similarity:.2%}")

        # Save diff image
        if result.diff_image:
            with open("diff.png", "wb") as f:
                f.write(result.diff_image)
    """

    def __init__(
        self,
        threshold: float = 0.01,
        method: ComparisonMethod = ComparisonMethod.PIXEL,
    ) -> None:
        """Initialize image comparator.

        Args:
            threshold: Difference threshold for matching (0.0 to 1.0).
            method: Default comparison method.
        """
        self._threshold = threshold
        self._method = method

    @property
    def threshold(self) -> float:
        """Get comparison threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Set comparison threshold."""
        self._threshold = max(0.0, min(1.0, value))

    def compare(
        self,
        image1: Union[bytes, str, Path],
        image2: Union[bytes, str, Path],
        *,
        method: Optional[ComparisonMethod] = None,
        threshold: Optional[float] = None,
        generate_diff: bool = True,
    ) -> ComparisonResult:
        """Compare two images.

        Args:
            image1: First image (bytes, file path, or Path).
            image2: Second image (bytes, file path, or Path).
            method: Comparison method to use.
            threshold: Difference threshold for matching.
            generate_diff: Generate difference visualization.

        Returns:
            Comparison result.
        """
        method = method or self._method
        threshold = threshold if threshold is not None else self._threshold

        # Load images
        img1 = self._load_image(image1)
        img2 = self._load_image(image2)

        if method == ComparisonMethod.PIXEL:
            return self._compare_pixels(img1, img2, threshold, generate_diff)
        elif method == ComparisonMethod.SSIM:
            return self._compare_ssim(img1, img2, threshold, generate_diff)
        elif method == ComparisonMethod.HASH:
            return self._compare_hash(img1, img2, threshold)
        elif method == ComparisonMethod.HISTOGRAM:
            return self._compare_histogram(img1, img2, threshold)
        else:
            return self._compare_pixels(img1, img2, threshold, generate_diff)

    def _load_image(self, image: Union[bytes, str, Path]) -> "Image.Image":
        """Load image from various sources."""
        try:
            from PIL import Image
        except ImportError:
            raise ImportError(
                "Pillow is required for image comparison: pip install Pillow"
            )

        if isinstance(image, bytes):
            return Image.open(io.BytesIO(image))
        else:
            return Image.open(image)

    def _compare_pixels(
        self,
        img1: "Image.Image",
        img2: "Image.Image",
        threshold: float,
        generate_diff: bool,
    ) -> ComparisonResult:
        """Pixel-by-pixel comparison."""
        from PIL import Image, ImageChops

        # Ensure same size
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.LANCZOS)

        # Convert to same mode
        img1 = img1.convert("RGBA")
        img2 = img2.convert("RGBA")

        # Calculate difference
        diff = ImageChops.difference(img1, img2)

        # Count different pixels
        diff_data = diff.getdata()
        diff_pixels = sum(
            1 for pixel in diff_data if any(c > 0 for c in pixel[:3])
        )
        total_pixels = img1.width * img1.height

        # Calculate difference ratio
        difference = diff_pixels / total_pixels if total_pixels > 0 else 0.0
        similarity = 1.0 - difference
        match = difference <= threshold

        # Generate diff image
        diff_image = None
        if generate_diff and diff_pixels > 0:
            diff_image = self._generate_diff_image(img1, img2, diff)

        return ComparisonResult(
            match=match,
            similarity=similarity,
            difference=difference,
            diff_pixels=diff_pixels,
            total_pixels=total_pixels,
            diff_image=diff_image,
            method=ComparisonMethod.PIXEL,
            threshold=threshold,
        )

    def _compare_ssim(
        self,
        img1: "Image.Image",
        img2: "Image.Image",
        threshold: float,
        generate_diff: bool,
    ) -> ComparisonResult:
        """Structural Similarity Index comparison."""
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            raise ImportError(
                "NumPy is required for SSIM comparison: pip install numpy"
            )

        # Ensure same size
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.LANCZOS)

        # Convert to grayscale numpy arrays
        arr1 = np.array(img1.convert("L"), dtype=np.float64)
        arr2 = np.array(img2.convert("L"), dtype=np.float64)

        # Calculate SSIM
        similarity = self._calculate_ssim(arr1, arr2)
        difference = 1.0 - similarity
        match = difference <= threshold

        # Generate diff image
        diff_image = None
        if generate_diff:
            diff_image = self._generate_ssim_diff(img1, img2, arr1, arr2)

        return ComparisonResult(
            match=match,
            similarity=similarity,
            difference=difference,
            total_pixels=img1.width * img1.height,
            diff_image=diff_image,
            method=ComparisonMethod.SSIM,
            threshold=threshold,
        )

    def _calculate_ssim(
        self,
        arr1: "np.ndarray",
        arr2: "np.ndarray",
        k1: float = 0.01,
        k2: float = 0.03,
        L: float = 255,
    ) -> float:
        """Calculate SSIM between two arrays."""
        import numpy as np

        c1 = (k1 * L) ** 2
        c2 = (k2 * L) ** 2

        mu1 = arr1.mean()
        mu2 = arr2.mean()
        sigma1_sq = arr1.var()
        sigma2_sq = arr2.var()
        sigma12 = np.cov(arr1.flat, arr2.flat)[0, 1]

        ssim = ((2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)) / (
            (mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)
        )

        return float(ssim)

    def _compare_hash(
        self,
        img1: "Image.Image",
        img2: "Image.Image",
        threshold: float,
    ) -> ComparisonResult:
        """Perceptual hash comparison."""
        hash1 = self._calculate_phash(img1)
        hash2 = self._calculate_phash(img2)

        # Calculate Hamming distance
        hamming = bin(hash1 ^ hash2).count("1")
        max_bits = 64  # 8x8 hash

        difference = hamming / max_bits
        similarity = 1.0 - difference
        match = difference <= threshold

        return ComparisonResult(
            match=match,
            similarity=similarity,
            difference=difference,
            method=ComparisonMethod.HASH,
            threshold=threshold,
        )

    def _calculate_phash(self, img: "Image.Image") -> int:
        """Calculate perceptual hash of image."""
        try:
            import numpy as np
            from PIL import Image
        except ImportError:
            raise ImportError(
                "NumPy is required for hash comparison: pip install numpy"
            )

        # Resize to 32x32
        img = img.convert("L").resize((32, 32), Image.LANCZOS)

        # Convert to numpy array
        arr = np.array(img, dtype=np.float64)

        # Calculate DCT (simplified using numpy)
        dct = self._dct2(arr)

        # Use top-left 8x8
        dct_low = dct[:8, :8]

        # Calculate median (excluding DC component)
        median = np.median(dct_low[1:].flatten())

        # Generate hash
        hash_value = 0
        for i in range(8):
            for j in range(8):
                if dct_low[i, j] > median:
                    hash_value |= 1 << (i * 8 + j)

        return hash_value

    def _dct2(self, arr: "np.ndarray") -> "np.ndarray":
        """2D Discrete Cosine Transform (simplified)."""
        import numpy as np

        # Simple DCT approximation
        N = arr.shape[0]
        result = np.zeros_like(arr)

        for u in range(N):
            for v in range(N):
                sum_val = 0.0
                for x in range(N):
                    for y in range(N):
                        sum_val += arr[x, y] * np.cos(
                            np.pi * u * (2 * x + 1) / (2 * N)
                        ) * np.cos(np.pi * v * (2 * y + 1) / (2 * N))
                result[u, v] = sum_val

        return result

    def _compare_histogram(
        self,
        img1: "Image.Image",
        img2: "Image.Image",
        threshold: float,
    ) -> ComparisonResult:
        """Histogram comparison."""
        from PIL import Image

        # Ensure same size
        if img1.size != img2.size:
            img2 = img2.resize(img1.size, Image.LANCZOS)

        # Get histograms
        hist1 = img1.convert("RGB").histogram()
        hist2 = img2.convert("RGB").histogram()

        # Normalize
        sum1 = sum(hist1) or 1
        sum2 = sum(hist2) or 1
        hist1 = [h / sum1 for h in hist1]
        hist2 = [h / sum2 for h in hist2]

        # Calculate correlation
        mean1 = sum(hist1) / len(hist1)
        mean2 = sum(hist2) / len(hist2)

        numerator = sum((h1 - mean1) * (h2 - mean2) for h1, h2 in zip(hist1, hist2))
        denom1 = sum((h - mean1) ** 2 for h in hist1) ** 0.5
        denom2 = sum((h - mean2) ** 2 for h in hist2) ** 0.5

        if denom1 * denom2 == 0:
            correlation = 1.0 if hist1 == hist2 else 0.0
        else:
            correlation = numerator / (denom1 * denom2)

        # Convert to similarity (correlation ranges from -1 to 1)
        similarity = (correlation + 1) / 2
        difference = 1.0 - similarity
        match = difference <= threshold

        return ComparisonResult(
            match=match,
            similarity=similarity,
            difference=difference,
            method=ComparisonMethod.HISTOGRAM,
            threshold=threshold,
        )

    def _generate_diff_image(
        self,
        img1: "Image.Image",
        img2: "Image.Image",
        diff: "Image.Image",
    ) -> bytes:
        """Generate difference visualization."""
        from PIL import Image, ImageDraw

        # Create output image (side by side comparison)
        width = img1.width * 3
        height = img1.height
        output = Image.new("RGBA", (width, height))

        # Paste original images
        output.paste(img1, (0, 0))
        output.paste(img2, (img1.width, 0))

        # Create highlighted diff
        diff_highlight = Image.new("RGBA", img1.size, (255, 255, 255, 255))
        diff_data = diff.getdata()
        img1_data = img1.getdata()

        pixels = []
        for i, (diff_pixel, orig_pixel) in enumerate(zip(diff_data, img1_data)):
            if any(c > 0 for c in diff_pixel[:3]):
                # Highlight differences in red
                pixels.append((255, 0, 0, 255))
            else:
                # Keep original with reduced opacity
                pixels.append(
                    (orig_pixel[0], orig_pixel[1], orig_pixel[2], 128)
                )

        diff_highlight.putdata(pixels)
        output.paste(diff_highlight, (img1.width * 2, 0))

        # Add labels
        draw = ImageDraw.Draw(output)
        draw.text((10, 10), "Original", fill=(255, 255, 255))
        draw.text((img1.width + 10, 10), "Compared", fill=(255, 255, 255))
        draw.text((img1.width * 2 + 10, 10), "Diff", fill=(255, 255, 255))

        # Convert to bytes
        buffer = io.BytesIO()
        output.save(buffer, format="PNG")
        return buffer.getvalue()

    def _generate_ssim_diff(
        self,
        img1: "Image.Image",
        img2: "Image.Image",
        arr1: "np.ndarray",
        arr2: "np.ndarray",
    ) -> bytes:
        """Generate SSIM difference visualization."""
        import numpy as np
        from PIL import Image

        # Calculate local SSIM map
        window_size = 11
        diff_arr = np.abs(arr1 - arr2)
        diff_normalized = (diff_arr / diff_arr.max() * 255).astype(np.uint8)

        # Create heatmap
        diff_img = Image.fromarray(diff_normalized)
        diff_colored = Image.merge(
            "RGB",
            (
                diff_img,
                Image.new("L", diff_img.size, 0),
                Image.new("L", diff_img.size, 0),
            ),
        )

        # Combine with original
        combined = Image.blend(
            img1.convert("RGB"),
            diff_colored,
            alpha=0.5,
        )

        buffer = io.BytesIO()
        combined.save(buffer, format="PNG")
        return buffer.getvalue()


def compare_images(
    image1: Union[bytes, str, Path],
    image2: Union[bytes, str, Path],
    *,
    threshold: float = 0.01,
    method: ComparisonMethod = ComparisonMethod.PIXEL,
) -> ComparisonResult:
    """Convenience function to compare two images.

    Args:
        image1: First image.
        image2: Second image.
        threshold: Difference threshold.
        method: Comparison method.

    Returns:
        Comparison result.

    Example:
        result = compare_images("screenshot1.png", "screenshot2.png")
        if result.match:
            print("Images match!")
        else:
            print(f"Images differ by {result.diff_percent:.2f}%")
    """
    comparator = ImageComparator(threshold=threshold, method=method)
    return comparator.compare(image1, image2)


def images_are_equal(
    image1: Union[bytes, str, Path],
    image2: Union[bytes, str, Path],
    *,
    threshold: float = 0.0,
) -> bool:
    """Check if two images are equal.

    Args:
        image1: First image.
        image2: Second image.
        threshold: Allowed difference threshold.

    Returns:
        True if images match within threshold.

    Example:
        if images_are_equal("expected.png", "actual.png"):
            print("Visual regression test passed!")
    """
    result = compare_images(image1, image2, threshold=threshold)
    return result.match


def calculate_image_hash(
    image: Union[bytes, str, Path],
    algorithm: str = "sha256",
) -> str:
    """Calculate cryptographic hash of image data.

    Args:
        image: Image to hash.
        algorithm: Hash algorithm (md5, sha1, sha256).

    Returns:
        Hex digest of image hash.
    """
    if isinstance(image, (str, Path)):
        with open(image, "rb") as f:
            data = f.read()
    else:
        data = image

    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()


__all__ = [
    "ComparisonMethod",
    "ComparisonResult",
    "ImageComparator",
    "compare_images",
    "images_are_equal",
    "calculate_image_hash",
]
