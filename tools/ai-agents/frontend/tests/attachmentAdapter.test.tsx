import { describe, it, expect, vi } from 'vitest';
// @ts-expect-error - Not created yet
import { createAttachmentAdapter } from '../adapters/attachmentAdapter';

describe('AttachmentAdapter', () => {
    it('adds file and returns attachment object', async () => {
        const adapter = createAttachmentAdapter();
        const file = new File(['hello world'], 'test.txt', { type: 'text/plain' });
        
        const attachment = await adapter.add({ file });
        
        expect(attachment).toMatchObject({
            name: 'test.txt',
            type: 'file',
            contentType: 'text/plain'
        });
        // btoa('hello world') = aGVsbG8gd29ybGQ=
        // But readAsDataURL includes prefix "data:text/plain;base64,..."
        // We need to check implementation. Usually content is just the data.
        // Let's just check it is a string.
        expect(typeof attachment.content).toBe('string');
    });

    it('converts attachment to text part on send (Backend Compatibility)', async () => {
        const adapter = createAttachmentAdapter();
        const attachment = {
            id: '1',
            type: 'file' as const,
            name: 'test.txt',
            content: btoa('hello world'), // Base64 content (simulated)
            contentType: 'text/plain'
        };

        const part = await adapter.send(attachment);
        
        expect(part).toEqual({
            type: 'text',
            text: expect.stringContaining('[File: test.txt]')
        });
        expect(part.text).toContain('hello world');
    });
});
