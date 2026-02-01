"""
CDP patches for hiding browser automation indicators.

These patches are injected before any page scripts run to modify
JavaScript APIs and hide automation artifacts.
"""

from typing import Any, Optional

from kuromi_browser.models import Fingerprint


# Hide navigator.webdriver property
WEBDRIVER_PATCH = """
(() => {
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });

    // Also delete from prototype
    delete Object.getPrototypeOf(navigator).webdriver;
})();
"""

# Emulate Chrome browser environment
CHROME_PATCHES = """
(() => {
    // Chrome runtime
    if (!window.chrome) {
        window.chrome = {};
    }

    window.chrome.runtime = {
        OnInstalledReason: {
            CHROME_UPDATE: 'chrome_update',
            INSTALL: 'install',
            SHARED_MODULE_UPDATE: 'shared_module_update',
            UPDATE: 'update'
        },
        OnRestartRequiredReason: {
            APP_UPDATE: 'app_update',
            OS_UPDATE: 'os_update',
            PERIODIC: 'periodic'
        },
        PlatformArch: {
            ARM: 'arm',
            ARM64: 'arm64',
            MIPS: 'mips',
            MIPS64: 'mips64',
            X86_32: 'x86-32',
            X86_64: 'x86-64'
        },
        PlatformNaclArch: {
            ARM: 'arm',
            MIPS: 'mips',
            MIPS64: 'mips64',
            X86_32: 'x86-32',
            X86_64: 'x86-64'
        },
        PlatformOs: {
            ANDROID: 'android',
            CROS: 'cros',
            LINUX: 'linux',
            MAC: 'mac',
            OPENBSD: 'openbsd',
            WIN: 'win'
        },
        RequestUpdateCheckStatus: {
            NO_UPDATE: 'no_update',
            THROTTLED: 'throttled',
            UPDATE_AVAILABLE: 'update_available'
        },
        connect: function() { return { disconnect: function() {} }; },
        sendMessage: function() {}
    };

    // Chrome loadTimes (deprecated but still checked)
    window.chrome.loadTimes = function() {
        return {
            commitLoadTime: Date.now() / 1000,
            connectionInfo: 'h2',
            finishDocumentLoadTime: Date.now() / 1000,
            finishLoadTime: Date.now() / 1000,
            firstPaintAfterLoadTime: 0,
            firstPaintTime: Date.now() / 1000,
            navigationType: 'Other',
            npnNegotiatedProtocol: 'h2',
            requestTime: Date.now() / 1000 - 0.1,
            startLoadTime: Date.now() / 1000 - 0.1,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true
        };
    };

    // Chrome csi (deprecated but still checked)
    window.chrome.csi = function() {
        return {
            onloadT: Date.now(),
            pageT: Date.now() - performance.timing.navigationStart,
            startE: performance.timing.navigationStart,
            tran: 15
        };
    };

    // Chrome app
    window.chrome.app = {
        InstallState: {
            DISABLED: 'disabled',
            INSTALLED: 'installed',
            NOT_INSTALLED: 'not_installed'
        },
        RunningState: {
            CANNOT_RUN: 'cannot_run',
            READY_TO_RUN: 'ready_to_run',
            RUNNING: 'running'
        },
        getDetails: function() { return null; },
        getIsInstalled: function() { return false; },
        installState: function(callback) {
            if (callback) callback('not_installed');
            return 'not_installed';
        },
        isInstalled: false,
        runningState: function() { return 'cannot_run'; }
    };
})();
"""

# Fix permissions API inconsistency
PERMISSIONS_PATCH = """
(() => {
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => {
        if (parameters.name === 'notifications') {
            return Promise.resolve({
                state: Notification.permission,
                name: 'notifications',
                onchange: null
            });
        }
        return originalQuery.call(navigator.permissions, parameters);
    };
})();
"""

# Fix iframe contentWindow access detection
IFRAME_PATCH = """
(() => {
    try {
        if (window.frameElement) {
            Object.defineProperty(window, 'frameElement', {
                get: () => null
            });
        }
    } catch (e) {}
})();
"""

# Hide automation-related console output
CONSOLE_PATCH = """
(() => {
    const originalError = console.error;
    console.error = function(...args) {
        const message = args.join(' ');
        if (message.includes('Puppeteer') ||
            message.includes('automation') ||
            message.includes('controlled by')) {
            return;
        }
        return originalError.apply(console, args);
    };
})();
"""

