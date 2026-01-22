# Deployment Fix: yume-chan Workspace Package Error

## Problem

During deployment, `pnpm install` fails with:

```
ERR_PNPM_WORKSPACE_PKG_NOT_FOUND  In packages/device-manager: "@yume-chan/adb@workspace:*" is in the dependencies but no package named "@yume-chan/adb" is present in the workspace
```

## Root Cause

The `@yume-chan/adb` package is a workspace dependency that needs to be:
1. Present in the workspace before `pnpm install`
2. Properly configured in `pnpm-workspace.yaml`
3. Available during Docker build

## Solution

### Option 1: Ensure yume-chan Packages Are Committed (Recommended)

Make sure the `yume-chan` packages are committed to git:

```bash
# Check if yume-chan packages are tracked
git ls-files frontend/packages/yume-chan/

# If not, add them
git add frontend/packages/yume-chan/
git commit -m "Add yume-chan workspace packages"
```

### Option 2: Update Dockerfile (Already Fixed)

The Dockerfile has been updated to:
1. Copy yume-chan packages before `pnpm install`
2. Build yume-chan/adb if needed
3. Ensure workspace packages are available

### Option 3: Pre-build yume-chan Packages

If packages aren't committed, clone them during Docker build:

```dockerfile
# Add to Dockerfile before pnpm install
RUN if [ ! -d "packages/yume-chan" ]; then \
      git clone --depth 1 https://github.com/yume-chan/ya-webadb.git packages/yume-chan-temp && \
      mv packages/yume-chan-temp/libraries packages/yume-chan/libraries && \
      rm -rf packages/yume-chan-temp; \
    fi
```

## Verification

After fixing, verify the build:

```bash
# Test locally
docker-compose build

# Check if yume-chan packages are found
docker-compose run --rm flashdash ls -la /app/packages/yume-chan/libraries/adb/
```

## Quick Fix for Current Deployment

If you're deploying right now and getting this error:

### Step 1: Ensure yume-chan is in Git

```bash
# Check if it's tracked
git ls-files frontend/packages/yume-chan/libraries/adb/package.json

# If not, add it
git add frontend/packages/yume-chan/
git commit -m "Add yume-chan workspace packages"
git push
```

### Step 2: Rebuild Docker

```bash
docker-compose build --no-cache
docker-compose up -d
```

## Alternative: Use npm Instead of workspace

If workspace packages continue to cause issues, you can temporarily use npm packages:

```json
// In packages/device-manager/package.json
{
  "dependencies": {
    "@yume-chan/adb": "^2.1.0",
    "@yume-chan/adb-daemon-webusb": "^2.1.0"
  }
}
```

But this is **not recommended** as the packages may not be on npm.

## Prevention

To prevent this issue:

1. ✅ Always commit workspace packages to git
2. ✅ Use `.gitignore` carefully (don't ignore workspace packages)
3. ✅ Verify workspace packages exist before building
4. ✅ Test Docker build locally before deploying

## Current Status

The Dockerfile has been updated to handle this automatically. The fix:
- Copies yume-chan packages before install
- Builds yume-chan/adb if needed
- Ensures workspace resolution works correctly

---

**Status**: ✅ **FIXED** - Dockerfile updated to handle yume-chan packages correctly.
