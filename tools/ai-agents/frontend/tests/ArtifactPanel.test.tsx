import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ArtifactPanel } from '../components/ArtifactPanel';

describe('ArtifactPanel', () => {
  const defaultProps = {
    artifactProgress: {
      template: [{ stageId: 'stage1', artifactKey: 'doc1', name: '需求文档' }],
      completed: [],
      generating: null,
    },
    selectedStageId: null,
    currentStageId: 'stage1',
    artifacts: {},
    streamingArtifactKey: null,
    streamingArtifactContent: null,
    onBackToCurrentStage: vi.fn(),
  };

  describe('状态标签显示', () => {
    it('无内容且未生成时显示"待生成"', () => {
      render(<ArtifactPanel {...defaultProps} />);
      expect(screen.getByText('待生成')).toBeInTheDocument();
    });

    it('正在生成时显示"生成中..."', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          streamingArtifactKey="doc1"
          streamingArtifactContent="# 正在生成..."
        />
      );
      expect(screen.getByText('生成中...')).toBeInTheDocument();
    });

    it('有内容时显示"已生成"', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          artifacts={{ doc1: '# 完整文档' }}
        />
      );
      expect(screen.getByText('已生成')).toBeInTheDocument();
    });
  });

  describe('内容区显示逻辑', () => {
    it('生成中时保持显示旧内容而非流式内容', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          artifacts={{ doc1: '# 旧版本内容' }}
          streamingArtifactKey="doc1"
          streamingArtifactContent="# 新版本正在生成..."
        />
      );
      // 应该显示旧内容
      expect(screen.getByText('旧版本内容')).toBeInTheDocument();
      // 不应该显示流式新内容
      expect(screen.queryByText('新版本正在生成...')).not.toBeInTheDocument();
    });

    it('无旧内容时生成中显示占位符', () => {
      render(
        <ArtifactPanel
          {...defaultProps}
          streamingArtifactKey="doc1"
          streamingArtifactContent="# 首次生成..."
        />
      );
      expect(screen.getByText('完成当前阶段对话后，将在此生成产出物')).toBeInTheDocument();
    });
  });
});
