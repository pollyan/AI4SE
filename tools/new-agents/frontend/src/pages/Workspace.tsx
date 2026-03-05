import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Header } from '../components/Header';
import { ChatPane } from '../components/ChatPane';
import { ArtifactPane } from '../components/ArtifactPane';
import { SettingsModal } from '../components/SettingsModal';
import { useStore, SLUG_TO_WORKFLOW } from '../store';

export function Workspace() {
    const { workflowId } = useParams();
    const { workflow, setWorkflow } = useStore();

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
            <main className="flex flex-1 overflow-hidden relative">
                <ChatPane />
                <ArtifactPane />
            </main>
            <SettingsModal />
        </div>
    );
}
