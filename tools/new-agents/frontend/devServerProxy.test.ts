import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
    applyNewAgentsDevProxyAuth,
    buildNewAgentsDevProxy,
} from './devServerProxy';


describe('buildNewAgentsDevProxy', () => {
    it('rewrites only the New Agents API prefix', () => {
        const proxy = buildNewAgentsDevProxy('http://127.0.0.1:5002');
        const apiProxy = proxy['/new-agents/api'];

        expect(apiProxy.target).toBe('http://127.0.0.1:5002');
        expect(apiProxy.changeOrigin).toBe(true);
        expect(apiProxy.rewrite('/new-agents/api/agent/runs/stream')).toBe(
            '/api/agent/runs/stream',
        );
    });

    it('stays disabled without an explicit backend target', () => {
        expect(buildNewAgentsDevProxy(undefined)).toEqual({});
        expect(buildNewAgentsDevProxy('  ')).toEqual({});
    });

    it('injects server-side auth only for model-calling routes', () => {
        const proxyKey = 'server-side-proxy-key-canary';
        const makeProxyRequest = () => {
            const removed: string[] = [];
            const headers = new Map<string, string>();
            return {
                removed,
                headers,
                removeHeader: (name: string) => removed.push(name),
                setHeader: (name: string, value: string) => {
                    headers.set(name, value);
                },
            };
        };
        const runtimeRequest = makeProxyRequest();
        const repairRequest = makeProxyRequest();
        const defaultConfigCheckRequest = makeProxyRequest();
        const configUpdateRequest = makeProxyRequest();
        const configCheckRequest = makeProxyRequest();

        applyNewAgentsDevProxyAuth(
            runtimeRequest,
            '/api/agent/runs/stream',
            proxyKey,
        );
        applyNewAgentsDevProxyAuth(
            repairRequest,
            '/new-agents/api/utils/mermaid/repair?attempt=1',
            proxyKey,
        );
        applyNewAgentsDevProxyAuth(
            defaultConfigCheckRequest,
            '/new-agents/api/config/default/check',
            proxyKey,
        );
        applyNewAgentsDevProxyAuth(
            configUpdateRequest,
            '/api/config',
            proxyKey,
        );
        applyNewAgentsDevProxyAuth(
            configCheckRequest,
            '/api/config/check',
            proxyKey,
        );

        expect(runtimeRequest.headers.get('X-API-Key')).toBe(proxyKey);
        expect(repairRequest.headers.get('X-API-Key')).toBe(proxyKey);
        expect(defaultConfigCheckRequest.headers.get('X-API-Key')).toBe(proxyKey);
        expect(configUpdateRequest.headers.has('X-API-Key')).toBe(false);
        expect(configCheckRequest.headers.has('X-API-Key')).toBe(false);
        expect(runtimeRequest.removed).toEqual([
            'X-API-Key',
            'X-AI4SE-Gateway',
        ]);
        expect(configCheckRequest.removed).toEqual([
            'X-API-Key',
            'X-AI4SE-Gateway',
        ]);
    });

    it('does not inject model credentials or endpoints into the browser bundle', () => {
        const configSource = readFileSync(
            join(process.cwd(), 'vite.config.ts'),
            'utf-8',
        );

        expect(configSource).not.toContain('process.env.LLM_API_KEY');
        expect(configSource).not.toContain('process.env.LLM_BASE_URL');
        expect(configSource).not.toContain('process.env.LLM_MODEL');
        expect(configSource).not.toContain('NEW_AGENTS_SMOKE_API_KEY');
        expect(configSource).not.toContain('NEW_AGENTS_DEFAULT_LLM_API_KEY');
        expect(configSource).not.toContain(
            'import.meta.env.NEW_AGENTS_PROXY_API_KEY',
        );
    });
});
