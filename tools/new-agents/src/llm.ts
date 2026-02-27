import OpenAI from 'openai';
import { parseLlmStreamChunk } from './utils/llmParser';
import { getSystemPrompt } from './prompts/systemPrompt';
import { useStore, WORKFLOWS, WorkflowType, Attachment } from './store';

/** 将 base64 编码的文本安全解码为 UTF-8 字符串 */
const decodeBase64Text = (base64: string): string => {
  const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
  return new TextDecoder('utf-8').decode(bytes);
};

/** 将附件内容拼接到消息文本中 */
const buildContentWithAttachments = (text: string, attachments?: Attachment[]): string => {
  if (!attachments || attachments.length === 0) return text;
  const attachTxt = attachments
    .map(att => `[附件: ${att.name}]\n${decodeBase64Text(att.data)}`)
    .join('\n\n');
  return `${attachTxt}\n\n${text}`;
};

async function* generateResponseStreamViaProxy(
  messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[],
  modelOverride?: string,
  signal?: AbortSignal
) {
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

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6).trim();
      if (payload === '[DONE]') return;
      try {
        const { content, error } = JSON.parse(payload);
        if (error) throw new Error(error);
        if (content) yield content;
      } catch (e) {
        // Only throw actual parsing error if it looks like a valid structure.
      }
    }
  }
}

export const generateResponseStream = async function* (userMessage: string, attachments?: Attachment[], signal?: AbortSignal) {
  const state = useStore.getState();
  const { isUserConfigured, apiKey, baseUrl, model, workflow, stageIndex, artifactContent, chatHistory } = state;

  const systemInstruction = getSystemPrompt(workflow, stageIndex, artifactContent);

  const messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [
    { role: 'system', content: systemInstruction },
    ...chatHistory.map(msg => ({
      role: (msg.role === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
      content: buildContentWithAttachments(msg.content, msg.attachments),
    })),
    {
      role: 'user' as const,
      content: buildContentWithAttachments(userMessage, attachments),
    }
  ];

  const chunkGenerator = (async function* () {
    if (isUserConfigured && apiKey) {
      // 走现有的前端直连逻辑
      const client = new OpenAI({
        apiKey,
        baseURL: baseUrl || undefined,
        dangerouslyAllowBrowser: true
      });
      const responseStream = await client.chat.completions.create({
        model,
        messages,
        temperature: 0.7,
        stream: true,
      });

      for await (const chunk of responseStream) {
        if (signal?.aborted) throw new Error('Aborted by user');
        const chunkText = chunk.choices[0]?.delta?.content || '';
        if (chunkText) yield chunkText;
      }
    } else {
      // 后端代理直连
      for await (const chunkText of generateResponseStreamViaProxy(messages, model, signal)) {
        if (signal?.aborted) throw new Error('Aborted by user');
        yield chunkText;
      }
    }
  })();

  let fullText = '';
  for await (const chunkText of chunkGenerator) {
    fullText += chunkText;

    const { chatResponse, newArtifact, action, hasArtifactUpdate } = parseLlmStreamChunk(fullText, artifactContent);

    yield { chatResponse, newArtifact, action, hasArtifactUpdate };
  }
};
