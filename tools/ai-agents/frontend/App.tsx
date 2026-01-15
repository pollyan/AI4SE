import React, { useState, useRef, useCallback, useEffect } from 'react';
import Layout from './components/Layout';
import { AssistantChat } from './components/chat';
import AssistantCard from './components/AssistantCard';
import AnalysisResultPanel from './components/AnalysisResultPanel';
import { ASSISTANTS } from './constants';
import { AssistantId, Assistant } from './types';
import type { ProgressInfo } from './services/backendService';
import { Bot } from 'lucide-react';
import '@assistant-ui/styles/index.css';

const App: React.FC = () => {
  const [selectedAssistantId, setSelectedAssistantId] = useState<AssistantId | null>(null);
  const [analysisResult, setAnalysisResult] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [workflowProgress, setWorkflowProgress] = useState<ProgressInfo | null>(null);
  const [artifacts, setArtifacts] = useState<Record<string, string>>({});
  const [streamingArtifactKey, setStreamingArtifactKey] = useState<string | null>(null);
  const [streamingArtifactContent, setStreamingArtifactContent] = useState<string>('');

  const handleSelectAssistant = (id: AssistantId) => {
    if (!id) {
      setSelectedAssistantId(null);
      return;
    }
    if (id === selectedAssistantId) return;

    const assistant = ASSISTANTS.find(a => a.id === id);
    if (!assistant) return;

    setSelectedAssistantId(id);
    setAnalysisResult('');
    setWorkflowProgress(null);
    setArtifacts({});
    setStreamingArtifactKey(null);
    setStreamingArtifactContent('');
  };

  const handleBack = () => {
    setSelectedAssistantId(null);
  };

  const handleProgressChange = (progress: ProgressInfo | null) => {
    setWorkflowProgress(progress);
    // 合并而不是覆盖 artifacts，确保前端累积的内容不会丢失
    if (progress?.artifacts) {
      setArtifacts(prev => ({ ...prev, ...progress.artifacts }));
    }
  };

  // ArtifactEvent 已通过 onProgressChange 传递，无需单独处理

  const selectedAssistant = ASSISTANTS.find(a => a.id === selectedAssistantId);

  const [leftWidth, setLeftWidth] = useState<number>(40);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isDesktop, setIsDesktop] = useState<boolean>(typeof window !== 'undefined' ? window.innerWidth >= 1024 : true);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1024);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const newLeftWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;

    if (newLeftWidth >= 20 && newLeftWidth <= 80) {
      setLeftWidth(newLeftWidth);
    }
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // 助手选择面板
  const AssistantSelectionPanel = () => (
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
          {ASSISTANTS.map((assistant) => (
            <AssistantCard
              key={assistant.id}
              assistant={assistant}
              isSelected={selectedAssistantId === assistant.id}
              onSelect={handleSelectAssistant}
            />
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <Layout>

      <div
        ref={containerRef}
        className="flex flex-col lg:flex-row h-[calc(100vh-140px)] md:h-[calc(100vh-220px)] min-h-[600px] overflow-hidden"
      >
        <div
          className="h-full flex-shrink-0 transition-[width] duration-0 ease-linear"
          style={{ width: isDesktop ? `${leftWidth}%` : '100%' }}
        >
          {selectedAssistant ? (
            <AssistantChat
              assistant={selectedAssistant}
              onBack={handleBack}
              onProgressChange={handleProgressChange}
            />
          ) : (
            <AssistantSelectionPanel />
          )}
        </div>

        {/* Divider - only visible on desktop */}
        <div
          className="hidden lg:flex w-4 cursor-col-resize items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors flex-shrink-0 z-10 -ml-2 -mr-2 relative"
          onMouseDown={handleMouseDown}
        >
          <div className="w-1 h-12 bg-gray-300 dark:bg-gray-600 rounded-full" />
        </div>

        <div
          className="h-full flex-shrink-0 transition-[width] duration-0 ease-linear"
          style={{ width: isDesktop ? `${100 - leftWidth}%` : '100%' }}
        >
          <AnalysisResultPanel
            result={analysisResult}
            isProcessing={isProcessing}
            hasStarted={!!analysisResult || Object.keys(artifacts).length > 0 || (workflowProgress && workflowProgress.stages.length > 0)}
            progress={workflowProgress}
            assistantId={selectedAssistantId}
            artifacts={artifacts}
            streamingArtifactKey={streamingArtifactKey}
            streamingArtifactContent={streamingArtifactKey ? streamingArtifactContent : null}
          />
        </div>
      </div>
    </Layout>
  );
};

export default App;