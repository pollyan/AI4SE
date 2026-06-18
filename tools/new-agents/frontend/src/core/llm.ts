import { buildSystemPrompt } from './prompts/buildSystemPrompt';
import { useStore, WORKFLOWS, WorkflowType, Attachment, Message } from '../store';

type StreamChunk = {
  chatResponse: string;
  newArtifact: string;
  action: string;
  hasArtifactUpdate: boolean;
  artifactTruncated?: boolean;
};

type AgentArtifactUpdate = {
  type: 'replace' | 'none';
  markdown?: string | null;
};

type AgentStageAction = {
  type: 'request_next_stage';
  target_stage_id: string;
};

type AgentTurnOutput = {
  chat: string;
  artifact_update: AgentArtifactUpdate;
  stage_action?: AgentStageAction | null;
  warnings?: string[];
};

type AgentTurnDeltaOutput = {
  chat?: string | null;
  artifact_update?: AgentArtifactUpdate | null;
  stage_action?: AgentStageAction | null;
  warnings?: string[];
};

type AgentRuntimeEvent =
  | { type: 'run_started' }
  | { type: 'agent_delta'; output: AgentTurnDeltaOutput }
  | { type: 'agent_turn'; output: AgentTurnOutput }
  | { type: 'error'; code: string; message: string };

type AttachmentLike = Partial<Attachment>;
type AttachmentListState =
  | { type: 'valid'; attachments: unknown[] }
  | { type: 'invalid' };

const MAX_SYNTHETIC_STREAM_STEPS = 12;
const SYNTHETIC_STREAM_DELAY_MS = 20;

const LEGACY_PROTOCOL_TAG_PATTERN = /<\s*\/?\s*(?:CHART|ARTIFACT|CHAT)\b[^>]*>/i;

/** 将 base64 编码的文本安全解码为 UTF-8 字符串 */
const decodeBase64Text = (base64: string): string | null => {
  try {
    const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    return new TextDecoder('utf-8').decode(bytes);
  } catch {
    return null;
  }
};

const TEXT_ATTACHMENT_EXTENSIONS = [
  '.txt',
  '.md',
  '.markdown',
  '.json',
  '.csv',
  '.tsv',
  '.xml',
  '.yaml',
  '.yml',
  '.log',
];

const isAttachmentRecord = (attachment: unknown): attachment is AttachmentLike => (
  typeof attachment === 'object' && attachment !== null
);

const normalizeAttachmentList = (attachments: unknown): AttachmentListState => {
  if (attachments === undefined || attachments === null) {
    return { type: 'valid', attachments: [] };
  }
  if (!Array.isArray(attachments)) {
    return { type: 'invalid' };
  }
  return { type: 'valid', attachments };
};

const isTextAttachment = (attachment: AttachmentLike): boolean => {
  const mimeType = (attachment.mimeType || '').toLowerCase();
  if (mimeType.startsWith('text/')) return true;
  if (
    [
      'application/json',
      'application/xml',
      'application/javascript',
      'application/x-yaml',
      'application/yaml',
    ].includes(mimeType)
  ) {
    return true;
  }

  const fileName = (attachment.name || '').toLowerCase();
  return TEXT_ATTACHMENT_EXTENSIONS.some(extension =>
    fileName.endsWith(extension)
  );
};

const formatAttachmentForPrompt = (attachment: unknown): string => {
  if (!isAttachmentRecord(attachment)) {
    return '[附件: 无效附件记录]\n类型: unknown\n内容: 附件记录无效；请根据用户补充信息进行分析。';
  }

  const attachmentName = attachment.name || '未命名附件';
  const header = `[附件: ${attachmentName}]\n类型: ${attachment.mimeType || 'unknown'}`;
  if (isTextAttachment(attachment)) {
    if (typeof attachment.data !== 'string') {
      return `${header}\n内容: 文本附件内容缺失；请根据文件名、MIME 类型和用户补充信息进行分析。`;
    }
    const decodedText = decodeBase64Text(attachment.data);
    if (decodedText !== null) {
      return `${header}\n${decodedText}`;
    }
    return `${header}\n内容: 文本附件内容无法解码；请根据文件名、MIME 类型和用户补充信息进行分析。`;
  }

  return `${header}\n内容: 非文本附件未注入原始二进制内容；请根据文件名、MIME 类型和用户补充信息进行分析。`;
};

