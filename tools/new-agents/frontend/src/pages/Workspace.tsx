import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Header } from '../components/Header';
import { ChatPane } from '../components/ChatPane';
import { ArtifactPane } from '../components/ArtifactPane';
import { SettingsModal } from '../components/SettingsModal';
import { useStore, WorkflowType } from '../store';

const WORKFLOW_ID_MAP: Record<string, WorkflowType> = {
    'test-design': 'TEST_DESIGN',
    'req-review': 'REQ_REVIEW',
    'incident-review': 'INCIDENT_REVIEW',
};

export function Workspace() {
    const { workflowId } = useParams();
    const { workflow, setWorkflow } = useStore();

    useEffect(() => {
        if (workflowId) {
            const targetWorkflow = WORKFLOW_ID_MAP[workflowId];
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
