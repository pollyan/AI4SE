import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkflowSelect } from '../WorkflowSelect';
import { BrowserRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return { ...actual, useNavigate: () => mockNavigate, useParams: vi.fn() };
});

const mockUseParams = vi.mocked(await import('react-router-dom')).useParams;

describe('WorkflowSelect Page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    function renderComponent(agentId?: string) {
        mockUseParams.mockReturnValue({ agentId: agentId || '' });
        return render(
            <BrowserRouter>
                <WorkflowSelect />
            </BrowserRouter>
        );
    }

    describe('for alex agent', () => {
        it('renders alex workflow header', () => {
            renderComponent('alex');
            expect(screen.getByText(/Alex.*的工作流/)).toBeTruthy();
        });

        it('renders alex workflows', () => {
            renderComponent('alex');
            expect(screen.getByText('创意头脑风暴')).toBeTruthy();
            expect(screen.getByText('需求蓝图梳理')).toBeTruthy();
        });

        it('shows status labels for plan workflows', () => {
            renderComponent('alex');
            expect(screen.getAllByText('Plan').length).toBeGreaterThanOrEqual(1);
        });

        it('navigates on clicking an online workflow', () => {
            renderComponent('alex');
            const card = screen.getByText('创意头脑风暴').closest('[class*="rounded-2xl"]')!;
            fireEvent.click(card);
            expect(mockNavigate).toHaveBeenCalledWith('/workspace/alex/idea-brainstorm');
        });
    });

    describe('for lisa agent', () => {
        it('renders lisa workflow header', () => {
            renderComponent('lisa');
            expect(screen.getByText(/Lisa.*的工作流/)).toBeTruthy();
        });

        it('renders lisa workflows', () => {
            renderComponent('lisa');
            expect(screen.getByText('测试策略与用例设计')).toBeTruthy();
            expect(screen.getByText('需求评审')).toBeTruthy();
            expect(screen.getByText('线上故障复盘')).toBeTruthy();
        });

        it('keeps lisa workflow cards compact by hiding preview details', () => {
            renderComponent('lisa');

            expect(screen.queryByText('适合')).toBeNull();
            expect(screen.queryByText('不适合')).toBeNull();
            expect(screen.queryByText('准备输入')).toBeNull();
            expect(screen.queryByText('产出')).toBeNull();
            expect(screen.queryByText('样例输入')).toBeNull();
            expect(screen.queryByText(/支付功能上线前/)).toBeNull();
        });

        it('keeps alex workflow cards compact by hiding preview details', () => {
            renderComponent('alex');

            expect(screen.queryByText('适合')).toBeNull();
            expect(screen.queryByText('不适合')).toBeNull();
            expect(screen.queryByText('准备输入')).toBeNull();
            expect(screen.queryByText('产出')).toBeNull();
            expect(screen.queryByText('样例输入')).toBeNull();
            expect(screen.queryByText(/目标用户、痛点或机会假设/)).toBeNull();
        });

        it('shows dev and plan status labels', () => {
            renderComponent('lisa');
            expect(screen.getByText('Dev')).toBeTruthy();
            expect(screen.getByText('Plan')).toBeTruthy();
        });

        it('navigates on clicking an online lisa workflow', () => {
            renderComponent('lisa');
            const card = screen.getByText('测试策略与用例设计').closest('[class*="rounded-2xl"]')!;
            fireEvent.click(card);
            expect(mockNavigate).toHaveBeenCalledWith('/workspace/lisa/test-design');
        });
    });

    describe('edge cases', () => {
        it('shows fallback when agent is not found', () => {
            renderComponent('unknown-agent');
            expect(screen.getByText('该智能体暂不支持工作流配置')).toBeTruthy();
        });

        it('shows back button', () => {
            renderComponent('alex');
            expect(screen.getByText('返回智能体列表')).toBeTruthy();
        });
    });
});
