import { describe, expect, it } from 'vitest';
import {
    buildArtifactVisualDiagnostic,
    buildArtifactVisualDiagnosticId,
} from '../artifactVisualDiagnostics';

describe('artifact visual diagnostics', () => {
    it('uses the shared stage and block index format for diagnostic identity', () => {
        expect(buildArtifactVisualDiagnosticId('CLARIFY', 'mermaid', 2)).toBe('mermaid:CLARIFY:2');
        expect(buildArtifactVisualDiagnosticId(undefined, 'structured-visual', 0)).toBe('structured-visual:unknown:0');
    });

    it('builds explicit render failures without fabricating a successful visual state', () => {
        expect(buildArtifactVisualDiagnostic({
            stageId: 'CLARIFY',
            kind: 'mermaid',
            blockIndex: 1,
            message: '',
        })).toEqual({
            id: 'mermaid:CLARIFY:1',
            stageId: 'CLARIFY',
            kind: 'mermaid',
            title: 'Mermaid 图表渲染失败',
            message: '右侧 Mermaid 图表暂时无法渲染。',
            blockIndex: 1,
        });
    });
});
