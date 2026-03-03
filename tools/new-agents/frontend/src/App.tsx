import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AgentSelect } from './pages/AgentSelect';
import { WorkflowSelect } from './pages/WorkflowSelect';
import { Workspace } from './pages/Workspace';

export default function App() {
  return (
    <BrowserRouter basename="/new-agents">
      <Routes>
        <Route path="/" element={<AgentSelect />} />
        <Route path="/workflows/:agentId" element={<WorkflowSelect />} />
        <Route path="/workspace/:agentId/:workflowId" element={<Workspace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
