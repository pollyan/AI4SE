import React, { useState, useRef, useEffect } from 'react';
import { Bot, Paperclip, Send, User, ChevronLeft } from 'lucide-react';
import { Assistant, AssistantId, ChatMessage } from '../types';
import AssistantCard from './AssistantCard';
import ReactMarkdown from 'react-markdown';

interface AssistantPanelProps {
  assistants: Assistant[];
  selectedAssistantId: AssistantId | null;
  onSelectAssistant: (id: AssistantId) => void;
  messages: ChatMessage[];
  onSubmit: (text: string) => void;
  isProcessing: boolean;
}

const AssistantPanel: React.FC<AssistantPanelProps> = ({
  assistants,
  selectedAssistantId,
  onSelectAssistant,
  messages,
  onSubmit,
  isProcessing
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    // Scroll only within the chat container, not the entire page
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  // Focus input when assistant is selected - use preventScroll to avoid page jump
  useEffect(() => {
    if (selectedAssistantId && inputRef.current) {
      inputRef.current.focus({ preventScroll: true });
    }
  }, [selectedAssistantId]);

  const handleSend = () => {
    if (!inputText.trim() || isProcessing || !selectedAssistantId) return;
    onSubmit(inputText);
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const selectedAssistant = assistants.find(a => a.id === selectedAssistantId);

  // If no assistant selected, show selection screen
  if (!selectedAssistantId) {
    return (
      <div className="w-full flex flex-col bg-surface-light dark:bg-surface-dark rounded-xl shadow-lg border border-border-light dark:border-border-dark overflow-hidden h-full">
        <div className="px-6 py-4 border-b border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/50 h-16 flex items-center">
          <h2 className="font-semibold text-lg text-gray-800 dark:text-white flex items-center gap-2">
            <Bot className="text-primary" size={24} />
            选择智能助手
          </h2>
        </div>
        <div className="flex-grow overflow-y-auto p-6 flex flex-col justify-center">
          <div className="text-center mb-8">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">选择您的智能助手</h3>
            <p className="text-gray-500 dark:text-gray-400">请选择一位专业的AI助手开始对话：</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {assistants.map((assistant) => (
              <AssistantCard
                key={assistant.id}
                assistant={assistant}
                isSelected={selectedAssistantId === assistant.id}
                onSelect={onSelectAssistant}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col bg-surface-light dark:bg-surface-dark rounded-xl shadow-lg border border-border-light dark:border-border-dark overflow-hidden h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border-light dark:border-border-dark flex justify-between items-center bg-gray-50 dark:bg-gray-800/50 shrink-0 h-16">
        <div className="flex items-center gap-3">
          <button
            onClick={() => onSelectAssistant('' as any)} // Hack to reset, or pass a clear function
            className="lg:hidden mr-2 text-gray-500 hover:text-gray-700"
          >
            <ChevronLeft size={20} />
          </button>
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg text-white ${selectedAssistant?.colorClass.replace('bg-', 'bg-').replace('text-', 'text-').split(' ')[0]} ${selectedAssistant?.id === 'alex' ? 'bg-primary' : 'bg-secondary'}`}>
            {selectedAssistant?.initial}
          </div>
          <div>
            <h2 className="font-semibold text-gray-800 dark:text-white leading-tight">
              {selectedAssistant?.name}
            </h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {selectedAssistant?.role}
            </p>
          </div>
        </div>
        <button
          onClick={() => onSelectAssistant('' as any)}
          className="text-xs text-primary hover:underline hidden lg:block"
        >
          切换助手
        </button>
      </div>

      {/* Chat Area */}
      <div ref={chatContainerRef} className="flex-grow overflow-y-auto p-4 space-y-6 bg-white dark:bg-gray-900 scroll-smooth">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1
                    ${msg.role === 'user'
                ? 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                : `${selectedAssistant?.id === 'alex' ? 'bg-primary' : 'bg-secondary'} text-white`
              }`}
            >
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>

            <div className={`flex flex-col max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm
                        ${msg.role === 'user'
                  ? 'bg-primary text-white rounded-tr-none'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-none border border-gray-200 dark:border-gray-700'
                }`}
              >
                {msg.isThinking ? (
                  <div className="flex space-x-1 h-5 items-center px-1">
                    <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"></div>
                  </div>
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none break-words">
                    <ReactMarkdown>
                      {msg.text}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-gray-400 mt-1 px-1">
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/30 shrink-0">
        <div className="relative flex items-center gap-2">
          <div className="relative flex-grow">
            <input
              ref={inputRef}
              className="w-full pl-4 pr-12 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-full focus:ring-2 focus:ring-primary focus:border-primary text-sm shadow-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="请输入..."
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isProcessing}
            />
            <button
              className="absolute right-3 top-2.5 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              <Paperclip size={18} />
            </button>
          </div>

          <button
            onClick={handleSend}
            disabled={!inputText.trim() || isProcessing}
            className={`p-3 rounded-full shadow-sm transition-colors flex items-center justify-center
              ${!inputText.trim() || isProcessing
                ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                : 'bg-primary hover:bg-indigo-600 text-white cursor-pointer'
              }`}
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default AssistantPanel;