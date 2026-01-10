import React from 'react';
import ReactMarkdown from 'react-markdown';
import { BarChart2, Search } from 'lucide-react';
import { WorkflowProgress, Stage } from './WorkflowProgress';

interface ProgressInfo {
  stages: Stage[];
  currentStageIndex: number;
  currentTask: string | null;
}

interface AnalysisResultPanelProps {
  result: string;
  isProcessing: boolean;
  hasStarted: boolean;
  progress?: ProgressInfo | null;
  assistantId?: string | null;
}

const AnalysisResultPanel: React.FC<AnalysisResultPanelProps> = ({
  result,
  isProcessing,
  hasStarted,
  progress,
  assistantId
}) => {
  // 只对 Lisa 显示进度
  const showProgress = assistantId === 'lisa' && progress && progress.stages.length > 0;

  return (
    <div className="w-full bg-surface-light dark:bg-surface-dark rounded-xl shadow-lg border border-border-light dark:border-border-dark flex flex-col h-full overflow-hidden">
      <div className="px-6 py-4 border-b border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/50 h-16 flex items-center">
        <h2 className="font-semibold text-lg text-gray-800 dark:text-white flex items-center gap-2">
          <BarChart2 className="text-secondary" size={24} />
          分析成果
        </h2>
      </div>

      {/* 进度条 - 只对 Lisa 显示 */}
      {showProgress && (
        <WorkflowProgress
          stages={progress.stages}
          currentStageIndex={progress.currentStageIndex}
          currentTask={progress.currentTask}
        />
      )}

      <div className="flex-grow flex flex-col p-6 overflow-y-auto bg-gray-50/50 dark:bg-gray-900/20">
        {!hasStarted && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-24 h-24 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-6">
              <Search className="text-gray-300 dark:text-gray-500" size={48} />
            </div>
            <p className="text-gray-500 dark:text-gray-400 max-w-sm">
              开始与AI助手对话后，这里将实时显示结构化的分析成果
            </p>
          </div>
        )}

        {hasStarted && (
          <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none">
            {result ? (
              <ReactMarkdown>{result}</ReactMarkdown>
            ) : (
              isProcessing && <div className="animate-pulse flex space-x-4">
                <div className="flex-1 space-y-4 py-1">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                  <div className="space-y-2">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisResultPanel;