import React, { useRef, useEffect } from 'react';
import { useStore } from '../store';
import { Send, PlusCircle, Bot, User, FileText, X, Square, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { clsx } from 'clsx';
import { useChatService } from '../services/chatService';

export const ChatPane: React.FC = () => {
  const { chatHistory, isGenerating } = useStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    input,
    setInput,
    pendingAttachments,
    handleSend,
    handleRetry,
    handleStop,
    handleFileChange,
    removeAttachment
  } = useChatService();

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

  return (
    <section className="flex flex-col w-full lg:w-[40%] min-w-[360px] bg-[#0B1120] border-r border-[#1e293b] relative shadow-[10px_0_30px_-10px_rgba(0,0,0,0.5)] z-20 h-full">
      <div className="px-5 py-4 border-b border-[#1e293b] bg-[#0B1120]/95 backdrop-blur sticky top-0 z-10">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-white text-base font-bold flex items-center gap-2">
            <Bot className="w-5 h-5 text-blue-500" />
            智能需求分析
          </h3>
          <span className="text-[10px] uppercase tracking-wider text-cyan-400 font-mono border border-cyan-400/20 bg-cyan-400/10 px-2 py-0.5 rounded-full">Active</span>
        </div>
        <p className="text-slate-400 text-xs truncate">Lisa 测试专家正在为您服务</p>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6 custom-scrollbar">
        {chatHistory.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500 space-y-4">
            <Bot className="w-12 h-12 opacity-50" />
            <p className="text-sm text-center max-w-xs">
              你好，我是 Lisa。<br />
              请在下方输入您的需求，或上传已有的需求文档，我们将开始测试设计工作流。
            </p>
          </div>
        )}

        {chatHistory.map((msg) => {
          // Hide the empty assistant bubble that gets created initially before text arrives
          if (isGenerating && msg.role === 'assistant' && !msg.content && msg.id === chatHistory[chatHistory.length - 1]?.id) {
            return null;
          }

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
                  {msg.role === 'user' ? 'You' : 'Lisa AI'} • {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <div className={clsx(
                  "rounded-2xl p-4 text-sm leading-relaxed shadow-sm",
                  msg.role === 'user'
                    ? "rounded-tr-none bg-blue-600 text-white shadow-blue-500/10"
                    : "rounded-tl-none bg-[#151e32] text-gray-200 border border-[#1e293b]"
                )}>
                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2">
                      {msg.attachments.map((att, idx) => (
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
                      components={{
                        p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                        strong: ({ node, ...props }) => <strong className={msg.role === 'user' ? "text-white font-bold" : "text-blue-400 font-bold"} {...props} />,
                        code: ({ node, ...props }) => <code className="bg-black/30 px-1 py-0.5 rounded font-mono text-xs mx-1" {...props} />,
                        table: ({ node, ...props }: any) => <div className="overflow-x-auto my-3"><table className="w-full border-collapse text-sm" {...props} /></div>,
                        th: ({ node, ...props }: any) => <th className="bg-slate-800/50 text-slate-200 font-semibold text-left p-2 border border-slate-700" {...props} />,
                        td: ({ node, ...props }: any) => <td className="p-2 border border-slate-700/50 text-slate-300" {...props} />,
                        tr: ({ node, ...props }: any) => <tr className="hover:bg-white/5 transition-colors" {...props} />,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                  {msg.role === 'assistant' && !isGenerating && msg.id === chatHistory[chatHistory.length - 1]?.id && (
                    <div className="mt-3 pt-3 border-t border-white/10 flex justify-end">
                      <button
                        onClick={handleRetry}
                        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-blue-400 transition-colors"
                        title="重新生成"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>重试</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {isGenerating && (chatHistory.length === 0 || chatHistory[chatHistory.length - 1]?.role !== 'assistant' || !chatHistory[chatHistory.length - 1]?.content) && (
          <div className="flex items-start gap-4 animate-fade-in-up">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-500 shrink-0 mt-1">
              <Bot className="w-5 h-5 animate-pulse" />
            </div>
            <div className="flex flex-col gap-1 items-start">
              <span className="text-slate-500 text-[10px] font-mono ml-1">Lisa AI • 思考中...</span>
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
          {pendingAttachments.length > 0 && (
            <div className="flex flex-wrap gap-2 px-2 pt-2">
              {pendingAttachments.map((att, idx) => (
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
              placeholder="回复 Lisa..."
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
                onClick={handleSend}
                disabled={!input.trim() && pendingAttachments.length === 0}
                className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-colors shadow-lg shadow-blue-500/20 self-end mb-0.5"
                title="发送"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
        <p className="text-center text-[10px] text-slate-500 mt-3 font-mono">Lisa AI Generated Context • v1.0.4</p>
      </div>
    </section>
  );
};
