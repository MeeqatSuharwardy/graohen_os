import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5175,
    strictPort: true,
    // HTTPS required for WebUSB (but can use localhost for development)
    // Note: WebUSB works on localhost without HTTPS
    https: false, // Set to true if using custom domain in development
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    // Base path for production - serves at /flash route
    base: process.env.NODE_ENV === 'production' ? '/flash/' : '/',
  },
});

