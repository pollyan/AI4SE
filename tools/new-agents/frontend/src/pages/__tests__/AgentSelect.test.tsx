import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentSelect } from '../AgentSelect';
import { BrowserRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return { ...actual, useNavigate: () => mockNavigate };
});

describe('AgentSelect Page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    function renderComponent() {
        return render(
            <BrowserRouter>
                <AgentSelect />
            </BrowserRouter>
        );
    }

    it('renders the page title', () => {
        renderComponent();
        expect(screen.getByText('选择你的 AI 助手')).toBeTruthy();
    });

    it('renders both agents (alex and lisa)', () => {
        renderComponent();
        expect(screen.getAllByText('Alex').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Lisa').length).toBeGreaterThanOrEqual(1);
    });

    it('displays agent descriptions', () => {
        renderComponent();
        expect(screen.getByText(/业务需求深度解析/)).toBeTruthy();
        expect(screen.getByText(/智能化跟进需求评审/)).toBeTruthy();
    });

    it('displays agent roles', () => {
        renderComponent();
        expect(screen.getByText('业务需求分析师')).toBeTruthy();
        expect(screen.getByText('测试专家')).toBeTruthy();
    });

    it('renders agent features', () => {
        renderComponent();
        expect(screen.getByText('功能逻辑树构建')).toBeTruthy();
        expect(screen.getByText('测试策略推导与用例设计')).toBeTruthy();
    });

    it('navigates to workflows when clicking an online agent card', () => {
        renderComponent();
        const alexCard = screen.getAllByText('Alex').find(el => el.closest('[class*="rounded-2xl"]'))!.closest('[class*="rounded-2xl"]')!;
        fireEvent.click(alexCard);
        expect(mockNavigate).toHaveBeenCalledWith('/workflows/alex');
    });

    it('navigates to lisa workflows when clicking lisa card', () => {
        renderComponent();
        const lisaCard = screen.getAllByText('Lisa').find(el => el.closest('[class*="rounded-2xl"]'))!.closest('[class*="rounded-2xl"]')!;
        fireEvent.click(lisaCard);
        expect(mockNavigate).toHaveBeenCalledWith('/workflows/lisa');
    });

    it('renders back link', () => {
        renderComponent();
        expect(screen.getByText('返回平台首页')).toBeTruthy();
    });

    it('renders the hint badges for both agents', () => {
        renderComponent();
        expect(screen.getByText(/想梳理产品思路/)).toBeTruthy();
        expect(screen.getByText(/想设计测试用例/)).toBeTruthy();
    });
});
