import { describe, it, expect } from 'vitest';
import { parseLlmStreamChunk } from '../utils/llmParser';

describe('parseLlmStreamChunk', () => {
    it('should parse CHAT, ARTIFACT and ACTION tags', () => {
        const text = "<CHAT>Hello</CHAT><ACTION>NEXT_STAGE</ACTION><ARTIFACT># Doc</ARTIFACT>";
        const result = parseLlmStreamChunk(text, "old doc");

        expect(result.chatResponse).toBe('Hello');
        expect(result.action).toBe('NEXT_STAGE');
        expect(result.newArtifact).toBe('# Doc');
        expect(result.hasArtifactUpdate).toBe(true);
    });

    it('should handle NO_UPDATE artifact', () => {
        const text = "<CHAT>OK</CHAT><ARTIFACT>NO_UPDATE</ARTIFACT>";
        const result = parseLlmStreamChunk(text, "old doc");

        expect(result.newArtifact).toBe('old doc');
        expect(result.hasArtifactUpdate).toBe(false);
    });

    it('should fallback to raw text if no tags exist', () => {
        const text = "Just raw text";
        const result = parseLlmStreamChunk(text, "old doc");
        expect(result.chatResponse).toBe('Just raw text');
    });
});
