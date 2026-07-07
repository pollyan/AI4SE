import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore, WORKFLOWS } from '../store';
import { Send, PlusCircle, Bot, User, FileText, X, Square, RefreshCw, Copy, Check, ChevronRight, ChevronDown, ArrowRight, AlertTriangle, Settings } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { clsx } from 'clsx';
import { useChatService } from '../services/chatService';
import { getAgentById } from '../core/config/agents';
import { preprocessMarkdown, replaceMermaidBlockAtIndex } from '../core/utils/markdownUtils';
import { createMarkdownCodeRenderer } from './markdownCodeRenderer';
import {
  fetchTargetWorkflowHandoffCandidates,
  fetchWorkflowHandoffs,
  startWorkflowHandoff,
} from '../services/workflowHandoffService';
import type { Attachment, Message, MessageErrorDiagnosticKind, WorkflowHandoff, WorkflowType } from '../store';

const asRenderableAttachments = (attachments: unknown): Attachment[] => {
  if (!Array.isArray(attachments)) return [];

  return attachments.flatMap((attachment): Attachment[] => {
    if (
      typeof attachment !== 'object'
      || attachment === null
      || typeof attachment.name !== 'string'
      || typeof attachment.data !== 'string'
      || typeof attachment.mimeType !== 'string'
    ) {
      return [];
    }
    return [{
      name: attachment.name,
      data: attachment.data,
      mimeType: attachment.mimeType,
    }];
  });
};

const isStructuredOutputFailureContent = (content: string | undefined): boolean => (
  Boolean(content?.includes('结构化输出生成失败'))
);

const isProviderFailureContent = (content: string | undefined): boolean => (
  Boolean(content?.includes('模型配置或供应商异常') || content?.includes('模型调用未完成'))
);

const isStructuredOutputFailureMessage = (message: Message | undefined): boolean => (
  Boolean(
    message?.role === 'assistant'
    && (
      message.errorDiagnostic?.kind === 'structured'
      || isStructuredOutputFailureContent(message.content)
    )
  )
);

const isProviderFailureMessage = (message: Message | undefined): boolean => (
  Boolean(
    message?.role === 'assistant'
    && (
      message.errorDiagnostic?.kind === 'provider'
      || isProviderFailureContent(message.content)
    )
  )
);

const getMessageContentWithoutDiagnosticSummary = (message: Message): string => {
  if (!message.errorDiagnostic) return message.content;

  const summaryLine = `⚠️ ${message.errorDiagnostic.summary}`;
  if (!message.content.endsWith(summaryLine)) return message.content;
  return message.content.slice(0, -summaryLine.length).trim();
};

const ERROR_CARD_STYLE = {
  structured: {
    container: 'border-amber-500/25 bg-amber-500/10 text-amber-100',
    icon: 'text-amber-300',
    detail: 'border-amber-300/20 bg-amber-950/25 text-amber-50/85',
    secondaryButton: 'border-amber-300/30 bg-amber-300/10 text-amber-100 hover:bg-amber-300/20',
    primaryButton: 'bg-amber-500 text-slate-950 hover:bg-amber-400',
  },
  provider: {
    container: 'border-rose-500/25 bg-rose-500/10 text-rose-100',
    icon: 'text-rose-300',
    detail: 'border-rose-300/20 bg-rose-950/25 text-rose-50/85',
    secondaryButton: 'border-rose-300/30 bg-rose-300/10 text-rose-100 hover:bg-rose-300/20',
    primaryButton: 'bg-rose-500 text-white hover:bg-rose-400',
  },
  generic: {
    container: 'border-sky-500/25 bg-sky-500/10 text-sky-100',
    icon: 'text-sky-300',
    detail: 'border-sky-300/20 bg-sky-950/25 text-sky-50/85',
    secondaryButton: 'border-sky-300/30 bg-sky-300/10 text-sky-100 hover:bg-sky-300/20',
    primaryButton: 'bg-sky-500 text-white hover:bg-sky-400',
  },
} as const;

const getDiagnosticTitle = (kind: MessageErrorDiagnosticKind): string => (
  kind === 'structured'
    ? '结构化结果未更新'
    : kind === 'provider'
      ? '模型调用未完成'
      : '本轮生成失败'
);

const STRUCTURED_FAILURE_SUPPLEMENT_PROMPT = '请补充更明确的需求或阶段确认信息，我会基于补充内容重新生成当前阶段产出物。';

const TARGET_STARTUP_HANDOFF_COPY: Partial<Record<WorkflowType, {
  title: string;
  description: string;
  loading: string;
  empty: string;
}>> = {
  VALUE_DISCOVERY: {
    title: '选择需求蓝图起点',
    description: '可以从空白话题开始，也可以继承已有产品概念简报继续梳理。',
    loading: '正在查找可继承的产品概念简报...',
    empty: '暂无可继承的产品概念简报，可以直接开启新话题',
  },
  USER_STORY_BREAKDOWN: {
    title: '选择用户故事拆解起点',
    description: '可以从空白话题开始，也可以继承已有需求蓝图继续拆分。',
    loading: '正在查找可继承的需求蓝图...',
    empty: '暂无可继承的需求蓝图，可以直接开启新话题',
  },
};

