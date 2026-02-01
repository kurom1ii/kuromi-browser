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

# ============================================================================
# NEW PATCHES FROM MY-FINGERPRINT AND BROWSERFORGE
# ============================================================================

# Seeded random function for consistent fingerprint noise (from my-fingerprint)
SEEDED_RANDOM_PATCH = """
((globalSeed) => {
    window.__fp_seededRandom = function(seed, max = 1, min = 0) {
        const s = Math.sin(seed) * 10000;
        const r = s - Math.floor(s);
        return min + r * (max - min);
    };
    window.__fp_globalSeed = globalSeed;
})({global_seed});
"""

# WebRTC protection (from my-fingerprint) - blocks WebRTC to prevent IP leak
WEBRTC_DISABLE_PATCH = """
(() => {
    // Remove WebRTC APIs entirely
    const webrtcKeys = [
        'RTCDataChannel',
        'RTCIceCandidate',
        'RTCConfiguration',
        'MediaStreamTrack',
        'RTCPeerConnection',
        'RTCSessionDescription',
        'mozMediaStreamTrack',
        'mozRTCPeerConnection',
        'mozRTCSessionDescription',
        'webkitMediaStreamTrack',
        'webkitRTCPeerConnection',
        'webkitRTCSessionDescription',
    ];

    webrtcKeys.forEach(key => {
        if (window[key]) {
            Object.defineProperty(window, key, {
                value: undefined,
                writable: false,
                configurable: false
            });
        }
    });

    // Remove mediaDevices
    const mediaKeys = ['mediaDevices', 'getUserMedia', 'mozGetUserMedia', 'webkitGetUserMedia'];
    mediaKeys.forEach(key => {
        Object.defineProperty(navigator, key, {
            value: undefined,
            writable: false,
            configurable: false
        });
    });
})();
"""

# WebRTC fake IP mode (alternative to blocking)
WEBRTC_FAKE_PATCH = """
((publicIP, localIP) => {
    if (!window.RTCPeerConnection) return;

    const OriginalRTCPeerConnection = window.RTCPeerConnection;

    window.RTCPeerConnection = function(...args) {
        const pc = new OriginalRTCPeerConnection(...args);
        const originalSetLocalDescription = pc.setLocalDescription.bind(pc);

        pc.setLocalDescription = function(desc) {
            if (desc && desc.sdp) {
                // Replace real IPs with fake ones
                desc.sdp = desc.sdp.replace(/([0-9]{1,3}(\\.[0-9]{1,3}){3})/g, publicIP);
            }
            return originalSetLocalDescription(desc);
        };

        return pc;
    };

    window.RTCPeerConnection.prototype = OriginalRTCPeerConnection.prototype;
})({public_ip}, {local_ip});
"""

