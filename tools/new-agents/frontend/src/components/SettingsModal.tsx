import React, { FormEvent, useEffect, useState } from 'react';
import { useStore } from '../store';
import { Activity, KeyRound, Settings, X, Save, Trash2 } from 'lucide-react';

type ConfigStatus = 'idle' | 'loading' | 'saving' | 'checking' | 'saved' | 'error';

const readString = (value: unknown): string => (
  typeof value === 'string' ? value : ''
);

export const SettingsModal: React.FC = () => {
  const {
    isSettingsOpen,
    setSettingsOpen,
    clearHistory,
    notifyDefaultLlmConfigChanged,
  } = useStore();
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [description, setDescription] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState<ConfigStatus>('idle');
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    if (!isSettingsOpen) return;

    let isCurrent = true;
    setStatus('loading');
    setStatusMessage('');

    fetch('/new-agents/api/config')
      .then(async response => {
        if (!response.ok) {
          throw new Error('配置读取失败');
        }
        return response.json();
      })
      .then(data => {
        if (!isCurrent) return;
        if (data.hasDefault === true) {
          setBaseUrl(readString(data.baseUrl));
          setModel(readString(data.model));
          setDescription(readString(data.description));
        } else {
          setBaseUrl('https://api.openai.com/v1');
          setModel('');
          setDescription('');
        }
        setApiKey('');
        setStatus('idle');
      })
      .catch(() => {
        if (!isCurrent) return;
        setStatus('error');
        setStatusMessage('配置读取失败');
      });

    return () => {
      isCurrent = false;
    };
  }, [isSettingsOpen]);

  const buildConfigPayload = (): {
    baseUrl: string;
    model: string;
    description: string;
    apiKey?: string;
  } => {
    const payload: {
      baseUrl: string;
      model: string;
      description: string;
      apiKey?: string;
    } = {
      baseUrl: baseUrl.trim(),
      model: model.trim(),
      description: description.trim(),
    };
    if (apiKey.trim()) {
      payload.apiKey = apiKey.trim();
    }
    return payload;
  };

  const handleSaveConfig = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus('saving');
    setStatusMessage('');

    const payload = buildConfigPayload();

    try {
      const response = await fetch('/new-agents/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(readString(data.error) || '配置保存失败');
      }
      setBaseUrl(readString(data.baseUrl));
      setModel(readString(data.model));
      setDescription(readString(data.description));
      setApiKey('');
      setStatus('saved');
      setStatusMessage('配置已保存');
      notifyDefaultLlmConfigChanged();
    } catch (error) {
      setStatus('error');
      setStatusMessage(error instanceof Error ? error.message : '配置保存失败');
    }
  };

  const handleCheckConfig = async () => {
    setStatus('checking');
    setStatusMessage('');

    try {
      const response = await fetch('/new-agents/api/config/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildConfigPayload()),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(readString(data.error) || '模型检测失败');
      }
      setStatus(data.ok === true ? 'saved' : 'error');
      setStatusMessage(readString(data.message) || '模型检测完成');
    } catch (error) {
      setStatus('error');
      setStatusMessage(error instanceof Error ? error.message : '模型检测失败');
    }
  };

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

            <form onSubmit={handleSaveConfig} className="space-y-4 rounded-lg border border-slate-700 bg-slate-900/40 p-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-500/10 text-blue-300">
                  <KeyRound className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-100">后端默认 LLM 配置</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">
                    API Key 只会提交到后端保存；已存在的密钥不会回显，留空时保留当前密钥。
                  </p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block text-xs font-semibold text-slate-300">
                  Base URL
                  <input
                    value={baseUrl}
                    onChange={event => setBaseUrl(event.target.value)}
                    className="mt-2 w-full rounded-lg border border-slate-700 bg-[#0b1120] px-3 py-2 text-sm text-slate-100 outline-none transition-colors focus:border-blue-500"
                    placeholder="https://api.openai.com/v1"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-300">
                  模型名称
                  <input
                    value={model}
                    onChange={event => setModel(event.target.value)}
                    className="mt-2 w-full rounded-lg border border-slate-700 bg-[#0b1120] px-3 py-2 text-sm text-slate-100 outline-none transition-colors focus:border-blue-500"
                    placeholder="gpt-4.1"
                  />
                </label>
              </div>

              <label className="block text-xs font-semibold text-slate-300">
                描述
                <input
                  value={description}
                  onChange={event => setDescription(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-[#0b1120] px-3 py-2 text-sm text-slate-100 outline-none transition-colors focus:border-blue-500"
                  placeholder="本地默认模型配置"
                />
              </label>

              <label className="block text-xs font-semibold text-slate-300">
                新 API Key
                <input
                  value={apiKey}
                  onChange={event => setApiKey(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-[#0b1120] px-3 py-2 text-sm text-slate-100 outline-none transition-colors focus:border-blue-500"
                  placeholder="留空则不更换现有密钥"
                  type="password"
                />
              </label>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className={`text-xs ${
                  status === 'error'
                    ? 'text-red-300'
                    : status === 'saved'
                      ? 'text-emerald-300'
                      : 'text-slate-500'
                }`}>
                  {status === 'loading' ? '正在读取配置' : statusMessage}
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCheckConfig}
                    disabled={status === 'checking'}
                    className="flex h-9 items-center justify-center rounded-lg border border-slate-700 px-4 text-sm font-bold text-slate-200 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Activity className="mr-2 h-4 w-4" />
                    检测连接
                  </button>
                  <button
                    type="submit"
                    disabled={status === 'saving'}
                    className="flex h-9 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-bold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Save className="mr-2 h-4 w-4" />
                    保存配置
                  </button>
                </div>
              </div>
            </form>
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
