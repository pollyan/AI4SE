import React, { Suspense, useCallback, useEffect, useRef, useState } from 'react';
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

type ConfigCheckStatus = 'idle' | 'checking' | 'error';

export function Workspace() {
    const navigate = useNavigate();
    const { agentId, workflowId } = useParams();
    const {
        setWorkflow,
        chatHistory,
        restoreRunSnapshot,
        configRefreshSeq,
        setSettingsOpen,
    } = useStore();
    const [showOnboarding, setShowOnboarding] = useState(false);
    const [configCheckStatus, setConfigCheckStatus] = useState<ConfigCheckStatus>('idle');
    const [configCheckMessage, setConfigCheckMessage] = useState('');
    const configCheckSeqRef = useRef(0);

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

    const checkDefaultConfig = useCallback(async () => {
        const requestSeq = configCheckSeqRef.current + 1;
        configCheckSeqRef.current = requestSeq;
        if (chatHistory.length > 0) {
            setShowOnboarding(false);
            setConfigCheckStatus('idle');
            setConfigCheckMessage('');
            return;
        }

        setConfigCheckStatus('checking');
        setConfigCheckMessage('正在检查默认模型配置...');

        try {
            const response = await fetch('/new-agents/api/config');
            if (configCheckSeqRef.current !== requestSeq) return;
            if (!response.ok) {
                setShowOnboarding(true);
                setConfigCheckStatus('error');
                setConfigCheckMessage('默认模型配置检查失败，请稍后重试。');
                return;
            }

            const data = await response.json();
            if (configCheckSeqRef.current !== requestSeq) return;
            if (data.hasDefault === true) {
                setShowOnboarding(false);
                setConfigCheckStatus('idle');
                setConfigCheckMessage('');
                return;
            }

            setShowOnboarding(true);
            setConfigCheckStatus('idle');
            setConfigCheckMessage('尚未检测到可用的默认模型配置。');
        } catch {
            if (configCheckSeqRef.current !== requestSeq) return;
            setShowOnboarding(true);
            setConfigCheckStatus('error');
            setConfigCheckMessage('无法连接后端配置服务，请检查服务状态后重试。');
        }
    }, [chatHistory.length]);

    // P0-10: First-time usage detection
    // Check if backend has the default LLM config required by Agent Runtime.
    useEffect(() => {
        checkDefaultConfig();
    }, [checkDefaultConfig, configRefreshSeq]);

    return (
        <div className="flex h-[100dvh] min-h-0 w-full flex-col overflow-hidden bg-[#0B1120] text-slate-200 font-sans antialiased selection:bg-blue-500/30 selection:text-white">
            <Header />
            <main className="relative flex min-h-0 flex-1 overflow-hidden">
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
                                    当前主 Agent 只能通过后端结构化 Agent Runtime 调用模型。请先维护后端默认 LLM 配置，至少包含 API Key、Base URL 和模型名称。
                                </p>
                            </div>

                            <div className="bg-[#0f1623] rounded-xl p-5 text-left space-y-3 border border-[#1e293b]">
                                <h3 className="text-sm font-bold text-slate-200">推荐处理路径</h3>
                                <ul className="text-xs text-slate-400 space-y-2">
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        直接打开模型设置，维护后端默认 LLM 配置
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        保存后检测连接，确认当前模型可访问
                                    </li>
                                    <li className="flex items-center gap-2">
                                        <span className="text-emerald-400">&#10003;</span>
                                        配置可用后自动回到当前工作流继续生成
                                    </li>
                                </ul>
                                {configCheckMessage && (
                                    <p className={`rounded-lg border px-3 py-2 text-xs ${
                                        configCheckStatus === 'error'
                                            ? 'border-amber-700/50 bg-amber-950/30 text-amber-200'
                                            : 'border-slate-700 bg-slate-950/40 text-slate-400'
                                    }`}>
                                        {configCheckMessage}
                                    </p>
                                )}
                                <p className="text-[10px] text-slate-500 pt-2 border-t border-[#1e293b]">
                                    前端不会绕过后端结构化 Agent Runtime；API Key 只会提交到后端默认配置，不会在页面回显。
                                </p>
                            </div>

                            <div className="grid gap-3 pt-2 sm:grid-cols-2">
                                <button
                                    onClick={() => setSettingsOpen(true)}
                                    className="w-full rounded-xl bg-blue-600 hover:bg-blue-500 text-white py-3 text-sm font-bold transition-all shadow-lg shadow-blue-500/20"
                                >
                                    打开模型设置
                                </button>
                                <button
                                    onClick={checkDefaultConfig}
                                    disabled={configCheckStatus === 'checking'}
                                    className="w-full rounded-xl border border-slate-700 bg-slate-900/70 py-3 text-sm font-bold text-slate-100 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    {configCheckStatus === 'checking' ? '正在检查...' : '重新检查配置'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