# WebGPU fingerprint noise (from my-fingerprint)
WEBGPU_NOISE_PATCH = """
((seed) => {
    const seededRandom = (offset) => {
        const s = Math.sin(seed + (offset * 7)) * 10000;
        return s - Math.floor(s);
    };

    const makeNoise = (raw, offset) => {
        const rn = seededRandom(offset) * 64;
        return raw ? raw - Math.floor(rn) : raw;
    };

    // GPUAdapter limits
    if (window.GPUAdapter && GPUAdapter.prototype) {
        const originalLimitsGetter = Object.getOwnPropertyDescriptor(GPUAdapter.prototype, 'limits');
        if (originalLimitsGetter && originalLimitsGetter.get) {
            const origGet = originalLimitsGetter.get;
            Object.defineProperty(GPUAdapter.prototype, 'limits', {
                get: function() {
                    const limits = origGet.call(this);
                    return new Proxy(limits, {
                        get(target, prop) {
                            const value = target[prop];
                            if (prop === 'maxBufferSize') return makeNoise(value, 0);
                            if (prop === 'maxStorageBufferBindingSize') return makeNoise(value, 1);
                            return typeof value === 'function' ? value.bind(target) : value;
                        }
                    });
                },
                configurable: true
            });
        }
    }

    // GPUDevice limits
    if (window.GPUDevice && GPUDevice.prototype) {
        const originalLimitsGetter = Object.getOwnPropertyDescriptor(GPUDevice.prototype, 'limits');
        if (originalLimitsGetter && originalLimitsGetter.get) {
            const origGet = originalLimitsGetter.get;
            Object.defineProperty(GPUDevice.prototype, 'limits', {
                get: function() {
                    const limits = origGet.call(this);
                    return new Proxy(limits, {
                        get(target, prop) {
                            const value = target[prop];
                            if (prop === 'maxBufferSize') return makeNoise(value, 0);
                            if (prop === 'maxStorageBufferBindingSize') return makeNoise(value, 1);
                            return typeof value === 'function' ? value.bind(target) : value;
                        }
                    });
                },
                configurable: true
            });
        }
    }

    // GPUCommandEncoder beginRenderPass
    if (window.GPUCommandEncoder && GPUCommandEncoder.prototype.beginRenderPass) {
        const originalBeginRenderPass = GPUCommandEncoder.prototype.beginRenderPass;
        GPUCommandEncoder.prototype.beginRenderPass = function(desc) {
            if (desc?.colorAttachments?.[0]?.clearValue) {
                try {
                    const cv = desc.colorAttachments[0].clearValue;
                    let offset = 0;
                    for (let key in cv) {
                        const noise = seededRandom(offset++) * 0.01 * 0.001;
                        cv[key] = Math.abs(cv[key] + cv[key] * noise * -1);
                    }
                } catch (e) {}
            }
            return originalBeginRenderPass.call(this, desc);
        };
    }

    // GPUQueue writeBuffer
    if (window.GPUQueue && GPUQueue.prototype.writeBuffer) {
        const originalWriteBuffer = GPUQueue.prototype.writeBuffer;
        GPUQueue.prototype.writeBuffer = function(buffer, offset, data, ...rest) {
            if (data instanceof Float32Array) {
                try {
                    const count = Math.ceil(data.length * 0.05);
                    const indices = Array.from({length: data.length}, (_, i) => i)
                        .sort(() => seededRandom(count) - 0.5)
                        .slice(0, count);

                    let o = 0;
                    for (const idx of indices) {
                        const noise = seededRandom(o++) * 0.0002 - 0.0001;
                        data[idx] += noise * data[idx];
                    }
                } catch (e) {}
            }
            return originalWriteBuffer.call(this, buffer, offset, data, ...rest);
        };
    }
})({seed});
"""

# DomRect fingerprint noise (from my-fingerprint)
DOMRECT_NOISE_PATCH = """
((seed) => {
    const seededRandom = (s) => {
        const x = Math.sin(s) * 10000;
        return x - Math.floor(x);
    };

    const noise = seededRandom(seed) * 1e-6 * 2 - 1e-6;

    // Element.getBoundingClientRect
    const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function() {
        const rect = originalGetBoundingClientRect.call(this);
        if (rect) {
            if (rect.x !== 0) rect.x += noise;
            if (rect.width !== 0) rect.width += noise;
            if (rect.y !== 0) rect.y += noise;
            if (rect.height !== 0) rect.height += noise;
        }
        return rect;
    };

    // Range.getBoundingClientRect
    if (window.Range && Range.prototype.getBoundingClientRect) {
        const originalRangeGetBCR = Range.prototype.getBoundingClientRect;
        Range.prototype.getBoundingClientRect = function() {
            const rect = originalRangeGetBCR.call(this);
            if (rect) {
                if (rect.x !== 0) rect.x += noise;
                if (rect.width !== 0) rect.width += noise;
            }
            return rect;
        };
    }

    // Element.getClientRects
    const originalGetClientRects = Element.prototype.getClientRects;
    Element.prototype.getClientRects = function() {
        const rects = originalGetClientRects.call(this);
        if (rects) {
            for (let i = 0; i < rects.length; i++) {
                const rect = rects[i];
                if (rect.x !== 0) rect.x += noise;
                if (rect.width !== 0) rect.width += noise;
            }
        }
        return rects;
    };
})({seed});
"""

