import { useMemo } from 'react';
import { useChatRuntime as useAISdkChatRuntime, AssistantChatTransport } from "@assistant-ui/react-ai-sdk";
import { AssistantId } from "../types";

const API_BASE = '/ai-agents/api/requirements';

export function useChatRuntime(sessionId: string, assistantType: AssistantId, onProgressChange?: (progress: any) => void) {
  const api = `${API_BASE}/sessions/${sessionId}/messages/v2/stream`;
  
  const transport = useMemo(() => new AssistantChatTransport({
    api,
    url: api,
    baseUrl: api,
    headers: {
      'X-Assistant-Type': assistantType,
    },
  }), [api, assistantType]);

  return useAISdkChatRuntime({
    transport,
    onDataStream: ({ type, data }) => {
        if (type === "data" && onProgressChange) {
            // Data Stream Protocol sends {"type": "data", "value": ...}
            // data here is the value
            onProgressChange(data);
        }
    },
    // Performance optimization: throttle UI updates
    experimental_throttle: 50, // 50ms throttling
    onFinish: async (message) => {
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