# Plugin and mimeType patches
PLUGINS_PATCH = """
(() => {
    const pluginData = [
        {
            name: 'Chrome PDF Viewer',
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            mimeTypes: [{type: 'application/pdf', suffixes: 'pdf'}]
        },
        {
            name: 'Chromium PDF Viewer',
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            mimeTypes: [{type: 'application/pdf', suffixes: 'pdf'}]
        },
        {
            name: 'Microsoft Edge PDF Viewer',
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            mimeTypes: [{type: 'application/pdf', suffixes: 'pdf'}]
        },
        {
            name: 'PDF Viewer',
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            mimeTypes: [{type: 'application/pdf', suffixes: 'pdf'}]
        },
        {
            name: 'WebKit built-in PDF',
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            mimeTypes: [{type: 'application/pdf', suffixes: 'pdf'}]
        }
    ];

    const makeMimeType = (data) => {
        const mt = Object.create(MimeType.prototype);
        Object.defineProperties(mt, {
            type: { value: data.type, enumerable: true },
            suffixes: { value: data.suffixes, enumerable: true },
            description: { value: '', enumerable: true },
            enabledPlugin: { value: null, enumerable: true }
        });
        return mt;
    };

    const makePlugin = (data) => {
        const plugin = Object.create(Plugin.prototype);
        const mimeTypes = data.mimeTypes.map(makeMimeType);

        Object.defineProperties(plugin, {
            name: { value: data.name, enumerable: true },
            description: { value: data.description, enumerable: true },
            filename: { value: data.filename, enumerable: true },
            length: { value: mimeTypes.length, enumerable: true }
        });

        mimeTypes.forEach((mt, i) => {
            Object.defineProperty(plugin, i, { value: mt, enumerable: true });
            Object.defineProperty(plugin, mt.type, { value: mt, enumerable: false });
            Object.defineProperty(mt, 'enabledPlugin', { value: plugin });
        });

        plugin[Symbol.iterator] = function*() {
            yield* mimeTypes;
        };

        return plugin;
    };

    const plugins = pluginData.map(makePlugin);
    const mimeTypes = plugins.flatMap(p => Array.from(p));

    const pluginArray = Object.create(PluginArray.prototype);
    Object.defineProperty(pluginArray, 'length', { value: plugins.length, enumerable: true });
    plugins.forEach((p, i) => {
        Object.defineProperty(pluginArray, i, { value: p, enumerable: true });
        Object.defineProperty(pluginArray, p.name, { value: p, enumerable: false });
    });
    pluginArray[Symbol.iterator] = function*() { yield* plugins; };
    pluginArray.item = function(i) { return plugins[i] || null; };
    pluginArray.namedItem = function(name) { return plugins.find(p => p.name === name) || null; };
    pluginArray.refresh = function() {};

    const mimeTypeArray = Object.create(MimeTypeArray.prototype);
    Object.defineProperty(mimeTypeArray, 'length', { value: mimeTypes.length, enumerable: true });
    mimeTypes.forEach((mt, i) => {
        Object.defineProperty(mimeTypeArray, i, { value: mt, enumerable: true });
        Object.defineProperty(mimeTypeArray, mt.type, { value: mt, enumerable: false });
    });
    mimeTypeArray[Symbol.iterator] = function*() { yield* mimeTypes; };
    mimeTypeArray.item = function(i) { return mimeTypes[i] || null; };
    mimeTypeArray.namedItem = function(name) { return mimeTypes.find(m => m.type === name) || null; };

    Object.defineProperty(navigator, 'plugins', {
        get: () => pluginArray,
        configurable: true
    });

    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => mimeTypeArray,
        configurable: true
    });

    Object.defineProperty(navigator, 'pdfViewerEnabled', {
        get: () => true,
        configurable: true
    });
})();
"""

# Language consistency patches
LANGUAGES_PATCH = """
((languages) => {
    Object.defineProperty(navigator, 'languages', {
        get: () => Object.freeze([...languages]),
        configurable: true
    });

    Object.defineProperty(navigator, 'language', {
        get: () => languages[0],
        configurable: true
    });
})(['en-US', 'en']);
"""

# Hardware concurrency patch
HARDWARE_CONCURRENCY_PATCH = """
((value) => {
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => value,
        configurable: true
    });
})({concurrency});
"""

# Device memory patch
DEVICE_MEMORY_PATCH = """
((value) => {
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => value,
        configurable: true
    });
})({memory});
"""