# Font fingerprint noise (from my-fingerprint)
FONT_NOISE_PATCH = """
((seed) => {
    const seededRandom = (s, max = 1, min = 0) => {
        const x = Math.sin(s) * 10000;
        const r = x - Math.floor(x);
        return Math.floor(min + r * (max - min));
    };

    const hashCode = (str) => {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash;
    };

    // offsetHeight/offsetWidth noise
    const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
    const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');

    if (originalOffsetHeight && originalOffsetHeight.get) {
        Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
            get: function() {
                const result = originalOffsetHeight.get.call(this);
                const mark = (this.style?.fontFamily || 'offsetHeight') + result;
                const noise = seededRandom(hashCode(mark) + seed, 2, -1);
                return result + noise;
            },
            configurable: true
        });
    }

    if (originalOffsetWidth && originalOffsetWidth.get) {
        Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
            get: function() {
                const result = originalOffsetWidth.get.call(this);
                const mark = (this.style?.fontFamily || 'offsetWidth') + result;
                const noise = seededRandom(hashCode(mark) + seed, 2, -1);
                return result + noise;
            },
            configurable: true
        });
    }

    // FontFace local() spoofing
    if (window.FontFace) {
        const OriginalFontFace = window.FontFace;
        window.FontFace = function(family, source, descriptors) {
            if (typeof source === 'string' && source.startsWith('local(')) {
                const name = source.substring(source.indexOf('(') + 1, source.indexOf(')'));
                const rand = seededRandom(hashCode(name) + seed, 100, 0) / 100;
                if (rand < 0.02) {
                    source = `local("${rand}")`;
                } else if (rand < 0.04) {
                    source = 'local("Arial")';
                }
            }
            return new OriginalFontFace(family, source, descriptors);
        };
        window.FontFace.prototype = OriginalFontFace.prototype;
    }
})({seed});
"""

# UserAgentData (Client Hints) spoofing (from my-fingerprint)
USERAGENTDATA_PATCH = """
((uaData) => {
    if (!navigator.userAgentData) return;

    const brands = uaData.brands || [];
    const mobile = uaData.mobile || false;
    const platform = uaData.platform || 'Linux';

    const mockUserAgentData = {
        brands: brands,
        mobile: mobile,
        platform: platform,
        getHighEntropyValues: async function(hints) {
            const result = {
                brands: brands,
                mobile: mobile,
                platform: platform
            };

            if (hints.includes('architecture')) result.architecture = uaData.architecture || 'x86';
            if (hints.includes('bitness')) result.bitness = uaData.bitness || '64';
            if (hints.includes('model')) result.model = uaData.model || '';
            if (hints.includes('platformVersion')) result.platformVersion = uaData.platformVersion || '6.5.0';
            if (hints.includes('uaFullVersion')) result.uaFullVersion = uaData.uaFullVersion || '120.0.0.0';
            if (hints.includes('fullVersionList')) result.fullVersionList = uaData.fullVersionList || brands;
            if (hints.includes('wow64')) result.wow64 = uaData.wow64 || false;

            return result;
        },
        toJSON: function() {
            return {
                brands: brands,
                mobile: mobile,
                platform: platform
            };
        }
    };

    Object.defineProperty(navigator, 'userAgentData', {
        get: () => mockUserAgentData,
        configurable: true
    });
})({ua_data});
"""

# Battery API spoofing (from browserforge)
BATTERY_PATCH = """
((batteryData) => {
    if (!navigator.getBattery) return;

    const mockBattery = {
        charging: batteryData.charging,
        chargingTime: batteryData.chargingTime,
        dischargingTime: batteryData.dischargingTime,
        level: batteryData.level,
        addEventListener: function() {},
        removeEventListener: function() {},
        dispatchEvent: function() { return true; },
        onchargingchange: null,
        onchargingtimechange: null,
        ondischargingtimechange: null,
        onlevelchange: null
    };

    navigator.getBattery = function() {
        return Promise.resolve(mockBattery);
    };
})({battery_data});
"""

# Multimedia devices spoofing (from browserforge)
MULTIMEDIA_DEVICES_PATCH = """
((devices) => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;

    const mockDevices = [];

    for (let i = 0; i < devices.webcams; i++) {
        mockDevices.push({
            deviceId: 'webcam_' + i,
            kind: 'videoinput',
            label: '',
            groupId: 'group_video_' + i,
            toJSON: function() { return this; }
        });
    }

    for (let i = 0; i < devices.microphones; i++) {
        mockDevices.push({
            deviceId: 'mic_' + i,
            kind: 'audioinput',
            label: '',
            groupId: 'group_audio_' + i,
            toJSON: function() { return this; }
        });
    }

    for (let i = 0; i < devices.speakers; i++) {
        mockDevices.push({
            deviceId: 'speaker_' + i,
            kind: 'audiooutput',
            label: '',
            groupId: 'group_output_' + i,
            toJSON: function() { return this; }
        });
    }

    navigator.mediaDevices.enumerateDevices = function() {
        return Promise.resolve(mockDevices);
    };
})({devices});
"""

