import { beforeEach, describe, expect, it, vi } from 'vitest';
import { importIntentTesterDraft } from '../intentTesterImportService';
import type { IntentTesterDraft } from '../../core/types';

global.fetch = vi.fn();

const DRAFT: IntentTesterDraft = {
    sourceCaseId: 'TC-001',
    name: 'TC-001 用户登录成功',
    description: '来源: New Agents Lisa TEST_DESIGN/CASES',
    category: '正向功能验证',
    priority: 1,
    tags: ['lisa', 'new-agents', 'TC-001'],
    steps: [
        {
            action: 'ai_assert',
            params: { prompt: '验证预期结果：进入工作台' },
        },
    ],
    draftWarnings: ['导入前需要人工校准'],
};

describe('intentTesterImportService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('imports a Lisa intent-tester draft as a testcase', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                code: 200,
                message: '测试用例创建成功',
                data: {
                    id: 42,
                    name: 'TC-001 用户登录成功',
                },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const created = await importIntentTesterDraft(DRAFT);

        expect(fetch).toHaveBeenCalledWith('/intent-tester/api/testcases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: 'TC-001 用户登录成功',
                description: '来源: New Agents Lisa TEST_DESIGN/CASES',
                category: '正向功能验证',
                priority: 1,
                tags: ['lisa', 'new-agents', 'TC-001'],
                steps: [
                    {
                        action: 'ai_assert',
                        params: { prompt: '验证预期结果：进入工作台' },
                    },
                ],
            }),
        });
        expect(created).toEqual({
            id: 42,
            name: 'TC-001 用户登录成功',
        });
    });

    it('fails explicitly when the intent-tester response is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ code: 200, data: { id: 'broken' } }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(importIntentTesterDraft(DRAFT)).rejects.toThrow(
            'Invalid intent-tester import response'
        );
    });
});
