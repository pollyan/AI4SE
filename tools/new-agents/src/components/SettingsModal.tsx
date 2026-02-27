import React from 'react';
import { useStore, WORKFLOWS, WorkflowType } from '../store';
import { Settings, X, Key, Save, Trash2, Globe } from 'lucide-react';

export const SettingsModal: React.FC = () => {
  const {
    isSettingsOpen,
    setSettingsOpen,
    apiKey,
    setApiKey,
    model,
    setModel,
    baseUrl,
    setBaseUrl,
    workflow,
    setWorkflow,
    clearHistory,
    isUserConfigured,
    resetToSystemConfig
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
              <p className="text-xs font-medium text-slate-400">管理 API Key 与工作流</p>
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
              {isUserConfigured && (
                <button
                  onClick={resetToSystemConfig}
                  className="text-xs font-bold text-blue-400 hover:text-blue-300 transition-colors"
                >
                  恢复系统默认配置
                </button>
              )}
            </div>

            {!isUserConfigured && (
              <div className="rounded-lg border border-blue-900/30 bg-blue-900/10 p-3 mb-4">
                <p className="text-xs text-blue-300">
                  💡 系统已内置默认模型，无需配置即可直接体验。
                  如需使用自己的 API Key (或更改配置)，请在下方填写以覆盖默认设置。
                </p>
              </div>
            )}
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-300">API Key</label>
                <div className="relative flex items-center">
                  <Key className="absolute left-3 w-5 h-5 text-slate-500" />
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="不填则使用系统默认内置 API Key"
                    className="w-full rounded-lg border border-slate-700 bg-[#101922] py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-300">Base URL</label>
                <div className="relative flex items-center">
                  <Globe className="absolute left-3 w-5 h-5 text-slate-500" />
                  <input
                    type="text"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="例如: https://api.deepseek.com/v1"
                    className="w-full rounded-lg border border-slate-700 bg-[#101922] py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-300">模型名称</label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="例如: gemini-3-flash-preview, deepseek-chat, gpt-4o"
                  className="w-full rounded-lg border border-slate-700 bg-[#101922] py-2.5 px-3 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          </section>

          <section>
            <h3 className="mb-4 text-sm font-bold text-slate-200 uppercase tracking-wider">工作流配置</h3>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-300">当前工作流</label>
              <select
                value={workflow}
                onChange={(e) => setWorkflow(e.target.value as WorkflowType)}
                className="w-full rounded-lg border border-slate-700 bg-[#101922] py-2.5 px-3 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {Object.values(WORKFLOWS).map(wf => (
                  <option key={wf.id} value={wf.id}>{wf.name}</option>
                ))}
              </select>
              <p className="mt-2 text-xs text-yellow-500">注意：切换工作流将清空当前对话历史和产出物。</p>
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
