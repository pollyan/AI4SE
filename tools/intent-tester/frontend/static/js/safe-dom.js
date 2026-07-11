(function () {
    'use strict';

    function text(tagName, value) {
        const node = document.createElement(tagName);
        node.textContent = value == null ? '' : String(value);
        return node;
    }

    function button(label, handler) {
        const node = text('button', label);
        node.type = 'button';
        node.addEventListener('click', handler);
        return node;
    }

    function safeUrl(value, allowedProtocols) {
        const protocols = new Set(
            (allowedProtocols || ['http:', 'https:']).map(function (protocol) {
                const normalized = String(protocol).toLowerCase();
                return normalized.endsWith(':') ? normalized : normalized + ':';
            })
        );
        try {
            const parsed = new URL(String(value), document.baseURI);
            return protocols.has(parsed.protocol.toLowerCase()) ? parsed.href : null;
        } catch (error) {
            if (error instanceof TypeError) {
                return null;
            }
            throw error;
        }
    }

    function replaceChildren(target, children) {
        const nodes = Array.from(children || []).filter(function (child) {
            return child instanceof Node;
        });
        target.replaceChildren(...nodes);
        return target;
    }

    window.IntentSafeDom = Object.freeze({ text, button, safeUrl, replaceChildren });
}());