# Video/Audio codec support spoofing (from browserforge)
CODECS_PATCH = """
((videoCodecs, audioCodecs) => {
    // Video codec support
    const originalCanPlayType = HTMLVideoElement.prototype.canPlayType;
    HTMLVideoElement.prototype.canPlayType = function(type) {
        if (type.includes('video/mp4') || type.includes('avc1')) {
            return videoCodecs.h264 || '';
        }
        if (type.includes('video/ogg') || type.includes('theora')) {
            return videoCodecs.ogg || '';
        }
        if (type.includes('video/webm') || type.includes('vp8') || type.includes('vp9')) {
            return videoCodecs.webm || '';
        }
        return originalCanPlayType.call(this, type);
    };

    // Audio codec support
    const originalAudioCanPlayType = HTMLAudioElement.prototype.canPlayType;
    HTMLAudioElement.prototype.canPlayType = function(type) {
        if (type.includes('audio/aac') || type.includes('mp4a')) {
            return audioCodecs.aac || '';
        }
        if (type.includes('audio/mpeg') || type.includes('mp3')) {
            return audioCodecs.mp3 || '';
        }
        if (type.includes('audio/ogg') || type.includes('vorbis')) {
            return audioCodecs.ogg || '';
        }
        if (type.includes('audio/wav')) {
            return audioCodecs.wav || '';
        }
        return originalAudioCanPlayType.call(this, type);
    };
})({video_codecs}, {audio_codecs});
"""

# Advanced Audio fingerprint noise with DynamicsCompressor (from my-fingerprint)
AUDIO_ADVANCED_PATCH = """
((seed) => {
    const seededRandom = (s, max = 1, min = 0) => {
        const x = Math.sin(s) * 10000;
        const r = x - Math.floor(x);
        return min + r * (max - min);
    };

    const dcNoise = seededRandom(seed) * 1e-7;
    const processedBuffers = new WeakSet();

    // AudioBuffer.getChannelData with step-based noise
    const originalGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {
        const data = originalGetChannelData.call(this, channel);
        if (processedBuffers.has(data)) return data;

        const step = data.length > 2000 ? 100 : 20;
        for (let i = 0; i < data.length; i += step) {
            const v = data[i];
            if (v !== 0 && Math.abs(v) > 1e-7) {
                data[i] += seededRandom(seed + i) * 1e-7;
            }
        }

        processedBuffers.add(data);
        return data;
    };

    // DynamicsCompressorNode.reduction noise
    if (window.DynamicsCompressorNode) {
        const originalReductionGetter = Object.getOwnPropertyDescriptor(
            DynamicsCompressorNode.prototype, 'reduction'
        );
        if (originalReductionGetter && originalReductionGetter.get) {
            Object.defineProperty(DynamicsCompressorNode.prototype, 'reduction', {
                get: function() {
                    const res = originalReductionGetter.get.call(this);
                    return (typeof res === 'number' && res !== 0) ? res + dcNoise : res;
                },
                configurable: true
            });
        }
    }
})({seed});
"""

# Function.prototype.toString protection (from my-fingerprint)
# Makes proxied functions appear native
TOSTRING_PROTECTION_PATCH = """
(() => {
    const proxiedFunctions = new WeakSet();
    const originalToString = Function.prototype.toString;

    window.__fp_markAsProxied = function(fn, original) {
        proxiedFunctions.add(fn);
        fn.__fp_original = original;
    };

    Function.prototype.toString = function() {
        if (proxiedFunctions.has(this) && this.__fp_original) {
            return originalToString.call(this.__fp_original);
        }
        return originalToString.call(this);
    };
})();
"""


