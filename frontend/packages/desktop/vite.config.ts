import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, './src') },
      { find: '@flashdash/ui', replacement: path.resolve(__dirname, '../ui/src') },
      { find: '@flashdash/ui/styles/globals.css', replacement: path.resolve(__dirname, '../ui/src/styles/globals.css') },
    ],
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 5174,
  },
  build: {
    outDir: 'dist',
  },
  optimizeDeps: {
    include: ['@flashdash/ui'],
  },
});