# WebGL vendor/renderer patch
WEBGL_PATCH = """
((vendor, renderer) => {
    const getParameterProxyHandler = {
        apply: function(target, thisArg, args) {
            const param = args[0];
            const gl = thisArg;

            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) {
                return vendor;
            }
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) {
                return renderer;
            }

            return Reflect.apply(target, thisArg, args);
        }
    };

    const contexts = ['webgl', 'experimental-webgl', 'webgl2', 'experimental-webgl2'];
    const originalGetContext = HTMLCanvasElement.prototype.getContext;

    HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        const context = originalGetContext.apply(this, [type, ...args]);

        if (context && contexts.includes(type)) {
            const ext = context.getExtension('WEBGL_debug_renderer_info');
            if (ext) {
                context.getParameter = new Proxy(context.getParameter, getParameterProxyHandler);
            }
        }

        return context;
    };
})({vendor}, {renderer});
"""

# Canvas fingerprint noise
CANVAS_NOISE_PATCH = """
((seed) => {
    const random = (function() {
        let s = seed || Date.now();
        return function() {
            s = Math.sin(s) * 10000;
            return s - Math.floor(s);
        };
    })();

    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

    const addNoise = (canvas) => {
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const imageData = originalGetImageData.call(ctx, 0, 0, canvas.width, canvas.height);
        const data = imageData.data;

        for (let i = 0; i < data.length; i += 4) {
            // Add tiny noise to RGB channels
            const noise = Math.floor(random() * 3) - 1;
            data[i] = Math.max(0, Math.min(255, data[i] + noise));
            data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + noise));
            data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + noise));
        }

        ctx.putImageData(imageData, 0, 0);
    };

    HTMLCanvasElement.prototype.toDataURL = function(...args) {
        addNoise(this);
        return originalToDataURL.apply(this, args);
    };

    HTMLCanvasElement.prototype.toBlob = function(callback, ...args) {
        addNoise(this);
        return originalToBlob.call(this, callback, ...args);
    };

    CanvasRenderingContext2D.prototype.getImageData = function(...args) {
        addNoise(this.canvas);
        return originalGetImageData.apply(this, args);
    };
})({seed});
"""

# AudioContext fingerprint noise
AUDIO_NOISE_PATCH = """
((seed) => {
    const random = (function() {
        let s = seed || Date.now();
        return function() {
            s = Math.sin(s) * 10000;
            return s - Math.floor(s);
        };
    })();

    const originalGetFloatFrequencyData = AnalyserNode.prototype.getFloatFrequencyData;
    const originalGetByteFrequencyData = AnalyserNode.prototype.getByteFrequencyData;
    const originalGetChannelData = AudioBuffer.prototype.getChannelData;

    AnalyserNode.prototype.getFloatFrequencyData = function(array) {
        originalGetFloatFrequencyData.call(this, array);
        for (let i = 0; i < array.length; i++) {
            array[i] = array[i] + random() * 0.0001;
        }
    };

    AnalyserNode.prototype.getByteFrequencyData = function(array) {
        originalGetByteFrequencyData.call(this, array);
        for (let i = 0; i < array.length; i++) {
            array[i] = Math.min(255, Math.max(0, array[i] + Math.floor(random() * 2)));
        }
    };

    AudioBuffer.prototype.getChannelData = function(channel) {
        const array = originalGetChannelData.call(this, channel);
        for (let i = 0; i < array.length; i++) {
            array[i] = array[i] + (random() - 0.5) * 0.0001;
        }
        return array;
    };
})({seed});
"""

# Screen dimensions patch
SCREEN_PATCH = """
((width, height, availWidth, availHeight, colorDepth, pixelRatio) => {
    Object.defineProperty(screen, 'width', { get: () => width, configurable: true });
    Object.defineProperty(screen, 'height', { get: () => height, configurable: true });
    Object.defineProperty(screen, 'availWidth', { get: () => availWidth, configurable: true });
    Object.defineProperty(screen, 'availHeight', { get: () => availHeight, configurable: true });
    Object.defineProperty(screen, 'colorDepth', { get: () => colorDepth, configurable: true });
    Object.defineProperty(screen, 'pixelDepth', { get: () => colorDepth, configurable: true });
    Object.defineProperty(window, 'devicePixelRatio', { get: () => pixelRatio, configurable: true });
    Object.defineProperty(window, 'outerWidth', { get: () => width, configurable: true });
    Object.defineProperty(window, 'outerHeight', { get: () => height, configurable: true });
    Object.defineProperty(window, 'innerWidth', { get: () => availWidth, configurable: true });
    Object.defineProperty(window, 'innerHeight', { get: () => availHeight, configurable: true });
})({width}, {height}, {availWidth}, {availHeight}, {colorDepth}, {pixelRatio});
"""

