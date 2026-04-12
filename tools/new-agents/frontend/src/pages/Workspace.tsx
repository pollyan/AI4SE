import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Header } from '../components/Header';
import { ChatPane } from '../components/ChatPane';
import { ArtifactPane } from '../components/ArtifactPane';
import { SettingsModal } from '../components/SettingsModal';
import { useStore, SLUG_TO_WORKFLOW } from '../store';

export function Workspace() {
    const { workflowId } = useParams();
    const { workflow, setWorkflow, isUserConfigured, setSettingsOpen, chatHistory } = useStore();
    const [showOnboarding, setShowOnboarding] = useState(false);
    const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);

    useEffect(() => {
        if (workflowId) {
            const targetWorkflow = SLUG_TO_WORKFLOW[workflowId];
            if (targetWorkflow && targetWorkflow !== workflow) {
                setWorkflow(targetWorkflow);
            }
        }
    }, [workflowId]);

    // P0-10: First-time usage detection
    // Check if backend is available and user has no API config
    useEffect(() => {
        if (isUserConfigured) {
            setShowOnboarding(false);
            return;
        }
        // If user already has chat history, don't show onboarding
        if (chatHistory.length > 0) {
            setShowOnboarding(false);
            return;
        }

        // Check backend availability
        const checkBackend = async () => {
            try {
                const res = await fetch('/new-agents/api/config');
                if (res.ok) {
                    const data = await res.json();
                    if (data.hasDefault) {
                        // Backend has default config, no need for onboarding
                        setBackendAvailable(true);
                        setShowOnboarding(false);
                    } else {
                        // Backend has no default config, user needs to configure
                        setBackendAvailable(false);
                        setShowOnboarding(true);
                    }
                } else {
                    setBackendAvailable(false);
                    setShowOnboarding(true);
                }
            } catch {
                // Backend unreachable
                setBackendAvailable(false);
                setShowOnboarding(true);
            }
        };

        checkBackend();
    }, [isUserConfigured, chatHistory.length]);

    return (
        <div className="flex flex-col h-screen w-full bg-[#0B1120] text-slate-200 font-sans overflow-hidden antialiased selection:bg-blue-500/30 selection:text-white">
            <Header />
            <main className="flex flex-1 overflow-hidden relative">
                <ChatPane />
                <ArtifactPane />
            </main>
            <SettingsModal />

            {/* P0-10: First-time setup guide overlay */}
            {showOnboarding && !isUserConfigured && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
                    <div className="flex w-full max-w-lg flex-col overflow-hidden rounded-2xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10">
                        <div className="p-8 text-center space-y-6">
                            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-500 shadow-[0_0_30px_-5px_rgba(59,130,246,0.3)]">
                                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-white mb-2">配置你的 AI 模型</h2>
                                <p className="text-slate-400 text-sm leading-relaxed max-w-md mx-auto">
                                    系统后端暂未配置默认 LLM 模型。要开始使用，你需要配置自己的 API Key 才能与 AI 对话。
                                </p>
                            </div>

                            <div className="bg-[#0f1623] rounded-xl p-5 text-left space-y-3 border border-[#1e293b]">
                                <h3 className="text-sm font-bold text-slate-200">支持的模型服务商</h3>
                                <ul className="text-xs text-slate-400 space-y-2">
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        Google Gemini（免费额度可用）
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        OpenAI / GPT 系列
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        DeepSeek 等兼容 OpenAI 格式的服务商
                                    </li>
                                </ul>
                                <p className="text-[10px] text-slate-500 pt-2 border-t border-[#1e293b]">
                                    &#128274; 你的 API Key 仅保存在浏览器本地 (LocalStorage)，不会上传到服务器。
                                </p>
                            </div>

                            <div className="flex flex-col gap-3 pt-2">
                                <button
                                    onClick={() => {
                                        setShowOnboarding(false);
                                        setSettingsOpen(true);
                                    }}
                                    className="w-full rounded-xl bg-blue-600 hover:bg-blue-500 text-white py-3 text-sm font-bold transition-all shadow-lg shadow-blue-500/20"
                                >
                                    立即配置 API Key
                                </button>
                                <button
                                    onClick={() => setShowOnboarding(false)}
                                    className="text-xs text-slate-500 hover:text-slate-400 transition-colors"
                                >
                                    稍后再说
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
