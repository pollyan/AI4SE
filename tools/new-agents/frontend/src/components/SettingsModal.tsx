import React from 'react';
import { useStore } from '../store';
import { Settings, X, Save, Trash2 } from 'lucide-react';

export const SettingsModal: React.FC = () => {
  const {
    isSettingsOpen,
    setSettingsOpen,
    clearHistory,
  } = useStore();

  if (!isSettingsOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-[600px] flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10">
        <header className="flex items-center justify-between border-b border-slate-800 bg-[#151f2b] px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
              <Settings className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold leading-tight text-white">设置</h2>
              <p className="text-xs font-medium text-slate-400">查看系统配置并管理本地数据</p>
            </div>
          </div>
          <button
            onClick={() => setSettingsOpen(false)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <section>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">模型配置</h3>
            </div>

            <div className="rounded-lg border border-blue-900/30 bg-blue-900/10 p-4">
              <p className="text-sm font-medium text-blue-200">LLM 由后端系统配置统一管理</p>
              <p className="mt-2 text-xs leading-relaxed text-blue-300/80">
                主 Agent 调用只通过结构化 Agent Runtime 执行。API Key、Base URL 和模型名称需要在后端默认配置中维护，前端不再保存或直连个人 API Key。
              </p>
            </div>
          </section>


          <section>
            <div className="rounded-lg border border-red-900/30 bg-red-900/10 p-4 flex items-center justify-between">
              <div>
                <h4 className="text-sm font-bold text-red-400">清除本地数据</h4>
                <p className="mt-1 text-xs text-red-400/70">清空当前对话历史和产出物文档</p>
              </div>
              <button
                onClick={() => {
                  if (window.confirm('确定要清空所有对话和文档吗？')) {
                    clearHistory();
                    setSettingsOpen(false);
                  }
                }}
                className="flex items-center gap-2 rounded-lg border border-red-900/50 bg-red-900/20 px-4 py-2 text-sm font-bold text-red-400 transition-colors hover:bg-red-900/30"
              >
                <Trash2 className="w-4 h-4" />
                清空数据
              </button>
            </div>
          </section>
        </div>

        <footer className="flex items-center justify-end gap-3 border-t border-slate-800 bg-[#151f2b] px-6 py-4">
          <button
            onClick={() => setSettingsOpen(false)}
            className="flex h-10 items-center justify-center rounded-lg bg-blue-600 px-6 text-sm font-bold text-white shadow-md transition-all hover:bg-blue-500"
          >
            <Save className="w-4 h-4 mr-2" />
            完成
          </button>
        </footer>
      </div>
    </div>
  );
};
