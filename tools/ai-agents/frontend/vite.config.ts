/// <reference types="vitest" />
import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    // Production build will be deployed at /ai-agents/
    base: '/ai-agents/',
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        // Proxy API requests to Flask backend (running via Docker/Nginx on port 80)
        '/ai-agents/api': {
          target: 'http://127.0.0.1',
          changeOrigin: true,
        },
      },
    },
    plugins: [react()],
    define: {
      // API keys are no longer needed in frontend - all AI calls go through backend
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './tests/setupTests.ts',
      css: true,
    }
  };
});
