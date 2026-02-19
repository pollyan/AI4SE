/**
 * Backend Service for AI Agents
 * Communicates with Flask backend API using SSE for streaming responses.
 */

// API base URL - in development, Vite proxy will forward to Flask backend
const API_BASE = '/ai-agents/api/requirements';

interface CreateSessionResponse {
    id: string;
    project_name: string;
    session_status: string;
    current_stage: string;
    assistant_type?: string;
}

interface SessionData {
    sessionId: string;
    assistantType: string;
}

/**
 * Creates a new chat session with the backend
 */
export async function createSession(
    projectName: string,
    assistantType: string
): Promise<SessionData> {
    const response = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            project_name: projectName,
            assistant_type: assistantType,
        }),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to create session');
    }

    const result = await response.json();
    const sessionData: CreateSessionResponse = result.data;

    return {
        sessionId: sessionData.id,
        assistantType: assistantType,
    };
}

/**
 * Artifact template item from backend
 */
export interface ArtifactTemplateItem {
    stageId: string;
    artifactKey: string;
    name: string;
}

/**
 * Artifact progress info from state events
 */
export interface ArtifactProgress {
    template: ArtifactTemplateItem[];
    completed: string[];          // 已完成的 artifact keys
    generating: string | null;    // 正在生成的 artifact key
}

/**
 * Progress info from state events
 */
export interface ProgressInfo {
    stages: { id: string; name: string; status: 'pending' | 'active' | 'completed' }[];
    currentStageIndex: number;
    currentTask: string | null;
    artifactProgress?: ArtifactProgress | null;
    artifacts?: Record<string, string>;
    structured_artifacts?: Record<string, any>;
}

/**
 * Sends a message to the backend and streams the response via SSE.
 * The backend returns text/event-stream with format: data: {"type": "content", "chunk": "..."}
 */
export async function sendMessageStream(
    sessionId: string,
    message: string,
    onChunk: (fullText: string) => void,
    onStateChange?: (progress: ProgressInfo) => void,
    onStreamEnd?: () => void
): Promise<string> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages/stream`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content: message,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Stream request failed' }));
        throw new Error(error.message || 'Failed to send message');
    }

    if (!response.body) {
        throw new Error('Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let buffer = '';

    // Regex patterns to clean system tags from chat display
    const patterns = [
        /```json[\s\S]*?```/g,
        /<plan>[\s\S]*?<\/plan>/g,
        /<update_status[^>]*>[\s\S]*?<\/update_status>/g,
        /<artifact_template\s+[^>]*>/g,
        /<artifact\s+key="[^"]*">[\s\S]*?<\/artifact>/g
    ];

    const cleanText = (text: string): string => {
        let cleaned = text;
        patterns.forEach(pattern => {
            cleaned = cleaned.replace(pattern, '');
        });
        return cleaned;
    };

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE format: lines starting with "data: "
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr) continue;

                    try {
                        const data = JSON.parse(jsonStr);

                        if (data.type === 'content' && data.chunk) {
                            fullText += data.chunk;
                            // Clean text before sending to UI
                            const cleanedText = cleanText(fullText);
                            onChunk(cleanedText);
                        } else if (data.type === 'state' && data.progress && onStateChange) {
                            // Handle state events for workflow progress
                            onStateChange(data.progress);
                        } else if (data.type === 'done') {
                            // Stream completed - notify caller to clear generating state
                            onStreamEnd?.();
                            const finalCleaned = cleanText(fullText);
                            return finalCleaned;
                        } else if (data.type === 'error') {
                            throw new Error(data.message || 'Stream error from server');
                        }
                    } catch (parseError) {
                        console.warn('Failed to parse SSE data:', jsonStr, parseError);
                    }
                }
            }
        }
    } finally {
        reader.releaseLock();
    }

    return cleanText(fullText);
}

/**
 * Fallback: Non-streaming message send (for simple interactions or when SSE fails)
 */
export async function sendMessage(
    sessionId: string,
    message: string
): Promise<string> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content: message,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Request failed' }));
        throw new Error(error.message || 'Failed to send message');
    }

    const result = await response.json();
    return result.data?.ai_message?.content || '';
}
