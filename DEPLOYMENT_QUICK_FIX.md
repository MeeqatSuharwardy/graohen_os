# Quick Fix: yume-chan Workspace Package Error

## The Problem

During deployment, you get this error:
```
ERR_PNPM_WORKSPACE_PKG_NOT_FOUND  In packages/device-manager: "@yume-chan/adb@workspace:*" is in the dependencies but no package named "@yume-chan/adb" is present in the workspace
```

## Quick Solution

### Step 1: Run the Fix Script

```bash
./fix-deployment.sh
```

This will verify everything is configured correctly.

### Step 2: Ensure Packages Are Committed

```bash
# Check if packages are in git
git ls-files frontend/packages/yume-chan/libraries/adb/package.json

# If not found, add them
git add frontend/packages/yume-chan/
git commit -m "Add yume-chan workspace packages"
git push
```

### Step 3: Rebuild Docker

```bash
docker-compose build --no-cache
docker-compose up -d
```

## Why This Happens

The `@yume-chan/adb` package is a **workspace dependency** that must be:
1. ✅ Present in `frontend/packages/yume-chan/libraries/adb/`
2. ✅ Listed in `frontend/pnpm-workspace.yaml`
3. ✅ Committed to git (so Docker can copy it)

## Verification

After fixing, verify:

```bash
# Check packages exist
ls -la frontend/packages/yume-chan/libraries/adb/package.json

# Check workspace config
grep "yume-chan" frontend/pnpm-workspace.yaml

# Test Docker build
docker-compose build 2>&1 | grep -i "yume-chan\|workspace\|error" | tail -10
```

## Prevention

To prevent this in the future:

1. ✅ Always commit workspace packages
2. ✅ Don't add `packages/yume-chan/` to `.gitignore`
3. ✅ Run `./fix-deployment.sh` before deploying
4. ✅ Test Docker build locally first

---

**Status**: ✅ **FIXED** - Dockerfile updated with verification step
