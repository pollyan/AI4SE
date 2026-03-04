import { describe, it, expect } from 'vitest';
import mermaid from 'mermaid';
import { WORKFLOWS } from '../../workflows';

describe('Mermaid Syntax Validation for INCIDENT_REVIEW Workflow', () => {
    it('should successfully parse the timeline mermaid syntax from timeline prompt', async () => {
        // Initialize mermaid in non-browser env (jsdom is enough, but tell him not to start render loop on load)
        mermaid.initialize({ startOnLoad: false });
        
        // Extract the raw mermaid block from prompt
        const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'TIMELINE')?.description || '';
        
        // We know it looks like:
        // \`\`\`mermaid
        // timeline
        //     title [故障名称] 事件时间线
        // ...
        // \`\`\`
        
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();
        
        const graphDefinition = match![1];
        expect(graphDefinition).toContain('timeline');
        
        // Let mermaid parse it
        try {
           const isValid = await mermaid.parse(graphDefinition);
           expect(isValid).toBeDefined(); // Actually parse function throws error on invalid or returns void
        } catch (e) {
           throw new Error(`Mermaid timeline syntax error: ${e}`);
        }
    });
    
    it('should successfully parse the mindmap mermaid syntax from root_cause prompt', async () => {
        mermaid.initialize({ startOnLoad: false });
        
        const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'ROOT_CAUSE')?.description || '';
        
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();
        
        const graphDefinition = match![1];
        expect(graphDefinition).toContain('mindmap');
        
        try {
           const isValid = await mermaid.parse(graphDefinition);
           expect(isValid).toBeDefined(); 
        } catch (e) {
           throw new Error(`Mermaid mindmap syntax error: ${e}`);
        }
    });
    
    it('should successfully parse the pie mermaid syntax from improvement prompt', async () => {
        mermaid.initialize({ startOnLoad: false });
        
        const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'IMPROVEMENT')?.description || '';
        
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();
        
        const graphDefinition = match![1];
        expect(graphDefinition).toContain('pie');
        
        try {
           await mermaid.parse(graphDefinition);
        } catch (e) {
           throw new Error(`Mermaid pie syntax error: ${e}`);
        }
    });
});