class CDPPatches:
    """CDP patches for hiding browser automation indicators.

    Enhanced with techniques from my-fingerprint, browserforge, and camoufox.
    Supports: WebRTC, WebGPU, DomRect, Font, UserAgentData, Battery, Codecs.
    """

    def __init__(self, fingerprint: Optional[Fingerprint] = None) -> None:
        """Initialize CDP patches with optional fingerprint."""
        self._fingerprint = fingerprint

    @staticmethod
    def get_base_patches() -> list[str]:
        """Get all basic stealth patches that don't require customization."""
        return [
            TOSTRING_PROTECTION_PATCH,  # Must be first to protect other patches
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

            # Global seed for consistent noise
            global_seed = fp.global_seed or fp.canvas.noise_seed or "Date.now()"
            patches.append(
                SEEDED_RANDOM_PATCH.replace("{global_seed}", str(global_seed))
            )

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

            # Audio noise (basic and advanced)
            audio_seed = fp.audio.noise_seed or fp.canvas.noise_seed or "Date.now()"
            patches.append(
                AUDIO_NOISE_PATCH.replace("{seed}", str(audio_seed))
            )
            if fp.audio.noise_enabled:
                patches.append(
                    AUDIO_ADVANCED_PATCH.replace("{seed}", str(audio_seed))
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

            # ========== NEW PATCHES FROM MY-FINGERPRINT ==========

            # WebRTC protection
            if not fp.webrtc.enabled or fp.webrtc.mode == "disable":
                patches.append(WEBRTC_DISABLE_PATCH)
            elif fp.webrtc.mode == "fake" and fp.webrtc.public_ip:
                patches.append(
                    WEBRTC_FAKE_PATCH
                    .replace("{public_ip}", f"'{fp.webrtc.public_ip}'")
                    .replace("{local_ip}", f"'{fp.webrtc.local_ip or fp.webrtc.public_ip}'")
                )

            # WebGPU noise
            if fp.webgpu.noise_enabled:
                webgpu_seed = fp.webgpu.noise_seed or fp.canvas.noise_seed or "Date.now()"
                patches.append(
                    WEBGPU_NOISE_PATCH.replace("{seed}", str(webgpu_seed))
                )

            # DomRect noise
            if fp.dom_rect.noise_enabled:
                domrect_seed = fp.dom_rect.noise_seed or fp.canvas.noise_seed or "Date.now()"
                patches.append(
                    DOMRECT_NOISE_PATCH.replace("{seed}", str(domrect_seed))
                )

            # Font noise
            if fp.font_fp.noise_enabled:
                font_seed = fp.font_fp.noise_seed or fp.canvas.noise_seed or "Date.now()"
                patches.append(
                    FONT_NOISE_PATCH.replace("{seed}", str(font_seed))
                )

            # UserAgentData (Client Hints)
            ua_data = {
                "brands": fp.user_agent_data.brands,
                "mobile": fp.user_agent_data.mobile,
                "platform": fp.user_agent_data.platform,
                "platformVersion": fp.user_agent_data.platform_version,
                "architecture": fp.user_agent_data.architecture,
                "bitness": fp.user_agent_data.bitness,
                "model": fp.user_agent_data.model,
                "uaFullVersion": fp.user_agent_data.ua_full_version,
                "fullVersionList": fp.user_agent_data.full_version_list,
                "wow64": fp.user_agent_data.wow64,
            }
            import json
            patches.append(
                USERAGENTDATA_PATCH.replace("{ua_data}", json.dumps(ua_data))
            )

            # Battery API
            battery_data = {
                "charging": fp.battery.charging,
                "chargingTime": fp.battery.charging_time,
                "dischargingTime": fp.battery.discharging_time,
                "level": fp.battery.level,
            }
            patches.append(
                BATTERY_PATCH.replace("{battery_data}", json.dumps(battery_data))
            )

            # Multimedia devices
            devices = {
                "webcams": fp.multimedia_devices.webcams,
                "microphones": fp.multimedia_devices.microphones,
                "speakers": fp.multimedia_devices.speakers,
            }
            patches.append(
                MULTIMEDIA_DEVICES_PATCH.replace("{devices}", json.dumps(devices))
            )

            # Video/Audio codecs
            patches.append(
                CODECS_PATCH
                .replace("{video_codecs}", json.dumps(fp.video_codecs))
                .replace("{audio_codecs}", json.dumps(fp.audio_codecs))
            )

        else:
            # Default patches without fingerprint
            patches.append(LANGUAGES_PATCH)
            patches.append(HARDWARE_CONCURRENCY_PATCH.replace("{concurrency}", "8"))
            patches.append(DEVICE_MEMORY_PATCH.replace("{memory}", "8"))
            patches.append(WEBRTC_DISABLE_PATCH)  # Block WebRTC by default

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
