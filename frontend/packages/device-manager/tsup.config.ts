import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: {
    // Skip type checking for yume-chan packages during build
    // They are workspace packages and will be resolved at runtime
    compilerOptions: {
      skipLibCheck: true,
    },
  },
  splitting: false,
  sourcemap: true,
  clean: true,
  external: ['@yume-chan/adb', '@yume-chan/adb-backend-webusb'],
});

