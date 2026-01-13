import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ConfigPage from './ConfigPage';

// Simple path-based routing
const getPage = () => {
  const path = window.location.pathname;

  // Check if we're on the config page
  if (path.includes('/config') || path.endsWith('/config')) {
    return <ConfigPage />;
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