type ProviderCheckState = {
  status: 'idle' | 'checking' | 'success' | 'error';
  message: string | null;
};

type ProviderCheckStateByMessage = Record<string, ProviderCheckState>;

export const ChatPane: React.FC = () => {
  const navigate = useNavigate();
  // 使用选择器订阅特定状态，减少不必要的重渲染 (rerender-defer-reads)
  const chatHistory = useStore((state) => state.chatHistory);
  const isGenerating = useStore((state) => state.isGenerating);
  const workflow = useStore((state) => state.workflow);
  const stageIndex = useStore((state) => state.stageIndex);
  const currentRunId = useStore((state) => state.currentRunId);
  const pendingStageTransition = useStore((state) => state.pendingStageTransition);
  const clearPendingStageTransition = useStore((state) => state.clearPendingStageTransition);
  const applyWorkflowHandoff = useStore((state) => state.applyWorkflowHandoff);
  const setSettingsOpen = useStore((state) => state.setSettingsOpen);
  
  const onboardingConfig = WORKFLOWS[workflow].onboarding;
  const workflowStages = WORKFLOWS[workflow].stages;
  const currentStageId = workflowStages[stageIndex]?.id;
  const agentId = WORKFLOWS[workflow].agentId;
  const agentConfig = getAgentById(agentId);
  const displayTitle = agentConfig?.displayTitle || agentId;
  const agentName = agentConfig?.name || 'AI';
  const pendingNextStage = pendingStageTransition
    ? workflowStages[pendingStageTransition.toStageIndex]
    : null;
  const latestMessage = chatHistory[chatHistory.length - 1];
  const isLatestStructuredOutputFailure = isStructuredOutputFailureMessage(latestMessage);
  const isLatestProviderFailure = isProviderFailureMessage(latestMessage);
  const latestAssistantMessages = chatHistory
    .filter((message) => message.role === 'assistant')
    .slice(-2);
  const hasRepeatedStructuredOutputFailures = (
    latestAssistantMessages.length === 2
    && latestAssistantMessages.every((message) => (
      isStructuredOutputFailureMessage(message)
    ))
  );
  const updateMessage = useStore((state) => state.updateMessage);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const copyFeedbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [workflowHandoffs, setWorkflowHandoffs] = useState<WorkflowHandoff[]>([]);
  const [targetWorkflowHandoffs, setTargetWorkflowHandoffs] = useState<WorkflowHandoff[]>([]);
  const [targetHandoffStatus, setTargetHandoffStatus] = useState<'idle' | 'loading' | 'ready' | 'empty' | 'error'>('idle');
  const [targetHandoffPanelDismissed, setTargetHandoffPanelDismissed] = useState(false);
  const [providerCheckByMessageId, setProviderCheckByMessageId] = useState<ProviderCheckStateByMessage>({});
  const [expandedErrorDetails, setExpandedErrorDetails] = useState<Record<string, boolean>>({});

  const toggleErrorDetail = (messageId: string) => {
    setExpandedErrorDetails(current => ({
      ...current,
      [messageId]: !current[messageId],
    }));
  };

  const handleCopy = async (content: string, msgId: string) => {
    if (copyFeedbackTimeoutRef.current) {
      clearTimeout(copyFeedbackTimeoutRef.current);
      copyFeedbackTimeoutRef.current = null;
    }

    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(msgId);
      setToast('已复制到剪贴板');
    } catch {
      setCopiedId(null);
      setToast('复制失败');
    }
    copyFeedbackTimeoutRef.current = setTimeout(() => {
      setCopiedId(null);
      setToast(null);
      copyFeedbackTimeoutRef.current = null;
    }, 2000);
  };

  const handleProviderConfigCheck = async (messageId: string) => {
    setProviderCheckByMessageId(current => ({
      ...current,
      [messageId]: { status: 'checking', message: '正在检测模型连接...' },
    }));

    try {
      const response = await fetch('/new-agents/api/config/check', {
        method: 'POST',
      });
      let data: { ok?: boolean; message?: unknown; error?: unknown } = {};
      try {
        data = await response.json();
      } catch {
        data = {};
      }

      const message = typeof data.message === 'string' && data.message.trim()
        ? data.message
        : typeof data.error === 'string' && data.error.trim()
          ? data.error
          : response.ok && data.ok !== false
            ? '模型配置可用'
            : '模型连接检测失败';
      setProviderCheckByMessageId(current => ({
        ...current,
        [messageId]: {
          status: response.ok && data.ok !== false ? 'success' : 'error',
          message,
        },
      }));
    } catch {
      setProviderCheckByMessageId(current => ({
        ...current,
        [messageId]: {
          status: 'error',
          message: '无法完成连接检测，请检查网络或稍后重试。',
        },
      }));
    }
  };

  useEffect(() => () => {
    if (copyFeedbackTimeoutRef.current) {
      clearTimeout(copyFeedbackTimeoutRef.current);
    }
  }, []);

  useEffect(() => {
    let isCurrent = true;

    if (!currentRunId) {
      setWorkflowHandoffs([]);
      return () => {
        isCurrent = false;
      };
    }

    fetchWorkflowHandoffs(currentRunId)
      .then((handoffs) => {
        if (isCurrent) {
          setWorkflowHandoffs(handoffs);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setWorkflowHandoffs([]);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [currentRunId, chatHistory.length]);

  useEffect(() => {
    setTargetHandoffPanelDismissed(false);
  }, [workflow, currentStageId]);

  const targetStartupHandoffCopy = TARGET_STARTUP_HANDOFF_COPY[workflow];
  const shouldOfferTargetStartupHandoff = Boolean(
    targetStartupHandoffCopy
    && currentStageId === WORKFLOWS[workflow].stages[0]?.id
    && !currentRunId
    && chatHistory.length === 0
  );

  useEffect(() => {
    let isCurrent = true;

    if (!shouldOfferTargetStartupHandoff || !currentStageId || targetHandoffPanelDismissed) {
      setTargetWorkflowHandoffs([]);
      setTargetHandoffStatus('idle');
      return () => {
        isCurrent = false;
      };
    }

    setTargetHandoffStatus('loading');
    fetchTargetWorkflowHandoffCandidates(workflow, currentStageId)
      .then((handoffs) => {
        if (!isCurrent) return;
        setTargetWorkflowHandoffs(handoffs);
        setTargetHandoffStatus(handoffs.length > 0 ? 'ready' : 'empty');
      })
      .catch(() => {
        if (!isCurrent) return;
        setTargetWorkflowHandoffs([]);
        setTargetHandoffStatus('error');
      });

    return () => {
      isCurrent = false;
    };
  }, [chatHistory.length, currentRunId, currentStageId, shouldOfferTargetStartupHandoff, targetHandoffPanelDismissed, workflow]);

  const handleApplyWorkflowHandoff = async (handoff: WorkflowHandoff) => {
    const sourceRunId = currentRunId ?? handoff.sourceRunId;
    if (!sourceRunId) {
      setToast('无法启动接力：缺少上游 run');
      return;
    }
    const startedHandoff = sourceRunId
      ? await startWorkflowHandoff(sourceRunId, handoff.id)
      : handoff;
    applyWorkflowHandoff(startedHandoff);
    setWorkflowHandoffs([]);
    setTargetWorkflowHandoffs([]);
    setTargetHandoffPanelDismissed(true);
    const targetWorkflow = WORKFLOWS[startedHandoff.targetWorkflowId];
    const targetRunQuery = startedHandoff.targetRunId
      ? `?runId=${encodeURIComponent(startedHandoff.targetRunId)}`
      : '';
    navigate(`/workspace/${startedHandoff.targetAgentId}/${targetWorkflow.slug}${targetRunQuery}`);
  };

  const {
    input,
    setInput,
    pendingAttachments,
    handleSend,
    handleConfirmStageTransition,
    handleRetry,
    handleRetryCurrentStageGeneration,
    handleStop,
    handleFileChange,
    removeAttachment
  } = useChatService();

  const handleChatMermaidRetry = useCallback(async (msgId: string, brokenCode: string, errorMessage: string, blockIndex: number) => {
    // dynamically import to avoid cyclic or immediate heavy deps
    const { retryMermaidGeneration } = await import('../services/mermaidRetryService');
    const newCode = await retryMermaidGeneration(brokenCode, errorMessage, blockIndex);
    if (!newCode) return false;

    // Use regex to locate nth mermaid block
    const history = useStore.getState().chatHistory;
    const msg = history.find(m => m.id === msgId);
    if (!msg || !msg.content) return false;

    const updatedContent = replaceMermaidBlockAtIndex(msg.content, blockIndex, newCode);
    if (!updatedContent) return false;

    useStore.getState().updateMessage(msgId, updatedContent);
    return true;
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory, isGenerating, pendingAttachments]);

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileChange(e.target.files);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSupplementStructuredFailure = () => {
    setInput(STRUCTURED_FAILURE_SUPPLEMENT_PROMPT);
    textareaRef.current?.focus();
  };

  const renderablePendingAttachments = asRenderableAttachments(pendingAttachments);

  return (
    <section className="flex flex-col w-full lg:w-[40%] min-w-[360px] bg-[#0B1120] border-r border-[#1e293b] relative shadow-[10px_0_30px_-10px_rgba(0,0,0,0.5)] z-20 h-full">
      <div className="px-5 py-4 border-b border-[#1e293b] bg-[#0B1120]/95 backdrop-blur sticky top-0 z-10">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-white text-base font-bold flex items-center gap-2">
            <Bot className="w-5 h-5 text-blue-500" />
            {WORKFLOWS[workflow].name}
          </h3>
          <span className="text-[10px] uppercase tracking-wider text-cyan-400 font-mono border border-cyan-400/20 bg-cyan-400/10 px-2 py-0.5 rounded-full">Active</span>
        </div>
        <p className="text-slate-400 text-xs truncate">{displayTitle} 正在为您服务</p>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
        {workflowHandoffs.length > 0 && !isGenerating && (
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-3 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-semibold text-cyan-100">跨智能体接力</p>
                <p className="mt-0.5 truncate text-[11px] text-cyan-200/70">
                  当前产出物可以作为下游工作流输入
                </p>
              </div>
              <div className="flex shrink-0 flex-wrap justify-end gap-2">
                {workflowHandoffs.map((handoff) => (
                  <button
                    key={handoff.id}
                    onClick={() => handleApplyWorkflowHandoff(handoff)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-cyan-400/20 bg-cyan-400/10 px-3 py-1.5 text-xs font-semibold text-cyan-100 transition-colors hover:border-cyan-300/40 hover:bg-cyan-400/20"
                    title={handoff.label}
                  >
                    <span>{handoff.label}</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {chatHistory.length === 0 && (
          <div className="flex flex-col h-full items-center justify-center space-y-8 animate-fade-in-up pb-10">
            <div className="text-center space-y-4 max-w-xl px-4 flex flex-col items-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-3xl bg-blue-500/10 border border-blue-500/20 text-blue-500 shadow-[0_0_30px_-5px_rgba(59,130,246,0.3)] mb-2 mt-4">
                <Bot className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-white tracking-wide">
                {WORKFLOWS[workflow].name}
              </h2>
              <div className="text-sm text-slate-300 leading-relaxed bg-[#151e32] p-5 rounded-2xl border border-[#1e293b] shadow-sm text-left w-full mt-2">
                <ReactMarkdown
                  components={{
                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                    strong: ({ node, ...props }) => <strong className="text-blue-400 font-bold" {...props} />,
                  }}
                >
                  {preprocessMarkdown(onboardingConfig.welcomeMessage)}
                </ReactMarkdown>
              </div>
            </div>

            {shouldOfferTargetStartupHandoff && !targetHandoffPanelDismissed && (
              <div className="w-full max-w-xl px-4">
                <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-cyan-100">{targetStartupHandoffCopy?.title}</p>
                      <p className="mt-1 text-xs leading-relaxed text-cyan-100/70">
                        {targetStartupHandoffCopy?.description}
                      </p>
                    </div>
                    <button
                      onClick={() => setTargetHandoffPanelDismissed(true)}
                      className="shrink-0 rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-3 py-1.5 text-xs font-semibold text-cyan-50 transition-colors hover:bg-cyan-300/20"
                    >
                      开启新话题
                    </button>
                  </div>

                  {targetHandoffStatus === 'loading' && (
                    <p className="mt-3 text-xs text-cyan-100/70">{targetStartupHandoffCopy?.loading}</p>
                  )}

                  {targetHandoffStatus === 'error' && (
                    <p className="mt-3 text-xs text-amber-100">暂时无法读取上游内容，可以直接开启新话题。</p>
                  )}

                  {targetHandoffStatus === 'empty' && (
                    <p className="mt-3 text-xs text-cyan-100/70">{targetStartupHandoffCopy?.empty}</p>
                  )}

                  {targetWorkflowHandoffs.length > 0 && (
                    <div className="mt-3 grid grid-cols-1 gap-2">
                      {targetWorkflowHandoffs.map((handoff) => (
                        <button
                          key={`${handoff.sourceRunId ?? 'source'}-${handoff.id}-v${handoff.sourceArtifactVersion}`}
                          onClick={() => handleApplyWorkflowHandoff(handoff)}
                          className="text-left rounded-lg border border-cyan-300/20 bg-[#0f1623]/80 p-3 text-cyan-50 transition-colors hover:border-cyan-200/40 hover:bg-cyan-400/10"
                          title={handoff.sourceArtifactDigest}
                        >
                          <span className="flex items-center justify-between gap-2 text-sm font-semibold">
                            <span>{handoff.label}</span>
                            <ArrowRight className="h-4 w-4 shrink-0" />
                          </span>
                          <span className="mt-1 block text-[11px] text-cyan-100/60">
                            {handoff.sourceWorkflowId}/{handoff.sourceStageId} · v{handoff.sourceArtifactVersion}
                          </span>
                          {handoff.sourceArtifactSummary && (
                            <span className="mt-1.5 block line-clamp-2 text-xs leading-relaxed text-slate-300">
                              {handoff.sourceArtifactSummary}
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="flex flex-col gap-3 w-full max-w-xl px-4">
              <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold px-2 mb-1">你可以试试这样问：</p>
              <div className="grid grid-cols-1 gap-2.5">
                {onboardingConfig.starterPrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(prompt, { useDraftAttachments: false })}
                    className="text-left text-sm text-slate-300 bg-[#0f1623] hover:bg-[#1e293b] border border-[#1e293b] hover:border-blue-500/30 p-3.5 rounded-xl transition-all shadow-sm hover:shadow-md group flex items-start gap-3"
                  >
                    <span className="mt-0.5 text-blue-500/50 group-hover:text-blue-400 transition-colors">✦</span>
                    <span className="leading-snug">{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {chatHistory.map((msg) => {
          // Hide the empty assistant bubble that gets created initially before text arrives
          if (isGenerating && msg.role === 'assistant' && !msg.content?.trim() && msg.id === chatHistory[chatHistory.length - 1]?.id) {
            return null;
          }
          const messageAttachments = asRenderableAttachments(msg.attachments);
          const isStructuredOutputFailure = isStructuredOutputFailureMessage(msg);
          const isProviderFailure = isProviderFailureMessage(msg);
          const isDiagnosticFailure = Boolean(msg.errorDiagnostic);
          const shouldShowSupplementStructuredFailure = (
            isStructuredOutputFailure
            && hasRepeatedStructuredOutputFailures
            && msg.id === latestMessage?.id
          );
          const visibleMessageContent = getMessageContentWithoutDiagnosticSummary(msg);
          const isErrorDetailExpanded = expandedErrorDetails[msg.id] === true;
          const diagnosticStyle = msg.errorDiagnostic
            ? ERROR_CARD_STYLE[msg.errorDiagnostic.kind]
            : null;
          const providerCheck = providerCheckByMessageId[msg.id] || {
            status: 'idle',
            message: null,
          };
          let mermaidBlockCounter = 0;
          const headingClassName = msg.role === 'user' ? "text-white" : "text-slate-100";
          const messageMarkdownComponents: Components = {
            h1: ({ node, ...props }) => <h1 className={`text-base font-bold mb-2 ${headingClassName}`} {...props} />,
            h2: ({ node, ...props }) => <h2 className={`text-sm font-bold mt-3 mb-2 ${headingClassName}`} {...props} />,
            h3: ({ node, ...props }) => <h3 className={`text-sm font-semibold mt-3 mb-1.5 ${headingClassName}`} {...props} />,
            p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
            ul: ({ node, ...props }) => <ul className="list-disc pl-5 my-2 space-y-1.5" {...props} />,
            ol: ({ node, ...props }) => <ol className="list-decimal pl-5 my-2 space-y-1.5" {...props} />,
            li: ({ node, ...props }) => <li className="leading-relaxed pl-0.5" {...props} />,
            strong: ({ node, ...props }) => <strong className={msg.role === 'user' ? "text-white font-bold" : "text-blue-400 font-bold"} {...props} />,
            em: ({ node, ...props }) => <em className={msg.role === 'user' ? "text-blue-100 italic" : "text-slate-100 italic"} {...props} />,
            a: ({ node, ...props }) => (
              <a
                className={msg.role === 'user' ? "text-blue-100 underline underline-offset-2" : "text-cyan-300 underline underline-offset-2 hover:text-cyan-200"}
                target="_blank"
                rel="noreferrer"
                {...props}
              />
            ),
            blockquote: ({ node, ...props }) => (
              <blockquote
                className={msg.role === 'user'
                  ? "border-l-2 border-blue-200/70 pl-3 my-2 text-blue-50/90"
                  : "border-l-2 border-blue-500/60 pl-3 my-2 text-slate-300 bg-blue-500/5 py-1 rounded-r"}
                {...props}
              />
            ),
            hr: ({ node, ...props }) => <hr className="my-3 border-white/10" {...props} />,
            pre: ({ node, children }) => <>{children}</>,
            code: createMarkdownCodeRenderer({
              nextMermaidBlockIndex: () => mermaidBlockCounter++,
              onMermaidRetry: (brokenCode, errorMessage, blockIndex) => handleChatMermaidRetry(msg.id, brokenCode, errorMessage, blockIndex),
              renderBlockCode: ({ className, children, props }) => (
                <pre className="p-3 bg-[#0a0f18] rounded-lg text-xs font-mono overflow-x-auto my-2 border border-[#1e293b]">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              ),
              renderInlineCode: ({ children, props }) => (
                <code className="bg-black/30 px-1 py-0.5 rounded font-mono text-xs mx-1" {...props}>
                  {children}
                </code>
              ),
            }),
            table: ({ node, ...props }) => <div className="overflow-x-auto my-3"><table className="w-full border-collapse text-sm" {...props} /></div>,
            th: ({ node, ...props }) => <th className="bg-slate-800/50 text-slate-200 font-semibold text-left p-2 border border-slate-700" {...props} />,
            td: ({ node, ...props }) => <td className="p-2 border border-slate-700/50 text-slate-300" {...props} />,
            tr: ({ node, ...props }) => <tr className="hover:bg-white/5 transition-colors" {...props} />,
          };

          return (
            <div key={msg.id} className={clsx("flex items-start gap-4 animate-fade-in-up", msg.role === 'user' ? "flex-row-reverse" : "")}>
              <div className={clsx(
                "flex items-center justify-center w-8 h-8 rounded-lg shrink-0 mt-1 shadow-sm",
                msg.role === 'user'
                  ? "bg-slate-800 border border-slate-700 text-slate-300"
                  : "bg-blue-500/10 border border-blue-500/20 text-blue-500 shadow-[0_0_15px_-3px_rgba(59,130,246,0.3)]"
              )}>
                {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
              </div>

              <div className={clsx("flex flex-col gap-1 max-w-[90%]", msg.role === 'user' ? "items-end" : "items-start")}>
                <span className="text-slate-500 text-[10px] font-mono px-1">
                  {msg.role === 'user' ? 'You' : agentName} • {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <div className={clsx(
                  "rounded-2xl p-4 text-sm leading-relaxed shadow-sm",
                  msg.role === 'user'
                    ? "rounded-tr-none bg-blue-600 text-white shadow-blue-500/10"
                    : "rounded-tl-none bg-[#151e32] text-gray-200 border border-[#1e293b]"
                )}>
                  {messageAttachments.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2">
                      {messageAttachments.map((att, idx) => (
                        <div key={idx} className="flex items-center gap-1.5 bg-black/20 px-2 py-1 rounded text-xs border border-white/10">
                          <FileText className="w-3 h-3" />
                          <span className="truncate max-w-[150px]">{att.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {visibleMessageContent && (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={messageMarkdownComponents}
                    >
                      {preprocessMarkdown(visibleMessageContent)}
                    </ReactMarkdown>
                  )}
                  {msg.errorDiagnostic && diagnosticStyle && (
                    <div className={clsx(
                      'mt-3 rounded-xl border p-3 shadow-sm',
                      diagnosticStyle.container
                    )}>
                      <div className="flex items-start gap-2">
                        <AlertTriangle className={clsx('mt-0.5 h-4 w-4 shrink-0', diagnosticStyle.icon)} />
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-semibold">{getDiagnosticTitle(msg.errorDiagnostic.kind)}</div>
                          <p className="mt-1 text-xs leading-relaxed opacity-85">
                            {msg.errorDiagnostic.summary}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => toggleErrorDetail(msg.id)}
                          className={clsx(
                            'inline-flex shrink-0 items-center gap-1 rounded-lg border px-2 py-1 text-[11px] font-semibold transition-colors',
                            diagnosticStyle.secondaryButton
                          )}
                          aria-expanded={isErrorDetailExpanded}
                        >
                          {isErrorDetailExpanded ? '收起详情' : '查看详情'}
                          {isErrorDetailExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                        </button>
                      </div>
                      {isErrorDetailExpanded && (
                        <div className={clsx('mt-3 rounded-lg border px-3 py-2 text-xs leading-relaxed', diagnosticStyle.detail)}>
                          {msg.errorDiagnostic.reason && (
                            <p><span className="font-semibold">可能原因：</span>{msg.errorDiagnostic.reason}</p>
                          )}
                          {msg.errorDiagnostic.action && (
                            <p className="mt-1"><span className="font-semibold">建议处理：</span>{msg.errorDiagnostic.action}</p>
                          )}
                          {msg.errorDiagnostic.code && (
                            <p className="mt-1"><span className="font-semibold">错误代码：</span>{msg.errorDiagnostic.code}</p>
                          )}
                          {(msg.errorDiagnostic.workflowId || msg.errorDiagnostic.stageId) && (
                            <p className="mt-1">
                              <span className="font-semibold">工作流阶段：</span>
                              {[msg.errorDiagnostic.workflowId, msg.errorDiagnostic.stageId].filter(Boolean).join(' / ')}
                            </p>
                          )}
                          {msg.errorDiagnostic.phase && (
                            <p className="mt-1"><span className="font-semibold">失败阶段：</span>{msg.errorDiagnostic.phase}</p>
                          )}
                          {msg.errorDiagnostic.fieldPath && (
                            <p className="mt-1"><span className="font-semibold">字段路径：</span>{msg.errorDiagnostic.fieldPath}</p>
                          )}
                          {msg.errorDiagnostic.validator && (
                            <p className="mt-1"><span className="font-semibold">校验器：</span>{msg.errorDiagnostic.validator}</p>
                          )}
                          {typeof msg.errorDiagnostic.retryable === 'boolean' && (
                            <p className="mt-1">
                              <span className="font-semibold">重试建议：</span>
                              {msg.errorDiagnostic.retryable ? '可重试' : '需要先处理原因'}
                            </p>
                          )}
                          <pre className="mt-2 max-h-36 overflow-auto whitespace-pre-wrap rounded-md bg-black/25 p-2 font-mono text-[11px] leading-relaxed">
                            {msg.errorDiagnostic.rawMessage}
                          </pre>
                        </div>
                      )}
                      {msg.errorDiagnostic.kind === 'provider' && providerCheck.status !== 'idle' && (
                        <div className={clsx(
                          "mt-3 rounded-lg border px-3 py-2 text-xs leading-relaxed",
                          providerCheck.status === 'success'
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
                            : providerCheck.status === 'checking'
                              ? "border-rose-300/20 bg-rose-400/10 text-rose-100/80"
                              : "border-rose-400/40 bg-rose-400/10 text-rose-100"
                        )}>
                          {providerCheck.message}
                        </div>
                      )}
                      <div className="mt-3 flex flex-wrap justify-end gap-2">
                        {msg.errorDiagnostic.kind === 'structured' && shouldShowSupplementStructuredFailure && (
                          <button
                            type="button"
                            onClick={handleSupplementStructuredFailure}
                            className={clsx(
                              'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors',
                              diagnosticStyle.secondaryButton
                            )}
                          >
                            补充信息后再试
                          </button>
                        )}
                        {msg.errorDiagnostic.kind === 'provider' && (
                          <>
                            <button
                              type="button"
                              onClick={() => setSettingsOpen(true)}
                              className={clsx(
                                'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors',
                                diagnosticStyle.secondaryButton
                              )}
                            >
                              <Settings className="h-3.5 w-3.5" />
                              打开模型设置
                            </button>
                            <button
                              type="button"
                              onClick={() => void handleProviderConfigCheck(msg.id)}
                              disabled={providerCheck.status === 'checking'}
                              className={clsx(
                                'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-60',
                                diagnosticStyle.secondaryButton
                              )}
                            >
                              <RefreshCw className={clsx(
                                "h-3.5 w-3.5",
                                providerCheck.status === 'checking' && "animate-spin"
                              )} />
                              {providerCheck.status === 'checking' ? '正在检测...' : '检测连接'}
                            </button>
                          </>
                        )}
                        <button
                          type="button"
                          onClick={() => void handleRetryCurrentStageGeneration()}
                          className={clsx(
                            'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-colors',
                            diagnosticStyle.primaryButton
                          )}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          重试本阶段生成
                        </button>
                      </div>
                    </div>
                  )}
                  {!msg.errorDiagnostic && isStructuredOutputFailure && (
                    <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-amber-100">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
                        <div className="min-w-0">
                          <div className="text-sm font-semibold">结构化结果未更新</div>
                          <p className="mt-1 text-xs leading-relaxed text-amber-100/80">
                            右侧产出物已保持不变
                          </p>
                          <p className="mt-1 text-xs leading-relaxed text-amber-100/70">
                            连续失败时，请补充更明确的需求或阶段确认信息后再试。
                          </p>
                        </div>
                      </div>
                      <div className="mt-3 flex flex-wrap justify-end gap-2">
                        {shouldShowSupplementStructuredFailure && (
                          <button
                            type="button"
                            onClick={handleSupplementStructuredFailure}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-1.5 text-xs font-bold text-amber-100 transition-colors hover:bg-amber-400/20"
                          >
                            补充信息后再试
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => void handleRetryCurrentStageGeneration()}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition-colors hover:bg-amber-400"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          重试本阶段生成
                        </button>
                      </div>
                    </div>
                  )}
                  {!msg.errorDiagnostic && isProviderFailure && (
                    <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-rose-100">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />
                        <div className="min-w-0">
                          <div className="text-sm font-semibold">模型调用未完成</div>
                          <p className="mt-1 text-xs leading-relaxed text-rose-100/80">
                            右侧产出物已保持不变
                          </p>
                          <p className="mt-1 text-xs leading-relaxed text-rose-100/70">
                            请先检查模型配置、供应商额度或网络连通性，确认恢复后再重试。
                          </p>
                        </div>
                      </div>
                      {providerCheck.status !== 'idle' && (
                        <div className={clsx(
                          "mt-3 rounded-lg border px-3 py-2 text-xs leading-relaxed",
                          providerCheck.status === 'success'
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
                            : providerCheck.status === 'checking'
                              ? "border-rose-300/20 bg-rose-400/10 text-rose-100/80"
                              : "border-rose-400/40 bg-rose-400/10 text-rose-100"
                        )}>
                          {providerCheck.message}
                        </div>
                      )}
                      <div className="mt-3 flex flex-wrap justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setSettingsOpen(true)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300/30 bg-rose-300/10 px-3 py-1.5 text-xs font-bold text-rose-100 transition-colors hover:bg-rose-300/20"
                        >
                          <Settings className="h-3.5 w-3.5" />
                          打开模型设置
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleProviderConfigCheck(msg.id)}
                          disabled={providerCheck.status === 'checking'}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300/30 bg-rose-300/10 px-3 py-1.5 text-xs font-bold text-rose-100 transition-colors hover:bg-rose-300/20 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <RefreshCw className={clsx(
                            "h-3.5 w-3.5",
                            providerCheck.status === 'checking' && "animate-spin"
                          )} />
                          {providerCheck.status === 'checking' ? '正在检测...' : '检测连接'}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleRetryCurrentStageGeneration()}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-rose-400"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          重试本阶段生成
                        </button>
                      </div>
                    </div>
                  )}
                  <div className="mt-3 pt-3 border-t border-white/10 flex justify-end gap-3">
                    <button
                      onClick={() => handleCopy(msg.content || '', msg.id)}
                      className={clsx(
                        "flex items-center gap-1.5 text-xs transition-colors",
                        copiedId === msg.id ? "text-green-400" : "text-slate-400 hover:text-blue-400"
                      )}
                      title="复制内容"
                    >
                      {copiedId === msg.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedId === msg.id ? '已复制' : '复制'}</span>
                    </button>
                    {msg.role === 'assistant' && msg.retryable !== false && !isGenerating && msg.id === chatHistory[chatHistory.length - 1]?.id && !isStructuredOutputFailure && !isProviderFailure && !isDiagnosticFailure && (
                      <button
                        onClick={handleRetry}
                        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-blue-400 transition-colors"
                        title="重新生成"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>重试</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {pendingStageTransition && pendingNextStage && !isGenerating && !isLatestStructuredOutputFailure && !isLatestProviderFailure && (
          <div className="flex items-start gap-4 animate-fade-in-up">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg shrink-0 mt-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <ChevronRight className="w-5 h-5" />
            </div>
            <div className="flex flex-col gap-2 max-w-[90%] items-start">
              <span className="text-slate-500 text-[10px] font-mono px-1">{agentName} • 等待确认</span>
              <div className="rounded-2xl rounded-tl-none bg-emerald-500/10 text-emerald-100 border border-emerald-500/20 p-4 shadow-sm">
                <div className="text-sm font-medium">
                  AI 建议进入下一阶段：{pendingNextStage.name}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-emerald-200/70">
                  确认后我会进入该阶段，并继续生成对应的右侧产出物。
                </p>
                <div className="mt-4 flex flex-wrap justify-end gap-2">
                  <button
                    onClick={clearPendingStageTransition}
                    className="rounded-lg px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-white/5 transition-colors"
                  >
                    暂不进入
                  </button>
                  <button
                    onClick={handleConfirmStageTransition}
                    className="rounded-lg px-4 py-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 transition-colors shadow-md shadow-emerald-500/20"
                  >
                    确认进入 {pendingNextStage.name}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {isGenerating && (chatHistory.length === 0 || chatHistory[chatHistory.length - 1]?.role !== 'assistant' || !chatHistory[chatHistory.length - 1]?.content?.trim()) && (
          <div className="flex items-start gap-4 animate-fade-in-up">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-500 shrink-0 mt-1">
              <Bot className="w-5 h-5 animate-pulse" />
            </div>
            <div className="flex flex-col gap-1 items-start">
              <span className="text-slate-500 text-[10px] font-mono ml-1">{agentName} • 思考中...</span>
              <div className="rounded-2xl rounded-tl-none bg-[#151e32] p-4 border border-[#1e293b] flex gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-[#0B1120] border-t border-[#1e293b] relative z-20">
        <div className="relative flex flex-col gap-2 bg-[#0f1623] rounded-xl border border-[#1e293b] focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/50 transition-all p-2 shadow-inner">
          {renderablePendingAttachments.length > 0 && (
            <div className="flex flex-wrap gap-2 px-2 pt-2">
              {renderablePendingAttachments.map((att, idx) => (
                <div key={idx} className="flex items-center gap-1.5 bg-[#1e293b] px-2 py-1 rounded text-xs text-slate-300 border border-slate-700">
                  <FileText className="w-3 h-3 text-blue-400" />
                  <span className="truncate max-w-[150px]">{att.name}</span>
                  <button
                    onClick={() => removeAttachment(idx)}
                    className="text-slate-500 hover:text-red-400 transition-colors ml-1"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={onFileChange}
              className="hidden"
              multiple
              accept=".txt,.md,.pdf,.csv,.json,image/*"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="text-slate-500 hover:text-white p-2 rounded-lg hover:bg-white/5 transition-colors"
              title="上传附件"
            >
              <PlusCircle className="w-5 h-5" />
            </button>
            <textarea
              ref={textareaRef}
              className="w-full bg-transparent border-0 text-gray-200 placeholder-slate-500 focus:ring-0 resize-none py-2.5 max-h-32 text-sm leading-relaxed"
              placeholder={onboardingConfig.inputPlaceholder}
              rows={1}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 128)}px`;
              }}
              onKeyDown={handleKeyDown}
            />
            {isGenerating ? (
              <button
                onClick={handleStop}
                className="bg-red-500/10 hover:bg-red-500/20 text-red-500 p-2 rounded-lg transition-colors border border-red-500/20 self-end mb-0.5 flex items-center justify-center"
                title="停止生成"
              >
                <Square className="w-5 h-5 fill-current" />
              </button>
            ) : (
              <button
                id="send-button"
                onClick={() => handleSend()}
                disabled={!input.trim() && pendingAttachments.length === 0}
                className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-colors shadow-lg shadow-blue-500/20 self-end mb-0.5"
                title="发送"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
        <p className="text-center text-[10px] text-slate-500 mt-3 font-mono">{agentName} Generated Context • v1.0.4</p>
      </div>
      {toast && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {toast}
        </div>
      )}
    </section>
  );
};