/** 将附件内容拼接到消息文本中 */
const buildContentWithAttachments = (text: string, attachments?: unknown): string => {
  const normalized = normalizeAttachmentList(attachments);
  if (normalized.type === 'invalid') {
    return '[附件: 无效附件列表]\n类型: unknown\n内容: 附件列表格式无效；请根据用户补充信息进行分析。'
      + `\n\n${text}`;
  }
  if (normalized.attachments.length === 0) return text;
  const attachTxt = normalized.attachments
    .map(formatAttachmentForPrompt)
    .join('\n\n');
  return `${attachTxt}\n\n${text}`;
};

const areSameAttachments = (
  left?: unknown,
  right?: unknown
): boolean => {
  const leftState = normalizeAttachmentList(left);
  const rightState = normalizeAttachmentList(right);
  if (leftState.type === 'invalid' || rightState.type === 'invalid') {
    return left === right;
  }

  const leftAttachments = leftState.attachments;
  const rightAttachments = rightState.attachments;
  if (leftAttachments.length !== rightAttachments.length) return false;

  return leftAttachments.every((attachment, index) => {
    const other = rightAttachments[index];
    if (!isAttachmentRecord(attachment) || !isAttachmentRecord(other)) {
      return attachment === other;
    }
    return (
      attachment.name === other.name
      && attachment.mimeType === other.mimeType
      && attachment.data === other.data
    );
  });
};

const historyWithoutCurrentUserTurn = (
  chatHistory: Message[],
  userMessage: string,
  attachments?: Attachment[]
): Message[] => {
  const lastMessage = chatHistory[chatHistory.length - 1];
  if (
    lastMessage?.role === 'user'
    && lastMessage.content === userMessage
    && areSameAttachments(lastMessage.attachments, attachments)
  ) {
    return chatHistory.slice(0, -1);
  }

  return chatHistory;
};

const isAssistantControlFeedback = (message: Message): boolean => (
  message.role === 'assistant'
  && /(^|\n)\s*(\*\*Error:\*\*|\*\(已停止生成\)\*|⚠️\s*\*\*模型额度或限流异常\*\*)/.test(
    message.content
  )
);

const buildRuntimePrompt = (
  userMessage: string,
  attachments: Attachment[] | undefined,
  chatHistory: Message[]
): string => {
  const currentUserContent = buildContentWithAttachments(
    userMessage,
    attachments
  );
  if (chatHistory.length === 0) {
    return currentUserContent;
  }

  const priorHistory = historyWithoutCurrentUserTurn(
    chatHistory,
    userMessage,
    attachments
  );
  if (priorHistory.length === 0) {
    return currentUserContent;
  }

  const promptHistory = priorHistory.filter(
    msg => !isAssistantControlFeedback(msg)
  );
  if (promptHistory.length === 0) {
    return currentUserContent;
  }

  const historyText = promptHistory
    .map((msg) => {
      const roleLabel = msg.role === 'user' ? '用户' : '助手';
      return `[${roleLabel}]\n${buildContentWithAttachments(
        msg.content,
        msg.attachments
      )}`;
    })
    .join('\n\n');

  return `${historyText}\n\n[用户]\n${currentUserContent}`;
};

const getStructuredRuntimeStageId = (
  workflow: WorkflowType,
  stageIndex: number
): string => {
  const stage = WORKFLOWS[workflow].stages[stageIndex];
  if (!stage) {
    throw new Error(`当前工作流阶段不存在: ${workflow}/${stageIndex}`);
  }

  return stage.id;
};