# Timezone patch
TIMEZONE_PATCH = """
((timezone, offset) => {
    const DateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(locales, options) {
        options = options || {};
        options.timeZone = options.timeZone || timezone;
        return new DateTimeFormat(locales, options);
    };
    Intl.DateTimeFormat.prototype = DateTimeFormat.prototype;
    Intl.DateTimeFormat.supportedLocalesOf = DateTimeFormat.supportedLocalesOf;

    const resolvedOptions = DateTimeFormat.prototype.resolvedOptions;
    DateTimeFormat.prototype.resolvedOptions = function() {
        const result = resolvedOptions.call(this);
        if (!result.timeZone) {
            result.timeZone = timezone;
        }
        return result;
    };

    Date.prototype.getTimezoneOffset = function() {
        return offset;
    };
})({timezone}, {offset});
"""


class CDPPatches:
    """CDP patches for hiding browser automation indicators."""

    def __init__(self, fingerprint: Optional[Fingerprint] = None) -> None:
        """Initialize CDP patches with optional fingerprint."""
        self._fingerprint = fingerprint

    @staticmethod
    def get_base_patches() -> list[str]:
        """Get all basic stealth patches that don't require customization."""
        return [
            WEBDRIVER_PATCH,
            CHROME_PATCHES,
            PERMISSIONS_PATCH,
            IFRAME_PATCH,
            CONSOLE_PATCH,
            PLUGINS_PATCH,
        ]

    def get_all_patches(self) -> list[str]:
        """Get all stealth patches including fingerprint-specific ones."""
        patches = self.get_base_patches()

        if self._fingerprint:
            fp = self._fingerprint

            # Languages
            langs_js = str(fp.navigator.languages).replace("'", '"')
            patches.append(
                LANGUAGES_PATCH.replace("['en-US', 'en']", langs_js)
            )

            # Hardware concurrency
            patches.append(
                HARDWARE_CONCURRENCY_PATCH.replace(
                    "{concurrency}",
                    str(fp.navigator.hardware_concurrency)
                )
            )

            # Device memory
            if fp.navigator.device_memory:
                patches.append(
                    DEVICE_MEMORY_PATCH.replace(
                        "{memory}",
                        str(fp.navigator.device_memory)
                    )
                )

            # WebGL
            if fp.webgl.vendor and fp.webgl.renderer:
                patches.append(
                    WEBGL_PATCH
                    .replace("{vendor}", f"'{fp.webgl.vendor}'")
                    .replace("{renderer}", f"'{fp.webgl.renderer}'")
                )

            # Canvas noise
            if fp.canvas.noise_enabled:
                seed = fp.canvas.noise_seed or "Date.now()"
                patches.append(
                    CANVAS_NOISE_PATCH.replace("{seed}", str(seed))
                )

            # Audio noise
            patches.append(
                AUDIO_NOISE_PATCH.replace("{seed}", str(fp.canvas.noise_seed or "Date.now()"))
            )

            # Screen
            patches.append(
                SCREEN_PATCH
                .replace("{width}", str(fp.screen.width))
                .replace("{height}", str(fp.screen.height))
                .replace("{availWidth}", str(fp.screen.avail_width))
                .replace("{availHeight}", str(fp.screen.avail_height))
                .replace("{colorDepth}", str(fp.screen.color_depth))
                .replace("{pixelRatio}", str(fp.screen.device_pixel_ratio))
            )

            # Timezone
            patches.append(
                TIMEZONE_PATCH
                .replace("{timezone}", f"'{fp.timezone}'")
                .replace("{offset}", str(fp.timezone_offset))
            )
        else:
            # Default patches without fingerprint
            patches.append(LANGUAGES_PATCH)
            patches.append(HARDWARE_CONCURRENCY_PATCH.replace("{concurrency}", "8"))
            patches.append(DEVICE_MEMORY_PATCH.replace("{memory}", "8"))

        return patches

    def get_combined_patch(self) -> str:
        """Get all patches combined into a single script."""
        return "\n".join(self.get_all_patches())

    async def apply_to_page(self, cdp_session: Any) -> None:
        """Apply all patches to a CDP session before page loads.

        Args:
            cdp_session: CDP session with send() method
        """
        combined = self.get_combined_patch()
        await cdp_session.send(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": combined}
        )

    @staticmethod
    async def apply_basic_patches(cdp_session: Any) -> None:
        """Apply only basic patches without fingerprint customization.

        Args:
            cdp_session: CDP session with send() method
        """
        combined = "\n".join(CDPPatches.get_base_patches())
        await cdp_session.send(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": combined}
        )
