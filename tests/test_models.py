"""
Tests for kuromi-browser models - ProxyConfig and Fingerprint.

Run with: pytest tests/test_models.py -v
"""

import pytest
from kuromi_browser.models import (
    ProxyConfig,
    ProxyType,
    Fingerprint,
    NavigatorProperties,
    ScreenProperties,
    WebGLProperties,
    AudioProperties,
    WebRTCProperties,
    WebGPUProperties,
    DomRectProperties,
    FontProperties,
    UserAgentDataProperties,
    BatteryProperties,
    MultimediaDevicesProperties,
    BrowserConfig,
)


class TestProxyConfig:
    """Test ProxyConfig proxy parsing and conversion."""

    def test_from_url_http(self):
        """Test parsing HTTP proxy URL."""
        proxy = ProxyConfig.from_url("http://proxy.example.com:8080")

        assert proxy.proxy_type == ProxyType.HTTP
        assert proxy.server == "http://proxy.example.com:8080"
        assert proxy.username is None
        assert proxy.password is None

    def test_from_url_http_with_auth(self):
        """Test parsing HTTP proxy URL with authentication."""
        proxy = ProxyConfig.from_url("http://user:pass123@proxy.example.com:8080")

        assert proxy.proxy_type == ProxyType.HTTP
        assert proxy.server == "http://proxy.example.com:8080"
        assert proxy.username == "user"
        assert proxy.password == "pass123"

    def test_from_url_https(self):
        """Test parsing HTTPS proxy URL."""
        proxy = ProxyConfig.from_url("https://secure-proxy.example.com:443")

        assert proxy.proxy_type == ProxyType.HTTPS
        assert proxy.server == "https://secure-proxy.example.com:443"

    def test_from_url_socks5(self):
        """Test parsing SOCKS5 proxy URL."""
        proxy = ProxyConfig.from_url("socks5://127.0.0.1:1080")

        assert proxy.proxy_type == ProxyType.SOCKS5
        assert proxy.server == "socks5://127.0.0.1:1080"

    def test_from_url_socks5_with_auth(self):
        """Test parsing SOCKS5 proxy with authentication."""
        proxy = ProxyConfig.from_url("socks5://admin:secret@socks.example.com:1080")

        assert proxy.proxy_type == ProxyType.SOCKS5
        assert proxy.server == "socks5://socks.example.com:1080"
        assert proxy.username == "admin"
        assert proxy.password == "secret"

    def test_from_url_socks5h(self):
        """Test parsing SOCKS5H (DNS through proxy) URL."""
        proxy = ProxyConfig.from_url("socks5h://127.0.0.1:1080")

        assert proxy.proxy_type == ProxyType.SOCKS5
        assert "127.0.0.1:1080" in proxy.server

    def test_from_url_socks4(self):
        """Test parsing SOCKS4 proxy URL."""
        proxy = ProxyConfig.from_url("socks4://localhost:1080")

        assert proxy.proxy_type == ProxyType.SOCKS4

    def test_to_url_without_auth(self):
        """Test converting ProxyConfig to URL without auth."""
        proxy = ProxyConfig(
            server="http://proxy.example.com:8080",
            username="user",
            password="pass",
            proxy_type=ProxyType.HTTP,
        )

        url = proxy.to_url(include_auth=False)
        assert "user" not in url
        assert "pass" not in url
        assert "proxy.example.com:8080" in url

    def test_to_url_with_auth(self):
        """Test converting ProxyConfig to URL with auth."""
        proxy = ProxyConfig(
            server="http://proxy.example.com:8080",
            username="user",
            password="pass",
            proxy_type=ProxyType.HTTP,
        )

        url = proxy.to_url(include_auth=True)
        assert "user:pass@" in url
        assert "proxy.example.com:8080" in url

    def test_to_curl_cffi_proxy(self):
        """Test converting to curl_cffi proxy format."""
        proxy = ProxyConfig.from_url("socks5://user:pass@127.0.0.1:1080")

        curl_proxy = proxy.to_curl_cffi_proxy()
        assert "http" in curl_proxy
        assert "https" in curl_proxy
        assert "socks5://" in curl_proxy["http"]
        assert "user:pass@" in curl_proxy["http"]

    def test_to_httpx_proxy(self):
        """Test converting to httpx proxy format."""
        proxy = ProxyConfig.from_url("http://user:pass@proxy.com:8080")

        httpx_proxy = proxy.to_httpx_proxy()
        assert "http://" in httpx_proxy
        assert "user:pass@" in httpx_proxy

    def test_to_chromium_arg_http(self):
        """Test converting to Chromium argument for HTTP proxy."""
        proxy = ProxyConfig.from_url("http://proxy.com:8080")

        arg = proxy.to_chromium_arg()
        assert "proxy.com" in arg

    def test_to_chromium_arg_socks5(self):
        """Test converting to Chromium argument for SOCKS5 proxy."""
        proxy = ProxyConfig.from_url("socks5://127.0.0.1:1080")

        arg = proxy.to_chromium_arg()
        assert "socks5://" in arg
        assert "127.0.0.1:1080" in arg


