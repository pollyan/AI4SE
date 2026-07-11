(function () {
    'use strict';

    const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS']);

    function csrfToken() {
        const token = document.querySelector('meta[name="intent-csrf-token"]');
        return token ? token.content : '';
    }

    function csrfHeaders(method) {
        const normalized = String(method || 'GET').toUpperCase();
        if (safeMethods.has(normalized)) {
            return {};
        }
        const token = csrfToken();
        return token ? { 'X-CSRF-Token': token } : {};
    }

    window.IntentSecurity = Object.freeze({ csrfHeaders });

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-capability="denied"]').forEach(function (control) {
            control.hidden = true;
            if ('disabled' in control) {
                control.disabled = true;
            }
        });
    });

    if (window.axios && window.axios.interceptors) {
        window.axios.interceptors.request.use(function (config) {
            config.headers = Object.assign(
                {},
                config.headers || {},
                csrfHeaders(config.method)
            );
            return config;
        });
    }
}());