const parseAgentRuntimeEvent = (payload: string): AgentRuntimeEvent | null => {
  let parsed: unknown;
  try {
    parsed = JSON.parse(payload);
  } catch (e) {
    throw new Error('结构化智能体 SSE 数据格式错误');
  }

  if (!parsed || typeof parsed !== 'object') {
    throw new Error('结构化智能体 SSE 事件格式错误');
  }

  const event = parsed as Partial<AgentRuntimeEvent>;
  if (event.type === 'error') {
    if (
      !('code' in event)
      || typeof event.code !== 'string'
      || !event.code.trim()
      || !('message' in event)
      || typeof event.message !== 'string'
      || !event.message.trim()
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    return event as AgentRuntimeEvent;
  }

  if (event.type === 'run_started') {
    return event as AgentRuntimeEvent;
  }

  if (event.type === 'agent_delta') {
    if (
      !('output' in event)
      || !event.output
      || typeof event.output !== 'object'
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    const output = event.output as AgentTurnDeltaOutput;
    if (
      output.chat !== undefined
      && output.chat !== null
      && (
        typeof output.chat !== 'string'
        || !output.chat.trim()
        || LEGACY_PROTOCOL_TAG_PATTERN.test(output.chat)
      )
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (
      output.artifact_update !== undefined
      && output.artifact_update !== null
    ) {
      if (
        typeof output.artifact_update !== 'object'
        || !['replace', 'none'].includes(output.artifact_update.type)
      ) {
        throw new Error('结构化智能体 SSE 事件格式错误');
      }
      if (
        output.artifact_update.type === 'replace'
        && (
          typeof output.artifact_update.markdown !== 'string'
          || !output.artifact_update.markdown.trim()
        )
      ) {
        throw new Error('结构化智能体 SSE 事件格式错误');
      }
      if (
        output.artifact_update.type === 'none'
        && output.artifact_update.markdown !== undefined
        && output.artifact_update.markdown !== null
        && (
          typeof output.artifact_update.markdown !== 'string'
          || output.artifact_update.markdown.trim()
        )
      ) {
        throw new Error('结构化智能体 SSE 事件格式错误');
      }
    }
    if (
      output.warnings !== undefined
      && (
        !Array.isArray(output.warnings)
        || output.warnings.some(warning => typeof warning !== 'string')
      )
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (
      output.stage_action !== undefined
      && output.stage_action !== null
    ) {
      if (
        typeof output.stage_action !== 'object'
        || output.stage_action.type !== 'request_next_stage'
        || typeof output.stage_action.target_stage_id !== 'string'
        || !output.stage_action.target_stage_id.trim()
      ) {
        throw new Error('结构化智能体 SSE 事件格式错误');
      }
    }
    return event as AgentRuntimeEvent;
  }

  if (event.type === 'agent_turn') {
    if (
      !('output' in event)
      || !event.output
      || typeof event.output !== 'object'
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    const output = event.output as Partial<AgentTurnOutput>;
    if (typeof output.chat !== 'string' || !output.chat.trim()) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (LEGACY_PROTOCOL_TAG_PATTERN.test(output.chat)) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (
      !output.artifact_update
      || typeof output.artifact_update !== 'object'
      || !['replace', 'none'].includes(output.artifact_update.type)
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (
      output.artifact_update.type === 'replace'
      && (
        typeof output.artifact_update.markdown !== 'string'
        || !output.artifact_update.markdown.trim()
      )
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (
      output.artifact_update.type === 'none'
      && output.artifact_update.markdown !== undefined
      && output.artifact_update.markdown !== null
      && (
        typeof output.artifact_update.markdown !== 'string'
        || output.artifact_update.markdown.trim()
      )
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (
      output.warnings !== undefined
      && (
        !Array.isArray(output.warnings)
        || output.warnings.some(warning => typeof warning !== 'string')
      )
    ) {
      throw new Error('结构化智能体 SSE 事件格式错误');
    }
    if (
      output.stage_action !== undefined
      && output.stage_action !== null
    ) {
      if (
        typeof output.stage_action !== 'object'
        || output.stage_action.type !== 'request_next_stage'
        || typeof output.stage_action.target_stage_id !== 'string'
        || !output.stage_action.target_stage_id.trim()
      ) {
        throw new Error('结构化智能体 SSE 事件格式错误');
      }
    }
    return event as AgentRuntimeEvent;
  }

  throw new Error('结构化智能体 SSE 事件格式错误');
};

const extractMermaidBlocks = (markdown: string): string[] => {
  const blocks: string[] = [];
  const mermaidBlockPattern = /```mermaid(?:[ \t].*)?\n([\s\S]*?)```/gi;
  let match = mermaidBlockPattern.exec(markdown);
  while (match) {
    const diagram = match[1].trim();
    if (diagram) blocks.push(diagram);
    match = mermaidBlockPattern.exec(markdown);
  }
  return blocks;
};

const validateMermaidBlocks = async (markdown: string): Promise<void> => {
  const diagrams = extractMermaidBlocks(markdown);
  if (diagrams.length === 0) return;

  const { default: mermaid } = await import('mermaid');
  for (const diagram of diagrams) {
    try {
      const parseResult = await mermaid.parse(
        diagram,
        { suppressErrors: false }
      );
      if ((parseResult as unknown) === false) {
        throw new Error('mermaid.parse returned false');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Artifact Mermaid parse failed: ${message}`);
    }
  }
};

const splitChatForStreaming = (chat: string): string[] => {
  const trimmed = chat.trim();
  if (!trimmed) return [chat];

  const paragraphs = trimmed
    .split(/\n{2,}/)
    .map(part => part.trim())
    .filter(Boolean);
  const units = paragraphs.length > 1
    ? paragraphs
    : (
      trimmed.match(/[^。！？；.!?]+[。！？；.!?]+|[^。！？；.!?]+$/g)
      || [trimmed]
    ).map(part => part.trim()).filter(Boolean);

  if (units.length <= 1) return [chat];
  if (units.length <= MAX_SYNTHETIC_STREAM_STEPS) return units;

  const grouped: string[] = [];
  const groupSize = Math.ceil(units.length / MAX_SYNTHETIC_STREAM_STEPS);
  for (let index = 0; index < units.length; index += groupSize) {
    grouped.push(units.slice(index, index + groupSize).join('\n\n'));
  }
  return grouped;
};

const splitArtifactForStreaming = (
  artifact: string,
  targetSteps: number
): string[] => {
  const trimmed = artifact.trim();
  if (!trimmed) return [artifact];

  const blocks = trimmed
    .split(/\n{2,}/)
    .map(block => block.trim())
    .filter(Boolean);
  const units = blocks.length > 1 ? blocks : [artifact];
  const maxSteps = Math.max(1, Math.min(MAX_SYNTHETIC_STREAM_STEPS, targetSteps));
  if (units.length <= 1 || maxSteps <= 1) return [artifact];

  const groupSize = Math.ceil(units.length / maxSteps);
  const frames: string[] = [];
  for (let index = 0; index < units.length; index += groupSize) {
    frames.push(units.slice(0, index + groupSize).join('\n\n'));
  }

  frames[frames.length - 1] = artifact;
  return frames;
};

const waitForSyntheticStreamFrame = async (): Promise<void> => {
  await new Promise(resolve => {
    window.setTimeout(resolve, SYNTHETIC_STREAM_DELAY_MS);
  });
};

const hasArtifactTruncationWarning = (warnings?: string[]): boolean => {
  if (!warnings) return false;

  return warnings.some((warning) => {
    const normalized = warning.trim().toLowerCase();
    return (
      normalized === 'artifact_truncated'
      || normalized.includes('truncated')
      || normalized.includes('截断')
      || normalized.includes('不完整')
    );
  });
};

const getHttpErrorMessage = (payload: unknown): string => {
  if (!payload || typeof payload !== 'object') {
    return '结构化智能体请求失败';
  }

  const errorPayload = (payload as { error?: unknown }).error;
  if (typeof errorPayload === 'string' && errorPayload.trim()) {
    return errorPayload;
  }
  if (errorPayload && typeof errorPayload === 'object') {
    const nestedMessage = (errorPayload as { message?: unknown }).message;
    if (typeof nestedMessage === 'string' && nestedMessage.trim()) {
      return nestedMessage;
    }
    const nestedError = (errorPayload as { error?: unknown }).error;
    if (typeof nestedError === 'string' && nestedError.trim()) {
      return nestedError;
    }
  }

  const message = (payload as { message?: unknown }).message;
  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  return '结构化智能体请求失败';
};

const mapAgentTurnToStreamChunks = async function* (
  output: AgentTurnOutput,
  currentArtifact: string,
  expectedNextStageId: string | undefined
): AsyncGenerator<StreamChunk, void, unknown> {
  const hasArtifactUpdate = output.artifact_update.type === 'replace';
  const newArtifact = hasArtifactUpdate
    ? output.artifact_update.markdown || ''
    : currentArtifact;
  const artifactTruncated = hasArtifactTruncationWarning(output.warnings);

  if (
    output.stage_action
    && output.stage_action.target_stage_id !== expectedNextStageId
  ) {
    throw new Error('结构化智能体 SSE 阶段动作目标错误');
  }

  if (hasArtifactUpdate) {
    await validateMermaidBlocks(newArtifact);
  }

  const chatUnits = splitChatForStreaming(output.chat);
  const artifactUnits = hasArtifactUpdate
    ? splitArtifactForStreaming(
      newArtifact,
      chatUnits.length
    )
    : [];
  const frameCount = Math.max(chatUnits.length, artifactUnits.length, 1);
  let accumulatedChat = '';
  for (let index = 0; index < frameCount; index += 1) {
    const isFinalChunk = index === frameCount - 1;
    const chatUnit = chatUnits[Math.min(index, chatUnits.length - 1)];
    if (index < chatUnits.length) {
      accumulatedChat = accumulatedChat
        ? `${accumulatedChat}\n\n${chatUnit}`
        : chatUnit;
    }
    const artifactFrame = hasArtifactUpdate
      ? artifactUnits[Math.min(index, artifactUnits.length - 1)]
      : currentArtifact;

    yield {
      chatResponse: isFinalChunk ? output.chat : accumulatedChat,
      newArtifact: isFinalChunk ? newArtifact : artifactFrame,
      action: isFinalChunk && output.stage_action ? 'NEXT_STAGE' : '',
      hasArtifactUpdate,
      ...(artifactTruncated ? { artifactTruncated: true } : {}),
    };

    if (!isFinalChunk) {
      await waitForSyntheticStreamFrame();
    }
  }
};

const mapAgentTurnToFinalChunk = async function* (
  output: AgentTurnOutput,
  currentArtifact: string,
  expectedNextStageId: string | undefined
): AsyncGenerator<StreamChunk, void, unknown> {
  const hasArtifactUpdate = output.artifact_update.type === 'replace';
  const newArtifact = hasArtifactUpdate
    ? output.artifact_update.markdown || ''
    : currentArtifact;
  const artifactTruncated = hasArtifactTruncationWarning(output.warnings);

  if (
    output.stage_action
    && output.stage_action.target_stage_id !== expectedNextStageId
  ) {
    throw new Error('结构化智能体 SSE 阶段动作目标错误');
  }

  if (hasArtifactUpdate) {
    await validateMermaidBlocks(newArtifact);
  }

  yield {
    chatResponse: output.chat,
    newArtifact,
    action: output.stage_action ? 'NEXT_STAGE' : '',
    hasArtifactUpdate,
    ...(artifactTruncated ? { artifactTruncated: true } : {}),
  };
};

const mapAgentDeltaToStreamChunk = (
  output: AgentTurnDeltaOutput,
  currentArtifact: string
): StreamChunk => {
  const hasArtifactUpdate = output.artifact_update?.type === 'replace';
  const artifactTruncated = hasArtifactTruncationWarning(output.warnings);
  return {
    chatResponse: output.chat || '正在生成...',
    newArtifact: hasArtifactUpdate
      ? output.artifact_update.markdown || ''
      : currentArtifact,
    action: '',
    hasArtifactUpdate,
    ...(artifactTruncated ? { artifactTruncated: true } : {}),
  };
};

async function* generateResponseStreamViaAgentRuntime(
  prompt: string,
  systemPrompt: string,
  workflowId: WorkflowType,
  stageId: string,
  currentArtifact: string,
  expectedNextStageId: string | undefined,
  signal?: AbortSignal
): AsyncGenerator<StreamChunk, void, unknown> {
  const response = await fetch('/new-agents/api/agent/runs/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      systemPrompt,
      workflowId,
      stageId,
    }),
    signal
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(getHttpErrorMessage(err));
  }

  if (!response.body) {
    throw new Error('结构化智能体响应缺少流式内容');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let shouldStop = false;
  let pendingDataLines: string[] = [];
  let receivedAgentDelta = false;

  const processSsePayload = async function* (
    payload: string
  ): AsyncGenerator<StreamChunk, void, unknown> {
    const trimmedPayload = payload.trim();
    if (trimmedPayload === '[DONE]') {
      shouldStop = true;
      return;
    }

    const event = parseAgentRuntimeEvent(trimmedPayload);
    if (!event) return;
    if (event.type === 'error') {
      throw new Error(`${event.code}: ${event.message}`);
    }
    if (event.type === 'run_started') {
      yield {
        chatResponse: '正在生成...',
        newArtifact: currentArtifact,
        action: '',
        hasArtifactUpdate: false,
      };
      return;
    }
    if (event.type === 'agent_delta') {
      receivedAgentDelta = true;
      yield mapAgentDeltaToStreamChunk(event.output, currentArtifact);
      return;
    }
    if (event.type === 'agent_turn') {
      const chunkSource = receivedAgentDelta
        ? mapAgentTurnToFinalChunk(
          event.output,
          currentArtifact,
          expectedNextStageId
        )
        : mapAgentTurnToStreamChunks(
          event.output,
          currentArtifact,
          expectedNextStageId
        );
      for await (const chunk of chunkSource) {
        yield chunk;
      }
    }
  };

  const isCompleteSsePayload = (payload: string): boolean => {
    const trimmedPayload = payload.trim();
    if (!trimmedPayload) return false;
    if (trimmedPayload === '[DONE]') return true;
    try {
      JSON.parse(trimmedPayload);
      return true;
    } catch (e) {
      return false;
    }
  };

  const flushSseEvent = async function* (): AsyncGenerator<StreamChunk, void, unknown> {
    if (pendingDataLines.length === 0) return;
    const payload = pendingDataLines.join('\n');
    pendingDataLines = [];
    for await (const chunk of processSsePayload(payload)) {
      yield chunk;
    }
  };

  const processSseLine = async function* (
    line: string
  ): AsyncGenerator<StreamChunk, void, unknown> {
    if (!line.trim()) {
      for await (const chunk of flushSseEvent()) {
        yield chunk;
      }
      return;
    }
    if (!line.startsWith('data:')) return;
    const data = line.slice(5).trimStart();
    if (
      pendingDataLines.length > 0
      && (
        isCompleteSsePayload(pendingDataLines.join('\n'))
        || data.trim() === '[DONE]'
      )
    ) {
      for await (const chunk of flushSseEvent()) {
        yield chunk;
      }
    }
    pendingDataLines.push(data);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      if (buffer.trim()) {
        for await (const chunk of processSseLine(buffer)) {
          yield chunk;
        }
      }
      for await (const chunk of flushSseEvent()) {
        yield chunk;
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      for await (const chunk of processSseLine(line)) {
        yield chunk;
      }
      if (shouldStop) return;
    }
  }
}

export const generateResponseStream = async function* (userMessage: string, attachments?: Attachment[], signal?: AbortSignal): AsyncGenerator<StreamChunk, void, unknown> {
  const state = useStore.getState();
  const { workflow, stageIndex, artifactContent, chatHistory, stageArtifacts } = state;

  const agentId = WORKFLOWS[workflow].agentId;
  const systemInstruction = buildSystemPrompt({
    agentId,
    workflow,
    stageIndex,
    currentArtifact: artifactContent,
    stageArtifacts
  });

  const currentStageId = getStructuredRuntimeStageId(workflow, stageIndex);
  const expectedNextStageId = WORKFLOWS[workflow].stages[stageIndex + 1]?.id;
  const prompt = buildRuntimePrompt(
    userMessage,
    attachments,
    chatHistory
  );

  for await (const chunk of generateResponseStreamViaAgentRuntime(
    prompt,
    systemInstruction,
    workflow,
    currentStageId,
    artifactContent,
    expectedNextStageId,
    signal
  )) {
    if (signal?.aborted) throw new Error('Aborted by user');
    yield chunk;
  }
};
