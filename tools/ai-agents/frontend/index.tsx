import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ConfigPage from './ConfigPage';
import CompactApp from './CompactApp';

// Simple path-based routing
const getPage = () => {
  const path = window.location.pathname;

  // Check if we're on the config page
  if (path.includes('/config') || path.endsWith('/config')) {
    return <ConfigPage />;
  }

  // Check if we're on the compact page
  if (path.includes('/compact') || path.endsWith('/compact')) {
    return <CompactApp />;
  }

  // Default to the main assistant app
  return <App />;
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