import { describe, it, expect } from 'vitest';
import mermaid from 'mermaid';
import { WORKFLOWS } from '../../workflows';
import { parseStructuredVisual } from '../../structuredVisuals';

describe('Mermaid Syntax Validation for INCIDENT_REVIEW Workflow', () => {
   it('should use timeline-map in the timeline prompt instead of Mermaid timeline', () => {
      const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'TIMELINE')?.template || '';
      const match = promptText.match(/```ai4se-visual\n([\s\S]*?)```/);

      expect(match).toBeTruthy();
      expect(promptText).not.toContain('```mermaid');
      expect(promptText).not.toContain('\ntimeline\n');
      const result = parseStructuredVisual(match![1]);
      expect(result.valid).toBe(true);
      if (result.valid === false) throw new Error(result.message);
      expect(result.visual.kind).toBe('timeline');
   });

   it('should successfully parse the mindmap mermaid syntax from root_cause prompt', async () => {
      mermaid.initialize({ startOnLoad: false });

      const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'ROOT_CAUSE')?.template || '';

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

      const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'IMPROVEMENT')?.template || '';

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
