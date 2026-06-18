import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useStore, WORKFLOWS } from '../store';
import { Send, PlusCircle, Bot, User, FileText, X, Square, RefreshCw, Copy, Check, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { clsx } from 'clsx';
import { useChatService } from '../services/chatService';
import { getAgentById } from '../core/config/agents';
import { preprocessMarkdown, replaceMermaidBlockAtIndex } from '../core/utils/markdownUtils';
import { createMarkdownCodeRenderer } from './markdownCodeRenderer';
import type { Attachment } from '../store';

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

export const ChatPane: React.FC = () => {
  // 使用选择器订阅特定状态，减少不必要的重渲染 (rerender-defer-reads)
  const chatHistory = useStore((state) => state.chatHistory);
  const isGenerating = useStore((state) => state.isGenerating);
  const workflow = useStore((state) => state.workflow);
  const pendingStageTransition = useStore((state) => state.pendingStageTransition);
  const clearPendingStageTransition = useStore((state) => state.clearPendingStageTransition);
  
  const onboardingConfig = WORKFLOWS[workflow].onboarding;
  const workflowStages = WORKFLOWS[workflow].stages;
  const agentId = WORKFLOWS[workflow].agentId;
  const agentConfig = getAgentById(agentId);
  const displayTitle = agentConfig?.displayTitle || agentId;
  const agentName = agentConfig?.name || 'AI';
  const pendingNextStage = pendingStageTransition
    ? workflowStages[pendingStageTransition.toStageIndex]
    : null;

  const updateMessage = useStore((state) => state.updateMessage);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const copyFeedbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

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

  useEffect(() => () => {
    if (copyFeedbackTimeoutRef.current) {
      clearTimeout(copyFeedbackTimeoutRef.current);
    }
  }, []);

  const {
    input,
    setInput,
    pendingAttachments,
    handleSend,
    handleConfirmStageTransition,
    handleRetry,
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
          let mermaidBlockCounter = 0;
          const messageMarkdownComponents: Components = {
            p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
            strong: ({ node, ...props }) => <strong className={msg.role === 'user' ? "text-white font-bold" : "text-blue-400 font-bold"} {...props} />,
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
                  {msg.content && (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={messageMarkdownComponents}
                    >
                      {preprocessMarkdown(msg.content)}
                    </ReactMarkdown>
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
                    {msg.role === 'assistant' && msg.retryable !== false && !isGenerating && msg.id === chatHistory[chatHistory.length - 1]?.id && (
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

        {pendingStageTransition && pendingNextStage && !isGenerating && (
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
