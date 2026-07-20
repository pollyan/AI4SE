/// <reference types="vitest" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { readFileSync, unlinkSync } from 'node:fs';
import path from 'path';
import { defineConfig, loadEnv } from 'vite';

import { buildNewAgentsDevProxy } from './devServerProxy';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const proxyApiKeyFile = env.NEW_AGENTS_PROXY_API_KEY_FILE?.trim();
  let proxyApiKey: string | undefined;
  if (proxyApiKeyFile) {
    proxyApiKey = readFileSync(proxyApiKeyFile, 'utf-8').trim();
    unlinkSync(proxyApiKeyFile);
    if (!proxyApiKey) {
      throw new Error('New Agents proxy authentication file is empty');
    }
  }
  return {
    base: '/new-agents/',
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      proxy: buildNewAgentsDevProxy(
        env.NEW_AGENTS_BACKEND_URL,
        proxyApiKey,
      ),
    },
    test: {
      environment: 'jsdom',
      globals: true,
    },
  };
});
