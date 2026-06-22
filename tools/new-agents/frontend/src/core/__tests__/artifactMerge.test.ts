import { describe, expect, it } from 'vitest';
import {
    buildConflictMergeBlockLabel,
    buildConflictModificationBlockLabel,
    buildContiguousDiffBlocks,
    buildAutoMergedInsertionResult,
    replaceFirstLineSequence,
} from '../artifactMerge';
import type { LineDiffEntry } from '../artifactDiff';

describe('artifactMerge helpers', () => {
    it('builds labels for merge and modification blocks with truncated lines', () => {
        const longLine = '这是一个非常长的冲突行，用于验证活动轨迹标签会被截断，避免在按钮和审计记录中撑开布局。'.repeat(2);
        const longLabel = buildConflictMergeBlockLabel([longLine]);

        expect(buildConflictMergeBlockLabel(['第一行', '第二行'])).toBe('第一行 / 第二行');
        expect(longLabel).toHaveLength(60);
        expect(longLabel.endsWith('...')).toBe(true);
        expect(buildConflictModificationBlockLabel(['旧行'], ['新行'])).toBe('旧行 → 新行');
    });

    it('collects contiguous non-blank added or removed diff blocks with at least two lines', () => {
        const diff: LineDiffEntry[] = [
            { type: 'unchanged', content: '保留' },
            { type: 'removed', content: '旧第一行' },
            { type: 'removed', content: '旧第二行' },
            { type: 'removed', content: '   ' },
            { type: 'added', content: '新单行不成块' },
            { type: 'unchanged', content: '间隔' },
            { type: 'added', content: '新第一行' },
            { type: 'added', content: '新第二行' },
        ];

        expect(buildContiguousDiffBlocks(diff, 'removed')).toEqual([
            {
                startIndex: 1,
                lines: ['旧第一行', '旧第二行'],
                label: '旧第一行 / 旧第二行',
            },
        ]);
        expect(buildContiguousDiffBlocks(diff, 'added')).toEqual([
            {
                startIndex: 6,
                lines: ['新第一行', '新第二行'],
                label: '新第一行 / 新第二行',
            },
        ]);
    });

    it('replaces only the first matching non-blank line sequence', () => {
        const source = ['A', 'B', 'C', 'B', 'C', 'D'];

        expect(replaceFirstLineSequence(source, ['B', 'C'], ['X', 'Y'])).toEqual([
            'A',
            'X',
            'Y',
            'B',
            'C',
            'D',
        ]);
        expect(replaceFirstLineSequence(source, ['missing'], ['X'])).toBe(source);
        expect(replaceFirstLineSequence(source, ['   '], ['X'])).toBe(source);
    });

    it('auto-merges non-overlapping server and draft insertions', () => {
        const result = buildAutoMergedInsertionResult(
            ['# 策略', '', '## 范围', '基础范围'].join('\n'),
            ['# 策略', '', '服务端补充风险', '## 范围', '基础范围'].join('\n'),
            ['# 策略', '', '## 范围', '草稿补充验收', '基础范围'].join('\n')
        );

        expect(result).toEqual({
            content: ['# 策略', '', '服务端补充风险', '## 范围', '草稿补充验收', '基础范围'].join('\n'),
            summary: '合并轨迹：自动合并服务端与草稿的非重叠补充',
        });
    });

    it('auto-merges server insertions with draft deletions when base lines are unique', () => {
        const result = buildAutoMergedInsertionResult(
            ['A', 'B', 'C'].join('\n'),
            ['A', 'server', 'B', 'C'].join('\n'),
            ['A', 'C'].join('\n')
        );

        expect(result?.content).toBe(['A', 'server', 'C'].join('\n'));
    });

    it('rejects draft deletions when repeated base lines make anchors ambiguous', () => {
        const result = buildAutoMergedInsertionResult(
            ['A', 'B', 'A'].join('\n'),
            ['A', 'server', 'B', 'A'].join('\n'),
            ['A', 'B'].join('\n')
        );

        expect(result).toBeNull();
    });
});
