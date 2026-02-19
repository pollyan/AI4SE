import { useMemo } from 'react';
import { useChatRuntime as useAISdkChatRuntime, AssistantChatTransport } from "@assistant-ui/react-ai-sdk";
import { AssistantId } from "../types";
import { ProgressInfo } from "../services/backendService";
import { createAttachmentAdapter } from '../adapters/attachmentAdapter';

const API_BASE = '/ai-agents/api/requirements';

export function useChatRuntime(sessionId: string, assistantType: AssistantId, onProgressChange?: (progress: ProgressInfo) => void, onStreamEnd?: () => void) {
    const api = `${API_BASE}/sessions/${sessionId}/messages/v2/stream`;

    const transport = useMemo(() => new AssistantChatTransport({
        url: api,
        headers: {
            'X-Assistant-Type': assistantType,
        },
    }), [api, assistantType]);

    // const attachmentAdapter = useMemo(() => createAttachmentAdapter(), []);

    return useAISdkChatRuntime({
        transport,
        /*
        adapters: {
            attachments: attachmentAdapter,
        },
        */
        onDataStream: ({ type, data }) => {
            if ((type === "data" || type === "data-progress") && onProgressChange) {
                // Data Stream Protocol sends {"type": "data", "value": ...}
                // or {"type": "data-progress", "data": ...}
                // data here is the value
                onProgressChange(data);
            }
        },
        // Performance optimization: throttle UI updates
        experimental_throttle: 50, // 50ms throttling
        onFinish: async (message) => {
            console.log('DEBUG: onFinish message:', message);
            // Notify caller that stream has ended (clear generating state)
            onStreamEnd?.();
            // Sync message state to backend (Sync on Finish)
            try {
                await fetch(`${API_BASE}/sessions/${sessionId}/sync`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        messages: [message],
                    }),
                });
            } catch (error) {
                console.error('Failed to sync message:', error);
            }
        }
    });
}
