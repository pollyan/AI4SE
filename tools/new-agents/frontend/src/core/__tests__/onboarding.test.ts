import { describe, it, expect } from 'vitest';
import { WORKFLOWS } from '../workflows';
import { WorkflowType } from '../types';

describe('Onboarding Welcome Kit 配置', () => {

    const allWorkflowKeys = Object.keys(WORKFLOWS) as WorkflowType[];

    it('每个工作流都必须有 onboarding 配置', () => {
        for (const key of allWorkflowKeys) {
            const workflow = WORKFLOWS[key];
            expect(workflow.onboarding, `${key} 缺少 onboarding 配置`).toBeDefined();
            expect(workflow.onboarding.welcomeMessage, `${key} 缺少 welcomeMessage`).toBeTruthy();
            expect(workflow.onboarding.starterPrompts, `${key} 缺少 starterPrompts`).toBeDefined();
            expect(workflow.onboarding.inputPlaceholder, `${key} 缺少 inputPlaceholder`).toBeTruthy();
        }
    });

    it('每个工作流的 starterPrompts 应包含 2-3 个示例', () => {
        for (const key of allWorkflowKeys) {
            const prompts = WORKFLOWS[key].onboarding.starterPrompts;
            expect(prompts.length, `${key} 的 starterPrompts 数量不在 2-3 范围`).toBeGreaterThanOrEqual(2);
            expect(prompts.length, `${key} 的 starterPrompts 数量不在 2-3 范围`).toBeLessThanOrEqual(3);
        }
    });

    it('starterPrompts 中不应包含空字符串', () => {
        for (const key of allWorkflowKeys) {
            const prompts = WORKFLOWS[key].onboarding.starterPrompts;
            for (const prompt of prompts) {
                expect(prompt.trim(), `${key} 中存在空的 starterPrompt`).not.toBe('');
            }
        }
    });

    it('inputPlaceholder 不应过长（不超过 50 个字符）', () => {
        for (const key of allWorkflowKeys) {
            const placeholder = WORKFLOWS[key].onboarding.inputPlaceholder;
            expect(placeholder.length, `${key} 的 inputPlaceholder 过长: "${placeholder}"`).toBeLessThanOrEqual(50);
        }
    });
});
