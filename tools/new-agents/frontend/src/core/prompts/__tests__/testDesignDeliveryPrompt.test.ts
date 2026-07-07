import { describe, expect, it } from 'vitest';

import { DELIVERY_PROMPT, DELIVERY_TEMPLATE } from '../test_design/delivery';

describe('test design delivery prompt', () => {
    it('requires final coverage and traceability visuals for judge-ready delivery', () => {
        expect(DELIVERY_PROMPT).toContain('coverage-map');
        expect(DELIVERY_PROMPT).toContain('traceability-matrix');
        expect(DELIVERY_TEMPLATE).toContain('"type": "coverage-map"');
        expect(DELIVERY_TEMPLATE).toContain('"type": "traceability-matrix"');
        expect(DELIVERY_TEMPLATE).toContain('需求/风险/测试点');
    });
});
