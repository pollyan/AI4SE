import { describe, it, expect } from 'vitest';
import { getAgents, getAgentById } from '../agents';

describe('Agent Configuration', () => {
    it('should return a list of defined agents including Lisa and Alex', () => {
        const agents = getAgents();
        expect(agents.length).toBeGreaterThanOrEqual(2);

        const lisa = agents.find(a => a.id === 'lisa');
        expect(lisa).toBeDefined();
        expect(lisa?.name).toBe('Lisa');
        expect(lisa?.role).toBe('测试专家');
        expect(lisa?.status).toBe('online');
        expect(lisa?.features).toContain('自动化端到端测试设计');

        const alex = agents.find(a => a.id === 'alex');
        expect(alex).toBeDefined();
        expect(alex?.name).toBe('Alex');
        expect(alex?.status).toBe('coming_soon');
        expect(alex?.features).toContain('UI 视觉稿精准切图与识别');
    });

    it('should retrieve a specific agent by ID', () => {
        const agent = getAgentById('lisa');
        expect(agent).toBeDefined();
        expect(agent?.id).toBe('lisa');

        const unknown = getAgentById('unknown_agent');
        expect(unknown).toBeUndefined();
    });
});
