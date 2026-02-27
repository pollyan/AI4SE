/**
 * TOC 工具函数测试
 * 
 * 测试 TOC 内容选择逻辑：确保 TOC 只基于当前阶段的产出物内容生成，
 * 而不是所有阶段的内容拼接。
 */
import { describe, it, expect } from 'vitest';
import { getActiveArtifactContent, parseTocFromMarkdown } from '../src/utils/tocUtils';
import type { ArtifactProgress } from '../components/ArtifactPanel';

describe('getActiveArtifactContent', () => {
    const multiStageArtifacts: Record<string, string> = {
        'requirement_doc': '## 1. 被测对象\n### 登录功能\n## 2. 测试范围\n### 功能测试',
        'test_design_strategy': '## 1. 风险分析 (FMEA)\n### 风险矩阵\n## 2. 测试分层策略\n### 单元测试',
    };

    const artifactProgress: ArtifactProgress = {
        template: [
            { stageId: 'clarify', artifactKey: 'requirement_doc', name: '需求文档' },
            { stageId: 'strategy', artifactKey: 'test_design_strategy', name: '测试策略蓝图' },
        ],
        completed: ['requirement_doc'],
        generating: null,
    };

    it('当处于策略阶段时，只返回策略蓝图的内容', () => {
        const content = getActiveArtifactContent({
            artifacts: multiStageArtifacts,
            artifactProgress,
            selectedStageId: null,
            currentStageId: 'strategy',
            streamingArtifactContent: null,
            streamingArtifactKey: null,
        });

        expect(content).toBe(multiStageArtifacts['test_design_strategy']);
        // 不应该包含第一阶段的内容
        expect(content).not.toContain('被测对象');
    });

    it('当处于需求澄清阶段时，只返回需求文档的内容', () => {
        const content = getActiveArtifactContent({
            artifacts: multiStageArtifacts,
            artifactProgress,
            selectedStageId: null,
            currentStageId: 'clarify',
            streamingArtifactContent: null,
            streamingArtifactKey: null,
        });

        expect(content).toBe(multiStageArtifacts['requirement_doc']);
        expect(content).not.toContain('风险分析');
    });

    it('当用户选中历史阶段时，返回选中阶段的内容', () => {
        const content = getActiveArtifactContent({
            artifacts: multiStageArtifacts,
            artifactProgress,
            selectedStageId: 'clarify',      // 用户手动选了第一阶段
            currentStageId: 'strategy',       // 当前实际在第二阶段
            streamingArtifactContent: null,
            streamingArtifactKey: null,
        });

        expect(content).toBe(multiStageArtifacts['requirement_doc']);
    });

    it('流式生成中优先使用流式内容', () => {
        const streamingContent = '## 1. 风险分析 (FMEA)\n正在生成...';

        const content = getActiveArtifactContent({
            artifacts: multiStageArtifacts,
            artifactProgress,
            selectedStageId: null,
            currentStageId: 'strategy',
            streamingArtifactContent: streamingContent,
            streamingArtifactKey: 'test_design_strategy',
        });

        expect(content).toBe(streamingContent);
    });

    it('当 artifacts 为空时返回空字符串', () => {
        const content = getActiveArtifactContent({
            artifacts: {},
            artifactProgress,
            selectedStageId: null,
            currentStageId: 'strategy',
            streamingArtifactContent: null,
            streamingArtifactKey: null,
        });

        expect(content).toBe('');
    });
});

describe('parseTocFromMarkdown', () => {
    it('只提取带数字标号的 h2/h3 标题', () => {
        const content = '## 1. 风险分析\n### 风险矩阵\n## [P0] 登录模块\n## 2. 测试分层策略';
        const items = parseTocFromMarkdown(content);

        expect(items).toHaveLength(2);
        expect(items[0].title).toBe('1. 风险分析');
        expect(items[1].title).toBe('2. 测试分层策略');
    });
});
