import React from 'react';
import { Header } from '../components/Header';
import { ChatPane } from '../components/ChatPane';
import { ArtifactPane } from '../components/ArtifactPane';
import { SettingsModal } from '../components/SettingsModal';

export function Workspace() {

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
