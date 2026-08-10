import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Build → CALIFORNIAN_ID/src/californian_id/data/frontend/
// Backend serves index.html at /live and assets at /live/assets/*.
const outDir = resolve(__dirname, '../src/californian_id/data/frontend');

export default defineConfig({
  plugins: [svelte()],
  base: '/live/',
  build: {
    outDir,
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8765',
      '/ws': {
        target: 'ws://127.0.0.1:8766',
        ws: true
      }
    }
  }
});
