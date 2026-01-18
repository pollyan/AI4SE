import React from 'react';
import ReactDOM from 'react-dom/client';
import ConfigPage from './ConfigPage';
import CompactApp from './CompactApp';

import "@assistant-ui/styles/index.css";

// Simple path-based routing
const getPage = () => {
  const path = window.location.pathname;

  // Check if we're on the config page
  if (path.includes('/config') || path.endsWith('/config')) {
    return <ConfigPage />;
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