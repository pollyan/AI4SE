import React, { Suspense, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Header } from '../components/Header';
import { SettingsModal } from '../components/SettingsModal';
import { useStore, SLUG_TO_WORKFLOW, WORKFLOWS } from '../store';
import { fetchRunSnapshot } from '../services/runSnapshotService';

const ChatPane = React.lazy(() =>
    import('../components/ChatPane').then(module => ({ default: module.ChatPane }))
);
const ArtifactPane = React.lazy(() =>
    import('../components/ArtifactPane').then(module => ({ default: module.ArtifactPane }))
);

export function Workspace() {
    const navigate = useNavigate();
    const { agentId, workflowId } = useParams();
    const { setWorkflow, chatHistory, restoreRunSnapshot } = useStore();
    const [showOnboarding, setShowOnboarding] = useState(false);
    const [backendAvailable, setBackendAvailable] = useState<boolean | null>(null);

    useEffect(() => {
        if (workflowId) {
            const targetWorkflow = SLUG_TO_WORKFLOW[workflowId];
            if (!targetWorkflow) {
                navigate('/', { replace: true });
                return;
            }

            const owningAgentId = WORKFLOWS[targetWorkflow].agentId;
            if (agentId && agentId !== owningAgentId) {
                navigate(`/workspace/${owningAgentId}/${workflowId}`, { replace: true });
                return;
            }

            if (targetWorkflow !== useStore.getState().workflow) {
                setWorkflow(targetWorkflow);
            }
        }
    }, [agentId, navigate, setWorkflow, workflowId]);

    useEffect(() => {
        let isCurrent = true;
        const runId = new URLSearchParams(window.location.search).get('runId')?.trim();
        if (!runId || useStore.getState().currentRunId === runId) {
            return () => {
                isCurrent = false;
            };
        }

        fetchRunSnapshot(runId)
            .then((snapshot) => {
                if (!isCurrent) return;
                restoreRunSnapshot(snapshot);
                const snapshotWorkflow = WORKFLOWS[snapshot.run.workflowId];
                const targetWorkspacePath = `/workspace/${snapshot.run.agentId}/${snapshotWorkflow.slug}`;
                const targetPath = `${targetWorkspacePath}?runId=${encodeURIComponent(snapshot.run.id)}`;
                const currentRunId = new URLSearchParams(window.location.search).get('runId');
                const isAlreadyOnTargetWorkspace = (
                    window.location.pathname.endsWith(targetWorkspacePath)
                    && currentRunId === snapshot.run.id
                );
                if (!isAlreadyOnTargetWorkspace) {
                    navigate(targetPath, { replace: true });
                }
            })
            .catch(() => {
                // Keep the current local workspace when snapshot recovery fails.
            });

        return () => {
            isCurrent = false;
        };
    }, [navigate, restoreRunSnapshot]);

    // P0-10: First-time usage detection
    // Check if backend has the default LLM config required by Agent Runtime.
    useEffect(() => {
        let isCurrent = true;

        // If user already has chat history, don't show onboarding
        if (chatHistory.length > 0) {
            setShowOnboarding(false);
            return () => {
                isCurrent = false;
            };
        }

        // Check backend availability
        const checkBackend = async () => {
            try {
                const res = await fetch('/new-agents/api/config');
                if (!isCurrent) return;
                if (res.ok) {
                    const data = await res.json();
                    if (!isCurrent) return;
                    if (data.hasDefault === true) {
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
                if (!isCurrent) return;
                // Backend unreachable
                setBackendAvailable(false);
                setShowOnboarding(true);
            }
        };

        checkBackend();
        return () => {
            isCurrent = false;
        };
    }, [chatHistory.length]);

    return (
        <div className="flex flex-col h-screen w-full bg-[#0B1120] text-slate-200 font-sans overflow-hidden antialiased selection:bg-blue-500/30 selection:text-white">
            <Header />
            <main className="flex flex-1 overflow-hidden relative">
                <Suspense fallback={<div className="flex flex-1 bg-[#0B1120]" />}>
                    <ChatPane />
                    <ArtifactPane />
                </Suspense>
            </main>
            <SettingsModal />

            {/* P0-10: First-time setup guide overlay */}
            {showOnboarding && (
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
                                <h2 className="text-2xl font-bold text-white mb-2">后端默认 LLM 未配置</h2>
                                <p className="text-slate-400 text-sm leading-relaxed max-w-md mx-auto">
                                    当前主 Agent 只能通过后端结构化 Agent Runtime 调用模型。请先在后端默认 LLM 配置中维护 API Key、Base URL 和模型名称。
                                </p>
                            </div>

                            <div className="bg-[#0f1623] rounded-xl p-5 text-left space-y-3 border border-[#1e293b]">
                                <h3 className="text-sm font-bold text-slate-200">配置位置</h3>
                                <ul className="text-xs text-slate-400 space-y-2">
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        后端 `llm_config` 默认配置
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        `NEW_AGENTS_DEFAULT_LLM_API_KEY` 与 `NEW_AGENTS_DEFAULT_LLM_MODEL`
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        `/new-agents/api/config` 返回 `hasDefault: true`
                                    </li>
                                </ul>
                                <p className="text-[10px] text-slate-500 pt-2 border-t border-[#1e293b]">
                                    前端不再保存个人 API Key，也不会绕过后端结构化输出契约。
                                </p>
                            </div>

                            <div className="flex flex-col gap-3 pt-2">
                                <button
                                    onClick={() => setShowOnboarding(false)}
                                    className="w-full rounded-xl bg-blue-600 hover:bg-blue-500 text-white py-3 text-sm font-bold transition-all shadow-lg shadow-blue-500/20"
                                >
                                    我知道了
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
