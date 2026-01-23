# Fix: yume-chan Build Errors

## Problem

When building `@flashdash/device-manager`, you get errors:
- `Cannot find module '@yume-chan/adb'`
- `Cannot find module '@yume-chan/adb-backend-webusb'`
- `Cannot find name 'USBDevice'`

## Solution

The `yume-chan` packages are workspace dependencies that don't need to be built separately. The build errors occur because:

1. TypeScript is trying to type-check these packages during build
2. DOM types aren't included for `USBDevice`

## Fix Applied

### 1. Updated `tsup.config.ts`

Added `skipLibCheck: true` and marked yume-chan packages as external:

```typescript
export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: {
    compilerOptions: {
      skipLibCheck: true,
    },
  },
  external: ['@yume-chan/adb', '@yume-chan/adb-backend-webusb'],
  // ... rest of config
});
```

### 2. Updated `tsconfig.json`

Added DOM types to lib array:

```json
{
  "compilerOptions": {
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "types": ["node"]
  }
}
```

## Build Command

Now you can build device-manager:

```bash
cd /root/graohen_os/frontend
pnpm --filter @flashdash/device-manager build
```

## Complete Build Order

```bash
cd /root/graohen_os/frontend

# Build in order
pnpm --filter @flashdash/ui build
pnpm --filter @flashdash/device-manager build  # Now works!
pnpm --filter @flashdash/flasher build
pnpm --filter @flashdash/flasher-ui build
pnpm --filter @flashdash/web-flasher build
```

Or use the convenience script:

```bash
pnpm build:web-flasher
```

## Why This Works

- `skipLibCheck: true` tells TypeScript to skip type checking of declaration files
- `external` tells tsup not to bundle these packages (they're workspace dependencies)
- DOM types are needed for `USBDevice` which is a browser API

The yume-chan packages are already in the workspace and will be resolved at runtime, so we don't need to build them separately.
