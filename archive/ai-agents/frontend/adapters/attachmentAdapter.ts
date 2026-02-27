import type { AttachmentAdapter } from '@assistant-ui/react';

// Helper to read file as base64
const readFileAsBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const result = reader.result as string;
            // Remove data URL prefix (e.g., "data:image/png;base64,")
            const base64 = result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
};

export const createAttachmentAdapter = (): AttachmentAdapter => ({
    accept: '*', 
    
    async add({ file }) {
        const content = await readFileAsBase64(file);
        return {
            id: Math.random().toString(36).substring(7), // Simple ID
            type: 'file',
            name: file.name,
            contentType: file.type,
            content, 
        };
    },

    async remove() {
        // No-op
    },

    async send(attachment) {
        // 适配层：将标准格式转换为后端期望的格式
        try {
            const decodedContent = atob(attachment.content);
            return {
                type: 'text',
                text: `\n\n[File: ${attachment.name}]\n${decodedContent}\n\n`
            };
        } catch (e) {
            console.error("Failed to decode attachment content", e);
            return {
                type: 'text',
                text: `[File: ${attachment.name}] (Content decode failed)`
            };
        }
    }
});
