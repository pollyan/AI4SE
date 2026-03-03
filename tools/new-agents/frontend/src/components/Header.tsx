import React, { useState } from 'react';
import { useStore, WORKFLOWS } from '../store';
import { Settings, Share, Bot, Plus, AlertTriangle, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';

export const Header: React.FC = () => {
  const { workflow, stageIndex, setStageIndex, setSettingsOpen, clearHistory } = useStore();
  const stages = WORKFLOWS[workflow].stages;
  const [showConfirm, setShowConfirm] = useState(false);
  const navigate = useNavigate();

  const handleNewChat = () => {
    setShowConfirm(true);
  };

  const confirmNewChat = () => {
    clearHistory();
    setShowConfirm(false);
  };

  return (
    <>
      <header className="flex items-center justify-between border-b border-[#1e293b] bg-[#0B1120]/80 backdrop-blur-md px-6 py-3 shrink-0 z-30">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/workflows/lisa')}
            className="group flex items-center justify-center p-2 rounded-lg hover:bg-[#1e293b] text-slate-400 hover:text-white transition-all mr-2"
          >
            <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
          </button>

          <div className="w-8 h-8 flex items-center justify-center rounded bg-gradient-to-br from-blue-500 to-purple-600 text-white shadow-lg shadow-blue-500/20">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-white text-lg font-bold leading-tight tracking-tight cursor-default">
              Lisa <span className="text-slate-400 font-medium text-sm ml-1">AI 智能测试专家</span>
            </h2>
          </div>
        </div>

        <div className="hidden md:flex flex-1 max-w-2xl mx-8">
          <div className="flex h-12 w-full items-center justify-center rounded-xl bg-[#0f1623] p-1.5 border border-[#1e293b]/50">
            {stages.map((stage, idx) => {
              const isActive = idx === stageIndex;
              return (
                <div
                  key={stage.id}
                  onClick={() => setStageIndex(idx)}
                  className={clsx(
                    "relative flex cursor-pointer h-full grow items-center justify-center rounded-lg px-4 text-sm font-medium transition-all group",
                    isActive ? "bg-blue-600 text-white shadow-md shadow-blue-500/10 font-semibold" : "text-slate-400 hover:text-white hover:bg-white/5"
                  )}
                >
                  <span className={clsx(
                    "mr-2 text-[10px] font-mono px-1.5 py-0.5 rounded transition-opacity",
                    isActive ? "bg-white/20 opacity-80" : "bg-white/5 opacity-40 group-hover:opacity-60"
                  )}>
                    0{idx + 1}
                  </span>
                  <span className="truncate">{stage.name}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center gap-2 rounded-lg h-9 px-4 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-all shadow-md shadow-blue-500/20"
          >
            <Plus className="w-4 h-4" />
            <span className="truncate hidden lg:inline">新会话</span>
          </button>
          <button className="flex items-center justify-center gap-2 rounded-lg h-9 px-4 bg-[#151e32] border border-[#1e293b] hover:border-blue-500/50 text-slate-400 hover:text-white text-sm font-medium transition-all">
            <Share className="w-4 h-4" />
            <span className="truncate hidden lg:inline">导出报告</span>
          </button>
          <button
            onClick={() => setSettingsOpen(true)}
            className="flex items-center justify-center rounded-lg w-9 h-9 hover:bg-[#151e32] text-slate-400 hover:text-white transition-colors"
          >
            <Settings className="w-5 h-5" />
          </button>
          <div className="bg-center bg-no-repeat bg-cover rounded-full w-9 h-9 ml-2 ring-2 ring-[#151e32]" style={{ backgroundImage: 'url("https://picsum.photos/seed/lisa/100/100")' }}></div>
        </div>
      </header>

      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-sm flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">开启新会话</h3>
            </div>
            <p className="text-sm text-slate-300 mb-6">
              确定要开启新会话吗？这将清空当前的对话历史和产出物文档，且无法恢复。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/5 transition-colors"
              >
                取消
              </button>
              <button
                onClick={confirmNewChat}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-500 transition-colors shadow-md shadow-red-500/20"
              >
                确定清空
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
