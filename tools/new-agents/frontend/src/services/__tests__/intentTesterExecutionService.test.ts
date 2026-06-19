import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    createIntentTesterExecution,
    fetchIntentTesterExecutionDetail,
    fetchLatestIntentTesterExecution,
} from '../intentTesterExecutionService';

global.fetch = vi.fn();

describe('intentTesterExecutionService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('creates an intent-tester execution record for an imported testcase', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                code: 200,
                message: '执行任务创建成功',
                data: {
                    execution_id: 'exec-123',
                    status: 'pending',
                    testcase_name: 'TC-001 用户登录成功',
                    start_time: '2026-06-19T10:00:00',
                },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const execution = await createIntentTesterExecution(42);

        expect(fetch).toHaveBeenCalledWith('/intent-tester/api/executions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                testcase_id: 42,
                mode: 'headless',
                browser: 'chrome',
                executed_by: 'new-agents',
            }),
        });
        expect(execution).toEqual({
            executionId: 'exec-123',
            status: 'pending',
            testcaseName: 'TC-001 用户登录成功',
            startTime: '2026-06-19T10:00:00',
        });
    });

    it('fetches the latest intent-tester execution record for an imported testcase', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                code: 200,
                message: '获取成功',
                data: {
                    items: [
                        {
                            execution_id: 'exec-456',
                            test_case_id: 42,
                            status: 'success',
                            mode: 'headless',
                            browser: 'chrome',
                            start_time: '2026-06-19T10:00:00',
                            end_time: '2026-06-19T10:01:00',
                            duration: 60,
                            error_message: null,
                        },
                    ],
                    total: 1,
                    page: 1,
                    size: 1,
                    pages: 1,
                },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const execution = await fetchLatestIntentTesterExecution(42);

        expect(fetch).toHaveBeenCalledWith('/intent-tester/api/executions?testcase_id=42&size=1');
        expect(execution).toEqual({
            executionId: 'exec-456',
            testCaseId: 42,
            status: 'success',
            mode: 'headless',
            browser: 'chrome',
            startTime: '2026-06-19T10:00:00',
            endTime: '2026-06-19T10:01:00',
            duration: 60,
            errorMessage: null,
        });
    });

    it('returns null when no intent-tester executions exist for the testcase', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                code: 200,
                data: {
                    items: [],
                    total: 0,
                    page: 1,
                    size: 1,
                    pages: 0,
                },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchLatestIntentTesterExecution(42)).resolves.toBeNull();
    });

    it('fetches an intent-tester execution detail with step results', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                code: 200,
                message: '获取成功',
                data: {
                    execution_id: 'exec-456',
                    test_case_id: 42,
                    status: 'failed',
                    mode: 'headless',
                    browser: 'chrome',
                    start_time: '2026-06-19T10:00:00',
                    end_time: '2026-06-19T10:01:00',
                    duration: 60,
                    steps_total: 2,
                    steps_passed: 1,
                    steps_failed: 1,
                    error_message: '断言失败',
                    step_executions: [
                        {
                            step_index: 0,
                            step_description: '打开登录页',
                            status: 'success',
                            screenshot_path: '/static/screenshots/step-0.png',
                            action: 'ai_assert',
                            error_message: null,
                        },
                        {
                            step_index: 1,
                            step_description: '验证预期结果',
                            status: 'failed',
                            screenshot_path: '/static/screenshots/step-1.png',
                            action: 'ai_assert',
                            error_message: '未看到工作台',
                        },
                    ],
                },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const detail = await fetchIntentTesterExecutionDetail('exec-456');

        expect(fetch).toHaveBeenCalledWith('/intent-tester/api/executions/exec-456');
        expect(detail.executionId).toBe('exec-456');
        expect(detail.stepsTotal).toBe(2);
        expect(detail.stepsFailed).toBe(1);
        expect(detail.steps[1]).toEqual({
            stepIndex: 1,
            description: '验证预期结果',
            status: 'failed',
            errorMessage: '未看到工作台',
            screenshotPath: '/static/screenshots/step-1.png',
            action: 'ai_assert',
        });
    });

    it('fails explicitly when the create execution response is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ code: 200, data: { execution_id: 123 } }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(createIntentTesterExecution(42)).rejects.toThrow(
            'Invalid intent-tester execution create response'
        );
    });

    it('fails explicitly when the execution list response is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ code: 200, data: { items: [{ execution_id: 'exec-1' }] } }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchLatestIntentTesterExecution(42)).rejects.toThrow(
            'Invalid intent-tester execution list response'
        );
    });

    it('fails explicitly when the execution detail response is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ code: 200, data: { execution_id: 'exec-1', step_executions: [{}] } }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchIntentTesterExecutionDetail('exec-1')).rejects.toThrow(
            'Invalid intent-tester execution detail response'
        );
    });
});
