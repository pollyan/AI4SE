import OpenAI from 'openai';
import { useStore } from '../../store';

/**
 * 通过后端的 /api/chat/stream 接口发起的 SSE 代理请求
 * 并将 stream chunk 拼接成完整字符串返回
 */
async function collectResponseViaProxy(
    messages: OpenAI.Chat.ChatCompletionMessageParam[],
    modelOverride?: string,
    signal?: AbortSignal
): Promise<string> {
    const response = await fetch('/new-agents/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages, model: modelOverride, temperature: 0.7 }),
        signal
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || '后端代理请求失败');
    }

    if (!response.body) {
        throw new Error('No proxy response body');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullResponse = '';

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const payload = line.slice(6).trim();
                if (payload === '[DONE]') return fullResponse;

                let parsed;
                try {
                    parsed = JSON.parse(payload);
                } catch (e) {
                    console.error("[llmClient] Parse SSE data error:", e, payload);
                    // Incomplete JSON chunk, skip and append to fullResponse next time
                    continue;
                }

                if (parsed.error) throw new Error(parsed.error);
                if (parsed.response) {
                    fullResponse += parsed.response;
                }
            }
        }
    } catch (e) {
        console.error("[llmClient] Proxy stream collection failed:", e);
        return '';
    }

    return fullResponse;
}

/**
 * 发送 LLM 请求，封装双路径收集
 */
export async function collectLlmResponse(
    messages: OpenAI.Chat.ChatCompletionMessageParam[],
    modelOverride?: string,
    signal?: AbortSignal
): Promise<string> {
    const state = useStore.getState();
    const { isUserConfigured, apiKey, baseUrl, model } = state;
    let currentModel = modelOverride || model;

    if (isUserConfigured && apiKey) {
        // 前端直连
        try {
            const client = new OpenAI({
                apiKey,
                baseURL: baseUrl || undefined,
                dangerouslyAllowBrowser: true
            });

            const responseStream = await client.chat.completions.create({
                model: currentModel || 'gpt-3.5-turbo',
                messages,
                temperature: 0.7,
                stream: true,
            }, { signal });

            let fullText = '';
            for await (const chunk of responseStream) {
                if (signal?.aborted) throw new Error('Aborted by user');
                const chunkText = chunk.choices[0]?.delta?.content || '';
                if (chunkText) {
                    fullText += chunkText;
                }
            }
            return fullText;
        } catch (e) {
            console.error("[llmClient] OpenAI stream collection failed:", e);
            return '';
        }
    } else {
        // 后端代理
        return collectResponseViaProxy(messages, currentModel, signal);
    }
}
