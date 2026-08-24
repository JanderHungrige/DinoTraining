/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Set by `tauri dev` when developing against a physical device on the LAN.
const host = process.env['TAURI_DEV_HOST'];

export default defineConfig({
  plugins: [react()],

  // Tauri owns the terminal; wiping it hides Rust compiler output.
  clearScreen: false,

  server: {
    port: 1420,
    // A silent port change would leave the Tauri window pointing at nothing.
    strictPort: true,
    host: host ?? false,
    hmr: host ? { protocol: 'ws', host, port: 1421 } : undefined,
    // src-tauri is watched by cargo, not Vite — watching it double-triggers rebuilds.
    watch: { ignored: ['**/src-tauri/**'] },
  },

  envPrefix: ['VITE_', 'TAURI_ENV_'],

  build: {
    // Matches the webview floor Tauri v2 targets.
    target: 'es2021',
    sourcemap: true,
  },

  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
