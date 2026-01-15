/**
 * WorkflowProgress 组件测试
 * 
 * TDD 红阶段：这些测试应该失败，因为组件尚未实现
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { WorkflowProgress, Stage, WorkflowProgressProps } from '../components/WorkflowProgress';

// 测试数据
const mockStages: Stage[] = [
    { id: 'clarify', name: '需求澄清', status: 'completed' },
    { id: 'strategy', name: '策略制定', status: 'active' },
    { id: 'cases', name: '用例编写', status: 'pending' },
    { id: 'delivery', name: '文档交付', status: 'pending' },
];

describe('WorkflowProgress', () => {
    it('should render all stages', () => {
        render(
            <WorkflowProgress
                stages={mockStages}
                currentStageIndex={1}
            />
        );

        expect(screen.getByText('需求澄清')).toBeInTheDocument();
        expect(screen.getByText('策略制定')).toBeInTheDocument();
        expect(screen.getByText('用例编写')).toBeInTheDocument();
        expect(screen.getByText('文档交付')).toBeInTheDocument();
    });

    it('should highlight active stage', () => {
        const { container } = render(
            <WorkflowProgress
                stages={mockStages}
                currentStageIndex={1}
            />
        );

        // 活跃阶段应有旋转的加载图标 (Loader2)
        const spinningIcon = container.querySelector('.animate-spin');
        expect(spinningIcon).toBeInTheDocument();
    });

    it('should show completed stages with checkmark', () => {
        const { container } = render(
            <WorkflowProgress
                stages={mockStages}
                currentStageIndex={1}
            />
        );

        // 已完成阶段应有绿色勾选图标 (Check) - lucide-react 渲染为 svg
        const checkIcon = container.querySelector('.text-green-500');
        expect(checkIcon).toBeInTheDocument();
    });

    it('should return null when stages is empty', () => {
        const { container } = render(
            <WorkflowProgress
                stages={[]}
                currentStageIndex={0}
            />
        );

        expect(container.firstChild).toBeNull();
    });

    it('should handle null currentTask gracefully', () => {
        render(
            <WorkflowProgress
                stages={mockStages}
                currentStageIndex={0}
            />
        );

        // 应该正常渲染阶段
        expect(screen.getByText('需求澄清')).toBeInTheDocument();
    });
});
