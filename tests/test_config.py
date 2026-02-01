"""
Tests for kuromi-browser configuration system.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from kuromi_browser.config import (
    BrowserOptions,
    BrowserType,
    ColorScheme,
    ConfigLoader,
    ConfigurationError,
    EnvConfigLoader,
    KuromiConfig,
    PageMode,
    PageOptions,
    ProxyOptions,
    ProxyType,
    RetryOptions,
    SessionOptions,
    ViewportOptions,
    WaitUntil,
    find_config_file,
    get_env,
    get_env_bool,
    get_env_int,
    get_env_key,
    load_config,
    load_config_with_profile,
    load_file,
    load_profile,
    merge_configs,
    save_config,
)


class TestProxyOptions:
    """Tests for ProxyOptions class."""

    def test_from_url_http(self):
        """Test parsing HTTP proxy URL."""
        proxy = ProxyOptions.from_url("http://proxy.example.com:8080")
        assert proxy.server == "http://proxy.example.com:8080"
        assert proxy.proxy_type == ProxyType.HTTP
        assert proxy.username is None

    def test_from_url_with_auth(self):
        """Test parsing proxy URL with authentication."""
        proxy = ProxyOptions.from_url("http://user:pass@proxy.example.com:8080")
        assert proxy.server == "http://proxy.example.com:8080"
        assert proxy.username == "user"
        assert proxy.password == "pass"

    def test_from_url_socks5(self):
        """Test parsing SOCKS5 proxy URL."""
        proxy = ProxyOptions.from_url("socks5://proxy.example.com:1080")
        assert proxy.proxy_type == ProxyType.SOCKS5

    def test_to_url(self):
        """Test converting proxy to URL format."""
        proxy = ProxyOptions(
            server="http://proxy.example.com:8080",
            username="user",
            password="pass",
        )
        url = proxy.to_url(include_auth=True)
        assert "user:pass@" in url

        url_no_auth = proxy.to_url(include_auth=False)
        assert "user" not in url_no_auth


class TestViewportOptions:
    """Tests for ViewportOptions class."""

    def test_default_values(self):
        """Test default viewport values."""
        viewport = ViewportOptions()
        assert viewport.width == 1920
        assert viewport.height == 1080

    def test_custom_values(self):
        """Test custom viewport values."""
        viewport = ViewportOptions(width=1280, height=720)
        assert viewport.width == 1280
        assert viewport.height == 720

    def test_validation(self):
        """Test viewport validation."""
        with pytest.raises(ValueError):
            ViewportOptions(width=100)  # Too small


class TestBrowserOptions:
    """Tests for BrowserOptions class."""

    def test_default_values(self):
        """Test default browser options."""
        options = BrowserOptions()
        assert options.browser_type == BrowserType.CHROMIUM
        assert options.headless is False
        assert options.stealth is True
        assert options.timeout == 30000

    def test_proxy_string(self):
        """Test proxy as string."""
        options = BrowserOptions(proxy="http://proxy:8080")
        assert options.proxy == "http://proxy:8080"
        proxy_opts = options.get_proxy_options()
        assert proxy_opts is not None
        assert proxy_opts.server == "http://proxy:8080"

    def test_proxy_options(self):
        """Test proxy as ProxyOptions."""
        proxy = ProxyOptions(server="http://proxy:8080")
        options = BrowserOptions(proxy=proxy)
        assert options.get_proxy_options() == proxy

    def test_get_launch_args(self):
        """Test getting launch arguments."""
        options = BrowserOptions(
            headless=True,
            proxy="http://proxy:8080",
        )
        args = options.get_launch_args()
        assert "--headless=new" in args
        assert "--proxy-server=http://proxy:8080" in args

    def test_merge(self):
        """Test merging browser options."""
        base = BrowserOptions(headless=False, timeout=30000)
        override = BrowserOptions(headless=True, devtools=True)
        merged = base.merge(override)
        assert merged.headless is True
        assert merged.devtools is True
        assert merged.timeout == 30000


class TestSessionOptions:
    """Tests for SessionOptions class."""

    def test_default_values(self):
        """Test default session options."""
        options = SessionOptions()
        assert options.timeout == 30.0
        assert options.verify_ssl is True
        assert options.http2 is True

    def test_retry_options(self):
        """Test retry configuration."""
        options = SessionOptions(
            retry=RetryOptions(count=5, backoff=1.0)
        )
        assert options.retry.count == 5
        assert options.retry.backoff == 1.0

    def test_get_proxy_dict(self):
        """Test getting proxy as curl_cffi format."""
        options = SessionOptions(proxy="http://proxy:8080")
        proxy_dict = options.get_proxy_dict()
        assert proxy_dict["http"] == "http://proxy:8080"
        assert proxy_dict["https"] == "http://proxy:8080"

    def test_merge_headers(self):
        """Test merging headers."""
        base = SessionOptions(headers={"Accept": "text/html"})
        override = SessionOptions(headers={"X-Custom": "value"})
        merged = base.merge(override)
        assert "Accept" in merged.headers
        assert "X-Custom" in merged.headers


class TestPageOptions:
    """Tests for PageOptions class."""

    def test_default_values(self):
        """Test default page options."""
        options = PageOptions()
        assert options.mode == PageMode.BROWSER
        assert options.wait_until == WaitUntil.LOAD
        assert options.java_script_enabled is True

    def test_mobile_mode(self):
        """Test mobile configuration."""
        options = PageOptions(
            is_mobile=True,
            has_touch=True,
            device_scale_factor=3.0,
        )
        assert options.is_mobile is True
        assert options.has_touch is True
        assert options.device_scale_factor == 3.0


class TestKuromiConfig:
    """Tests for KuromiConfig class."""

    def test_default_values(self):
        """Test default configuration."""
        config = KuromiConfig()
        assert config.browser.headless is False
        assert config.session.timeout == 30.0
        assert config.page.mode == PageMode.BROWSER

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "browser": {"headless": True},
            "session": {"timeout": 60.0},
        }
        config = KuromiConfig.from_dict(data)
        assert config.browser.headless is True
        assert config.session.timeout == 60.0

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = KuromiConfig(
            browser=BrowserOptions(headless=True),
        )
        data = config.to_dict()
        assert data["browser"]["headless"] is True

    def test_merge(self):
        """Test merging configurations."""
        base = KuromiConfig(
            browser=BrowserOptions(headless=False, timeout=30000),
        )
        override = KuromiConfig(
            browser=BrowserOptions(headless=True),
        )
        merged = base.merge(override)
        assert merged.browser.headless is True
        assert merged.browser.timeout == 30000


class TestEnvironmentVariables:
    """Tests for environment variable support."""

    def test_get_env_key(self):
        """Test converting config key to env var name."""
        assert get_env_key("browser.headless") == "KUROMI_BROWSER_HEADLESS"
        assert get_env_key("session.timeout") == "KUROMI_SESSION_TIMEOUT"

    def test_get_env_bool(self):
        """Test getting boolean from environment."""
        os.environ["KUROMI_TEST_BOOL"] = "true"
        try:
            assert get_env_bool("test.bool") is True
        finally:
            del os.environ["KUROMI_TEST_BOOL"]

    def test_get_env_int(self):
        """Test getting integer from environment."""
        os.environ["KUROMI_TEST_INT"] = "42"
        try:
            assert get_env_int("test.int") == 42
        finally:
            del os.environ["KUROMI_TEST_INT"]

    def test_get_env_default(self):
        """Test environment variable default value."""
        result = get_env("nonexistent.key", default="default")
        assert result == "default"

    def test_env_config_loader(self):
        """Test EnvConfigLoader class."""
        os.environ["KUROMI_BROWSER_HEADLESS"] = "true"
        os.environ["KUROMI_BROWSER_TIMEOUT"] = "60000"
        try:
            loader = EnvConfigLoader()
            section = loader.load_section("browser")
            assert "headless" in section
            assert "timeout" in section
        finally:
            del os.environ["KUROMI_BROWSER_HEADLESS"]
            del os.environ["KUROMI_BROWSER_TIMEOUT"]


class TestConfigLoader:
    """Tests for configuration file loading."""

    def test_load_json(self):
        """Test loading JSON configuration."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"browser": {"headless": True}}, f)
            f.flush()

            try:
                data = load_file(f.name)
                assert data["browser"]["headless"] is True
            finally:
                os.unlink(f.name)

    def test_load_config(self):
        """Test load_config function."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"browser": {"headless": True}}, f)
            f.flush()

            try:
                config = load_config(f.name)
                assert config.browser.headless is True
            finally:
                os.unlink(f.name)

    def test_load_with_overrides(self):
        """Test loading with programmatic overrides."""
        config = load_config(
            overrides={"browser": {"headless": True, "devtools": True}}
        )
        assert config.browser.headless is True
        assert config.browser.devtools is True

    def test_merge_configs(self):
        """Test merging multiple configurations."""
        config1 = {"browser": {"headless": False}}
        config2 = {"browser": {"headless": True, "devtools": True}}
        merged = merge_configs(config1, config2)
        assert merged["browser"]["headless"] is True
        assert merged["browser"]["devtools"] is True


class TestProfiles:
    """Tests for configuration profiles."""

    def test_load_stealth_profile(self):
        """Test loading stealth profile."""
        profile = load_profile("stealth")
        assert profile["browser"]["stealth"] is True
        assert profile["browser"]["headless"] is True

    def test_load_debug_profile(self):
        """Test loading debug profile."""
        profile = load_profile("debug")
        assert profile["browser"]["devtools"] is True
        assert profile["browser"]["slow_mo"] == 100

    def test_load_mobile_profile(self):
        """Test loading mobile profile."""
        profile = load_profile("mobile")
        assert profile["page"]["is_mobile"] is True
        assert profile["page"]["has_touch"] is True

    def test_unknown_profile(self):
        """Test loading unknown profile."""
        with pytest.raises(ConfigurationError):
            load_profile("nonexistent")

    def test_load_config_with_profile(self):
        """Test load_config_with_profile function."""
        config = load_config_with_profile("stealth")
        assert config.browser.stealth is True
        assert config.browser.headless is True


class TestSaveConfig:
    """Tests for saving configuration."""

    def test_save_json(self):
        """Test saving configuration as JSON."""
        config = KuromiConfig(
            browser=BrowserOptions(headless=True),
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.close()
            try:
                save_config(config, f.name, format="json")
                loaded = load_file(f.name)
                assert loaded["browser"]["headless"] is True
            finally:
                os.unlink(f.name)
