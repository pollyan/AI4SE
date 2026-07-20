import type { ProxyOptions } from 'vite';


export type NewAgentsDevProxy = Record<string, ProxyOptions>;

type ProxyAuthRequest = {
    removeHeader: (name: string) => void;
    setHeader: (name: string, value: string) => void;
};

const MODEL_CALLING_PATHS = new Set([
    '/api/agent/runs/stream',
    '/api/config/default/check',
    '/api/utils/mermaid/repair',
]);


export const applyNewAgentsDevProxyAuth = (
    proxyRequest: ProxyAuthRequest,
    requestUrl: string,
    proxyApiKey: string | undefined,
): void => {
    proxyRequest.removeHeader('X-API-Key');
    proxyRequest.removeHeader('X-AI4SE-Gateway');

    const requestPath = requestUrl
        .split(/[?#]/, 1)[0]
        .replace(/^\/new-agents/, '');
    const normalizedProxyApiKey = proxyApiKey?.trim();
    if (normalizedProxyApiKey && MODEL_CALLING_PATHS.has(requestPath)) {
        proxyRequest.setHeader('X-API-Key', normalizedProxyApiKey);
    }
};


export const buildNewAgentsDevProxy = (
    target: string | undefined,
    proxyApiKey?: string,
): NewAgentsDevProxy => {
    const normalizedTarget = target?.trim();
    if (!normalizedTarget) return {};

    return {
        '/new-agents/api': {
            target: normalizedTarget,
            changeOrigin: true,
            configure: (proxy) => {
                proxy.on('proxyReq', (proxyRequest, request) => {
                    applyNewAgentsDevProxyAuth(
                        proxyRequest,
                        request.url || '',
                        proxyApiKey,
                    );
                });
            },
            rewrite: (value: string) => value.replace(/^\/new-agents/, ''),
        },
    };
};
