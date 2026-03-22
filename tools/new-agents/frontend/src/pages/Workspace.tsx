import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { clsx } from 'clsx';
import { Header } from '../components/Header';
import { ChatPane } from '../components/ChatPane';
import { ArtifactPane } from '../components/ArtifactPane';
import { SettingsModal } from '../components/SettingsModal';
import { useStore, SLUG_TO_WORKFLOW } from '../store';

export function Workspace() {
    const { workflowId } = useParams();
    const { workflow, setWorkflow } = useStore();
    const [mobileTab, setMobileTab] = useState<'chat' | 'artifact'>('chat');

    useEffect(() => {
        if (workflowId) {
            const targetWorkflow = SLUG_TO_WORKFLOW[workflowId];
            if (targetWorkflow && targetWorkflow !== workflow) {
                setWorkflow(targetWorkflow);
            }
        }
    }, [workflowId]);

    return (
        <div className="flex flex-col h-screen w-full bg-[#0B1120] text-slate-200 font-sans overflow-hidden antialiased selection:bg-blue-500/30 selection:text-white">
            <Header />
            <main className="flex flex-1 overflow-hidden relative mb-14 md:mb-0">
                <section className={clsx(
                    "flex flex-col w-full lg:w-[40%] bg-[#0B1120] border-r border-[#1e293b] relative shadow-[10px_0_30px_-10px_rgba(0,0,0,0.5)] z-20 h-full",
                    mobileTab === 'chat' ? "flex md:hidden" : "hidden md:flex"
                )}>
                    <ChatPane />
                </section>
                <section className={clsx(
                    "flex flex-col w-full lg:w-[60%] bg-[#0F17] text-gray-300 relative shadow-2xl overflow-hidden bg-grid-pattern h-full",
                    mobileTab === 'artifact' ? "flex md:hidden" : "hidden md:flex"
                )}>
                    <ArtifactPane />
                </section>
            </main>
            {/* 移动端 Tab 切换栏 */}
            <div className="flex md:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#0B1120] border-t border-[#1e293b] px-4 py-2">
                <div className="flex w-full bg-[#0f1623] rounded-xl p-1">
                    <button
                        onClick={() => setMobileTab('chat')}
                        className={clsx(
                            "flex-1 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2",
                            mobileTab === 'chat'
                                ? "bg-blue-600 text-white shadow-md"
                                : "text-slate-400 hover:text-white"
                        )}
                    >
                        💬 对话
                    </button>
                    <button
                        onClick={() => setMobileTab('artifact')}
                        className={clsx(
                            "flex-1 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2",
                            mobileTab === 'artifact'
                                ? "bg-blue-600 text-white shadow-md"
                                : "text-slate-400 hover:text-white"
                        )}
                    >
                        📋 产出物
                    </button>
                </div>
            </div>
            <SettingsModal />
        </div>
    );
}
