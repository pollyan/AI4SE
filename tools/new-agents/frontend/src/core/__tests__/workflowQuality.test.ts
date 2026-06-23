import { describe, expect, it } from 'vitest';
import { WORKFLOWS } from '../workflows';
import { buildWorkflowQualitySummary } from '../workflowQuality';

describe('buildWorkflowQualitySummary', () => {
  it('passes a complete stage artifact with contract evidence', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'STRATEGY',
      artifactMarkdown: [
        '# 测试策略蓝图',
        '## 1. 策略摘要',
        '## 2. 质量目标',
        '## 3. 风险识别与 FMEA',
        '### 3.1 风险矩阵',
        '### 3.2 风险明细',
        '## 4. 测试技术选型',
        '## 5. 测试分层策略',
        '### 5.1 测试金字塔',
        '### 5.2 分层明细',
        '## 6. 测试点拓扑',
        '## 7. 资源与取舍',
        '## 8. 阶段门禁',
        '| 风险 ID | 测试点 ID | 覆盖建议 |',
        '| R1 | TP1 | 覆盖核心链路 |',
        '```mermaid',
        'quadrantChart',
        '```',
        '```mermaid',
        'block-beta',
        '```',
        '```ai4se-visual',
        '{"type":"risk-board","items":[]}',
        '```',
      ].join('\n'),
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('pass');
    expect(summary.score).toBeGreaterThanOrEqual(90);
    expect(summary.failedCount).toBe(0);
    expect(summary.actionItems).toEqual([]);
  });

  it('fails when required headings are missing', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'STRATEGY',
      artifactMarkdown: '# 测试策略蓝图\n\n## 1. 策略摘要\n\n## 8. 阶段门禁',
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('fail');
    expect(summary.failedCount).toBeGreaterThan(0);
    expect(summary.actionItems.some(item => item.includes('补齐必需章节'))).toBe(true);
  });

  it('warns when visual contract evidence is missing', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'STRATEGY',
      artifactMarkdown: [
        '# 测试策略蓝图',
        '## 1. 策略摘要',
        '## 2. 质量目标',
        '## 3. 风险识别与 FMEA',
        '### 3.1 风险矩阵',
        '### 3.2 风险明细',
        '## 4. 测试技术选型',
        '## 5. 测试分层策略',
        '### 5.1 测试金字塔',
        '### 5.2 分层明细',
        '## 6. 测试点拓扑',
        '## 7. 资源与取舍',
        '## 8. 阶段门禁',
        '风险 ID 测试点 ID 覆盖建议',
      ].join('\n'),
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('warning');
    expect(summary.warningCount).toBeGreaterThan(0);
    expect(summary.actionItems.some(item => item.includes('补齐可视化'))).toBe(true);
  });

  it('fails empty artifact content', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'CLARIFY',
      artifactMarkdown: '   ',
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('fail');
    expect(summary.score).toBeLessThan(50);
    expect(summary.actionItems[0]).toContain('生成或恢复当前阶段产出物');
  });

  it('uses only current-stage visual diagnostics as quality issues', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'CLARIFY',
      artifactMarkdown: '# 需求分析文档\n\n## 8. 阶段门禁\n\n```mermaid\nflowchart TD\n```',
      visualDiagnostics: [
        {
          id: 'mermaid:CLARIFY:0',
          stageId: 'CLARIFY',
          kind: 'mermaid',
          title: 'Mermaid 渲染失败',
          message: '第 1 个 Mermaid 图无法渲染',
          createdAt: 1,
        },
        {
          id: 'mermaid:STRATEGY:0',
          stageId: 'STRATEGY',
          kind: 'mermaid',
          title: '其他阶段失败',
          message: '其他阶段问题',
          createdAt: 2,
        },
      ],
    });

    expect(summary.actionItems).toContain('修复当前阶段可视化渲染问题：第 1 个 Mermaid 图无法渲染');
    expect(summary.actionItems).not.toContain('修复当前阶段可视化渲染问题：其他阶段问题');
  });
});