class TestFingerprint:
    """Test Fingerprint model and its components."""

    def test_default_fingerprint(self):
        """Test creating fingerprint with defaults."""
        fp = Fingerprint()

        assert "Mozilla" in fp.user_agent
        assert fp.navigator.platform == "Linux x86_64"
        assert fp.screen.width == 1920
        assert fp.screen.height == 1080
        assert fp.timezone == "America/New_York"

    def test_fingerprint_properties(self):
        """Test fingerprint shortcut properties."""
        fp = Fingerprint()

        assert fp.platform == fp.navigator.platform
        assert fp.vendor == fp.navigator.vendor
        assert fp.screen_width == fp.screen.width
        assert fp.screen_height == fp.screen.height
        assert fp.webgl_vendor == fp.webgl.vendor
        assert fp.webgl_renderer == fp.webgl.renderer

    def test_navigator_properties(self):
        """Test NavigatorProperties model."""
        nav = NavigatorProperties(
            platform="Windows NT 10.0; Win64; x64",
            hardware_concurrency=16,
            device_memory=16.0,
            language="vi-VN",
            languages=["vi-VN", "en-US"],
        )

        assert nav.platform == "Windows NT 10.0; Win64; x64"
        assert nav.hardware_concurrency == 16
        assert nav.device_memory == 16.0
        assert "vi-VN" in nav.languages

    def test_screen_properties(self):
        """Test ScreenProperties model."""
        screen = ScreenProperties(
            width=2560,
            height=1440,
            device_pixel_ratio=2.0,
        )

        assert screen.width == 2560
        assert screen.height == 1440
        assert screen.device_pixel_ratio == 2.0
        assert screen.color_depth == 24

    def test_webgl_properties(self):
        """Test WebGLProperties model."""
        webgl = WebGLProperties(
            vendor="Google Inc. (AMD)",
            renderer="ANGLE (AMD, AMD Radeon RX 580 Direct3D11)",
        )

        assert "AMD" in webgl.vendor
        assert "Radeon" in webgl.renderer

    def test_webrtc_properties(self):
        """Test WebRTCProperties model."""
        webrtc = WebRTCProperties(
            enabled=False,
            mode="disable",
        )

        assert webrtc.enabled is False
        assert webrtc.mode == "disable"

        webrtc_fake = WebRTCProperties(
            enabled=True,
            mode="fake",
            public_ip="203.0.113.1",
            local_ip="192.168.1.100",
        )

        assert webrtc_fake.enabled is True
        assert webrtc_fake.public_ip == "203.0.113.1"

    def test_webgpu_properties(self):
        """Test WebGPUProperties model."""
        webgpu = WebGPUProperties(
            noise_enabled=True,
            noise_seed=12345,
        )

        assert webgpu.noise_enabled is True
        assert webgpu.noise_seed == 12345

    def test_domrect_properties(self):
        """Test DomRectProperties model."""
        domrect = DomRectProperties(
            noise_enabled=True,
            noise_level=1e-7,
        )

        assert domrect.noise_enabled is True
        assert domrect.noise_level == 1e-7

    def test_font_properties(self):
        """Test FontProperties model."""
        font = FontProperties(
            noise_enabled=True,
            offset_noise_range=(-2, 2),
        )

        assert font.noise_enabled is True
        assert font.offset_noise_range == (-2, 2)

    def test_user_agent_data_properties(self):
        """Test UserAgentDataProperties (Client Hints)."""
        uad = UserAgentDataProperties(
            mobile=False,
            platform="Windows",
            architecture="x86",
            bitness="64",
        )

        assert uad.mobile is False
        assert uad.platform == "Windows"
        assert uad.architecture == "x86"
        assert len(uad.brands) > 0

    def test_battery_properties(self):
        """Test BatteryProperties model."""
        battery = BatteryProperties(
            charging=False,
            level=0.75,
            discharging_time=3600.0,
        )

        assert battery.charging is False
        assert battery.level == 0.75
        assert battery.discharging_time == 3600.0

    def test_multimedia_devices(self):
        """Test MultimediaDevicesProperties model."""
        devices = MultimediaDevicesProperties(
            webcams=2,
            microphones=1,
            speakers=2,
        )

        assert devices.webcams == 2
        assert devices.microphones == 1
        assert devices.speakers == 2

    def test_custom_fingerprint(self):
        """Test creating custom fingerprint."""
        fp = Fingerprint(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            navigator=NavigatorProperties(
                platform="Win32",
                hardware_concurrency=8,
            ),
            screen=ScreenProperties(width=1920, height=1080),
            timezone="Asia/Ho_Chi_Minh",
            locale="vi-VN",
            global_seed=42,
        )

        assert "Windows" in fp.user_agent
        assert fp.navigator.platform == "Win32"
        assert fp.timezone == "Asia/Ho_Chi_Minh"
        assert fp.locale == "vi-VN"
        assert fp.global_seed == 42

    def test_fingerprint_fonts(self):
        """Test fingerprint fonts list."""
        fp = Fingerprint(
            fonts=["Arial", "Times New Roman", "Courier New"]
        )

        assert "Arial" in fp.fonts
        assert len(fp.fonts) == 3

    def test_fingerprint_plugins(self):
        """Test fingerprint plugins."""
        fp = Fingerprint()

        assert len(fp.plugins) > 0
        assert any("PDF" in p.get("name", "") for p in fp.plugins)

    def test_fingerprint_codecs(self):
        """Test video/audio codec support."""
        fp = Fingerprint()

        assert "h264" in fp.video_codecs
        assert "mp3" in fp.audio_codecs
        assert fp.video_codecs["h264"] == "probably"


class TestBrowserConfig:
    """Test BrowserConfig model."""

    def test_default_config(self):
        """Test default browser config."""
        config = BrowserConfig()

        assert config.headless is False
        assert config.stealth is True
        assert config.proxy is None
        assert config.timeout == 30000

    def test_config_with_proxy_string(self):
        """Test config with proxy as string."""
        config = BrowserConfig(
            proxy="http://proxy.example.com:8080"
        )

        args = config.get_launch_args()
        assert any("proxy-server" in arg for arg in args)

    def test_config_with_proxy_config(self):
        """Test config with ProxyConfig object."""
        proxy = ProxyConfig.from_url("socks5://127.0.0.1:1080")
        config = BrowserConfig(proxy=proxy)

        args = config.get_launch_args()
        assert any("proxy-server" in arg for arg in args)

    def test_config_headless_args(self):
        """Test headless config adds correct args."""
        config = BrowserConfig(headless=True)

        args = config.get_launch_args()
        assert any("headless" in arg for arg in args)

    def test_config_custom_args(self):
        """Test custom browser args."""
        config = BrowserConfig(
            args=["--disable-gpu", "--no-sandbox"]
        )

        args = config.get_launch_args()
        assert "--disable-gpu" in args
        assert "--no-sandbox" in args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
