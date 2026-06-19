import { describe, expect, it } from 'vitest';
import { buildLineDiff } from '../artifactDiff';

describe('artifactDiff', () => {
    it('builds a stable line diff between a historical artifact and the current artifact', () => {
        const diff = buildLineDiff(
            '# 标题\n旧结论\n保留内容',
            '# 标题\n新结论\n保留内容\n新增风险',
        );

        expect(diff).toEqual([
            { type: 'unchanged', content: '# 标题' },
            { type: 'removed', content: '旧结论' },
            { type: 'added', content: '新结论' },
            { type: 'unchanged', content: '保留内容' },
            { type: 'added', content: '新增风险' },
        ]);
    });
});
