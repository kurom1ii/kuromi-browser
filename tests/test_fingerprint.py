"""
Tests for kuromi-browser stealth fingerprint generation.

Run with: pytest tests/test_fingerprint.py -v
"""

import pytest
from kuromi_browser.stealth.fingerprint import FingerprintGenerator
from kuromi_browser.models import Fingerprint


class TestFingerprintGenerator:
    """Test FingerprintGenerator class."""

    def test_generate_default(self):
        """Test generating fingerprint with defaults."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        assert isinstance(fp, Fingerprint)
        assert fp.user_agent is not None
        assert fp.navigator.platform is not None
        assert fp.screen.width > 0
        assert fp.screen.height > 0

    def test_generate_with_seed(self):
        """Test generating reproducible fingerprint with seed."""
        gen = FingerprintGenerator()

        fp1 = gen.generate(seed=12345)
        fp2 = gen.generate(seed=12345)

        # Same seed should produce same fingerprint
        assert fp1.user_agent == fp2.user_agent
        assert fp1.navigator.platform == fp2.navigator.platform
        assert fp1.screen.width == fp2.screen.width

    def test_generate_different_seeds(self):
        """Test different seeds produce different fingerprints."""
        gen = FingerprintGenerator()

        fp1 = gen.generate(seed=11111)
        fp2 = gen.generate(seed=22222)

        # Different seeds should (very likely) produce different fingerprints
        assert fp1.global_seed != fp2.global_seed

    def test_generate_for_os_windows(self):
        """Test generating fingerprint for Windows."""
        gen = FingerprintGenerator()
        fp = gen.generate(os="windows")

        # Windows fingerprint should have Windows-like properties
        assert any(x in fp.user_agent.lower() for x in ["windows", "win64", "win32"])

    def test_generate_for_os_macos(self):
        """Test generating fingerprint for macOS."""
        gen = FingerprintGenerator()
        fp = gen.generate(os="macos")

        assert any(x in fp.user_agent.lower() for x in ["mac", "macintosh", "darwin"])

    def test_generate_for_os_linux(self):
        """Test generating fingerprint for Linux."""
        gen = FingerprintGenerator()
        fp = gen.generate(os="linux")

        assert any(x in fp.user_agent.lower() for x in ["linux", "x11"])

    def test_fingerprint_consistency(self):
        """Test fingerprint internal consistency."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        # Screen avail should be <= screen size
        assert fp.screen.avail_width <= fp.screen.width
        assert fp.screen.avail_height <= fp.screen.height

        # Hardware concurrency should be reasonable
        assert 1 <= fp.navigator.hardware_concurrency <= 64

        # Device memory should be reasonable
        if fp.navigator.device_memory:
            assert 0.25 <= fp.navigator.device_memory <= 512

    def test_generate_with_screen_constraints(self):
        """Test generating with screen size constraints."""
        gen = FingerprintGenerator()
        fp = gen.generate(
            min_width=1920,
            min_height=1080,
            max_width=3840,
            max_height=2160,
        )

        assert 1920 <= fp.screen.width <= 3840
        assert 1080 <= fp.screen.height <= 2160

    def test_validate_fingerprint(self):
        """Test fingerprint validation."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        # Validation should pass for generated fingerprints
        issues = gen.validate(fp)

        # May have some minor issues, but should not have critical ones
        critical = [i for i in issues if "critical" in i.lower()]
        assert len(critical) == 0

    def test_fingerprint_noise_properties(self):
        """Test noise properties are set."""
        gen = FingerprintGenerator()
        fp = gen.generate(seed=42)

        # Noise-based properties should be configured
        assert fp.webgpu.noise_enabled is True
        assert fp.dom_rect.noise_enabled is True
        assert fp.font_fp.noise_enabled is True

        # Seeds should be set
        assert fp.global_seed is not None

    def test_fingerprint_webrtc_default_disabled(self):
        """Test WebRTC is disabled by default for privacy."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        # WebRTC should be disabled by default
        assert fp.webrtc.enabled is False
        assert fp.webrtc.mode == "disable"

    def test_fingerprint_user_agent_data(self):
        """Test Client Hints (userAgentData) generation."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        # Should have brands
        assert len(fp.user_agent_data.brands) > 0

        # Platform should match fingerprint
        uad_platform = fp.user_agent_data.platform.lower()
        nav_platform = fp.navigator.platform.lower()

        # They should be related
        # (Windows -> Windows, Mac -> macOS, Linux -> Linux)
        if "win" in nav_platform:
            assert "win" in uad_platform.lower()
        elif "mac" in nav_platform:
            assert "mac" in uad_platform.lower()

    def test_fingerprint_codecs(self):
        """Test codec support is set."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        # Should have video codecs
        assert "h264" in fp.video_codecs

        # Should have audio codecs
        assert "mp3" in fp.audio_codecs

    def test_fingerprint_battery(self):
        """Test battery properties."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        # Battery level should be valid
        assert 0.0 <= fp.battery.level <= 1.0

    def test_fingerprint_multimedia_devices(self):
        """Test multimedia devices properties."""
        gen = FingerprintGenerator()
        fp = gen.generate()

        # Should have reasonable device counts
        assert 0 <= fp.multimedia_devices.webcams <= 5
        assert 0 <= fp.multimedia_devices.microphones <= 5
        assert 0 <= fp.multimedia_devices.speakers <= 5


class TestFromBrowserforge:
    """Test from_browserforge integration."""

    def test_from_browserforge_basic(self):
        """Test creating fingerprint from browserforge."""
        gen = FingerprintGenerator()

        try:
            fp = gen.from_browserforge()
            assert isinstance(fp, Fingerprint)
            assert fp.user_agent is not None
        except ImportError:
            # browserforge not installed, skip
            pytest.skip("browserforge not installed")

    def test_from_browserforge_with_browser(self):
        """Test from_browserforge with browser type."""
        gen = FingerprintGenerator()

        try:
            fp = gen.from_browserforge(browser="chrome")
            assert "Chrome" in fp.user_agent or "chrome" in fp.user_agent.lower()
        except ImportError:
            pytest.skip("browserforge not installed")

    def test_from_browserforge_with_os(self):
        """Test from_browserforge with OS."""
        gen = FingerprintGenerator()

        try:
            fp = gen.from_browserforge(os="windows")
            assert any(
                x in fp.user_agent.lower()
                for x in ["windows", "win64", "win32"]
            )
        except ImportError:
            pytest.skip("browserforge not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
