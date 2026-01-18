import React from 'react';
import ReactDOM from 'react-dom/client';
import ConfigPage from './ConfigPage';
import CompactApp from './CompactApp';
import { DebugChat } from './components/debug/DebugChat';

// import "@assistant-ui/styles/index.css"; // Removed

// Simple path-based routing
const getPage = () => {
  const path = window.location.pathname;

  // Check if we're on the config page
  if (path.includes('/config') || path.endsWith('/config')) {
    return <ConfigPage />;
  }

  // Debug page
  if (path.includes('/debug') || path.endsWith('/debug')) {
    return <DebugChat />;
  }

  // 默认使用紧凑型页面
  return <CompactApp />;
};

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    {getPage()}
  </React.StrictMode>
);