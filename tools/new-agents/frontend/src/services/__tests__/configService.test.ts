import { describe, expect, it, vi, beforeEach } from 'vitest';
import { checkDefaultLlmConfig } from '../configService';

describe('configService', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('checks default model connectivity with backend message fallback', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue({
                ok: true,
                message: '模型配置可用',
            }),
        });
        vi.stubGlobal('fetch', fetchMock);

        await expect(checkDefaultLlmConfig()).resolves.toEqual({
            ok: true,
            message: '模型配置可用',
        });
        expect(fetchMock).toHaveBeenCalledWith('/new-agents/api/config/default/check', { method: 'POST' });
    });

    it('uses backend error text when model connectivity check fails', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
            ok: false,
            json: vi.fn().mockResolvedValue({
                error: 'API Key 无效',
            }),
        }));

        await expect(checkDefaultLlmConfig()).resolves.toEqual({
            ok: false,
            message: 'API Key 无效',
        });
    });

    it('uses default failure text when the config check request rejects', async () => {
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network failed')));

        await expect(checkDefaultLlmConfig()).resolves.toEqual({
            ok: false,
            message: '模型连接检测失败',
        });
    });
});
