import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { BarChart2, Search } from 'lucide-react';
import { WorkflowProgress, Stage } from './WorkflowProgress';
import { ArtifactPanel, ArtifactProgress } from './ArtifactPanel';

interface ProgressInfo {
  stages: Stage[];
  currentStageIndex: number;
  currentTask: string | null;
  artifactProgress?: ArtifactProgress | null;
}

interface AnalysisResultPanelProps {
  result: string;
  isProcessing: boolean;
  hasStarted: boolean;
  progress?: ProgressInfo | null;
  assistantId?: string | null;
  /** 产出物内容 (key -> content) */
  artifacts?: Record<string, string>;
  /** 正在生成中的产出物内容 (实时流式) */
  streamingArtifactContent?: string | null;
}

const AnalysisResultPanel: React.FC<AnalysisResultPanelProps> = ({
  result,
  isProcessing,
  hasStarted,
  progress,
  assistantId,
  artifacts = {},
  streamingArtifactContent = null,
}) => {
  // 选中查看的阶段 ID (null 表示当前活动阶段)
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);

  // 对 Lisa 和 Alex 显示进度
  const showProgress = (assistantId === 'lisa' || assistantId === 'alex') && progress && progress.stages.length > 0;

  // 获取当前活动阶段 ID
  const currentStageId = progress?.stages?.[progress.currentStageIndex]?.id || null;

  // 处理阶段点击
  const handleStageClick = (stageId: string) => {
    setSelectedStageId(stageId);
  };

  // 返回当前阶段
  const handleBackToCurrentStage = () => {
    setSelectedStageId(null);
  };

  return (
    <div className="w-full bg-surface-light dark:bg-surface-dark rounded-xl shadow-lg border border-border-light dark:border-border-dark flex flex-col h-full overflow-hidden">
      <div className="px-6 py-4 border-b border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/50 h-16 flex items-center">
        <h2 className="font-semibold text-lg text-gray-800 dark:text-white flex items-center gap-2">
          <BarChart2 className="text-secondary" size={24} />
          分析成果
        </h2>
      </div>

      {/* 进度条 */}
      {showProgress && (
        <WorkflowProgress
          stages={progress.stages}
          currentStageIndex={progress.currentStageIndex}
          currentTask={progress.currentTask}
          selectedStageId={selectedStageId}
          onStageClick={handleStageClick}
        />
      )}

      {/* 内容区域 */}
      <div className="flex-grow flex flex-col overflow-hidden">
        {!hasStarted ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6">
            <div className="w-24 h-24 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mb-6">
              <Search className="text-gray-300 dark:text-gray-500" size={48} />
            </div>
            <p className="text-gray-500 dark:text-gray-400 max-w-sm">
              开始与AI助手对话后，这里将实时显示结构化的分析成果
            </p>
          </div>
        ) : showProgress ? (
          <ArtifactPanel
            artifactProgress={progress?.artifactProgress || null}
            selectedStageId={selectedStageId}
            currentStageId={currentStageId}
            artifacts={artifacts}
            streamingArtifactContent={streamingArtifactContent}
            onBackToCurrentStage={handleBackToCurrentStage}
          />
        ) : (
          <div className="flex-grow p-6 overflow-y-auto bg-gray-50/50 dark:bg-gray-900/20">
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
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisResultPanel;