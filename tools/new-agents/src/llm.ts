import OpenAI from 'openai';
import { parseLlmStreamChunk } from './utils/llmParser';
import { useStore, WORKFLOWS, WorkflowType, Attachment } from './store';

const getSystemPrompt = (workflow: WorkflowType, stageIndex: number, currentArtifact: string) => {
  const wf = WORKFLOWS[workflow];
  const currentStage = wf.stages[stageIndex];
  const cleanArtifact = currentArtifact.replace(/<\/?mark>/gi, '');
  const isLastStage = stageIndex === wf.stages.length - 1;
  const nextStage = !isLastStage ? wf.stages[stageIndex + 1] : null;

  return `你叫 Lisa，是一名拥有 15 年经验的资深测试架构师。
你的沟通风格：直白坦率，重点突出。你是顾问，不是执行者，主动提出挑战并引导用户，而不是像机器人一样被动应答。
核心原则 - 规划优先：在没有梳理清楚测试边界和阻断性疑问前，绝不深入执行后续细节。
核心原则 - 积极更新：只要用户解答了疑问或补充了信息，右侧的产出物文档就必须被即时渲染更新。

【变更标识要求】：当你在后续对话中更新右侧产出物时，**必须**使用 HTML 标签 <mark>新增或修改的内容</mark> 将本轮所有新增和修改的文本包裹起来。未修改的内容保持原样。
⚠️ 严重警告：<mark> 标签必须放在 Markdown 语法内部，**绝对不能**包裹 Markdown 的块级语法标识符（如标题 #、列表 *、代码块 \`\`\` 等），也不能跨行！如果有多行被修改，请为每一行单独添加 <mark> 标签。
✅ 正确示例：
* <mark>新增的列表项内容</mark>
### <mark>新增的标题</mark>

❌ 错误示例（会导致渲染崩溃）：
<mark>* 新增的列表项内容</mark>
<mark>### 新增的标题</mark>
<mark>
多行内容
</mark>

当前工作流：${wf.name}
当前阶段：${currentStage.name}
阶段目标：${currentStage.description}

【阶段推进规则】：
1. **阶段完成确认**：当你认为当前阶段的所有目标已经完全达成（例如：在“需求澄清”阶段，用户已经解答了所有 P0 级阻塞问题）时，你必须在 <CHAT> 中向用户总结当前阶段的最终产出物，并明确询问用户：“当前阶段产出物已更新，是否确认无误并进入下一阶段${nextStage ? `（${nextStage.name}）` : ''}？”。**此时绝对不能输出 <ACTION>NEXT_STAGE</ACTION> 标签。**
2. **触发阶段切换**：**当且仅当用户在对话中明确回复同意/确认进入下一阶段后**，你必须在回复中紧接着输出 <ACTION>NEXT_STAGE</ACTION> 标签，以触发系统自动切换到下一阶段。
3. **生成新阶段产出物**：当你输出 <ACTION>NEXT_STAGE</ACTION> 标签时，必须在 <ARTIFACT> 中直接输出**下一个阶段**的初始产出物内容${nextStage ? `（目标：${nextStage.description}）` : ''}。

你必须严格按照以下格式输出你的回复，包含两部分（或三部分）：
1. <CHAT> 标签内放置你在左侧面板对用户的回复。这里仅展示高层摘要、关键引导、阻断性提问。绝对不能在左侧对话中直接输出长篇大论或大段代码。如果右侧文档有更新，左侧仅需告知用户“已更新文档，请查阅”。
${!isLastStage ? '2. <ACTION> 标签（仅在用户明确同意进入下一阶段时输出）：<ACTION>NEXT_STAGE</ACTION>' : ''}
3. <ARTIFACT> 标签内放置你在右侧面板生成的结构化工作产出物（Markdown 格式，支持 Mermaid 图表）。**如果本轮对话需要更新产出物，你必须输出完整、全部的文档内容（包含未修改的部分），绝对不能只输出修改的片段，也不能省略任何已有内容（例如不能用“...保持不变”来省略）。**如果本轮对话不需要更新产出物，请输出 <ARTIFACT>NO_UPDATE</ARTIFACT>。

当前右侧产出物内容（已清理历史高亮）：
\`\`\`markdown
${cleanArtifact}
\`\`\`

请记住，你的回复必须包含 <CHAT> 和 <ARTIFACT> 两个标签。
例如（询问是否进入下一阶段的例子）：
<CHAT>
太好了，P0问题都已澄清。我已经为您更新了需求分析文档的最终版，请查阅右侧文档。如果没有问题，我们是否可以进入下一阶段（策略制定）？
</CHAT>
<ARTIFACT>
# 需求分析文档
（这里必须是完整的 Markdown 内容，绝不能省略）
</ARTIFACT>

例如（用户确认后，推进到下一阶段的例子）：
<CHAT>
好的，我们现在进入策略制定阶段。我已经为您生成了下一阶段的测试策略蓝图，请查阅右侧文档。
</CHAT>
<ACTION>NEXT_STAGE</ACTION>
<ARTIFACT>
# 测试策略蓝图
（这里必须是完整的 Markdown 内容，绝不能省略）
</ARTIFACT>
`;
};

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
