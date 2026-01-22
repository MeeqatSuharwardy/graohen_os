# Deployment Troubleshooting Guide

## Common Deployment Errors and Solutions

### Error: `ERR_PNPM_WORKSPACE_PKG_NOT_FOUND` for `@yume-chan/adb`

**Error Message**:
```
ERR_PNPM_WORKSPACE_PKG_NOT_FOUND  In packages/device-manager: "@yume-chan/adb@workspace:*" is in the dependencies but no package named "@yume-chan/adb" is present in the workspace
```

**Cause**: The `@yume-chan/adb` workspace package is not present during Docker build.

**Solution**:

#### Step 1: Verify yume-chan Packages Are Committed

```bash
# Check if packages are in git
git ls-files frontend/packages/yume-chan/libraries/adb/package.json

# If not found, add them
git add frontend/packages/yume-chan/
git commit -m "Add yume-chan workspace packages"
git push
```

#### Step 2: Verify .gitignore Doesn't Exclude Them

Check `.gitignore` doesn't have:
```
packages/yume-chan/
**/yume-chan/
```

#### Step 3: Rebuild Docker

```bash
docker-compose build --no-cache
docker-compose up -d
```

#### Step 4: Verify Workspace Configuration

Check `frontend/pnpm-workspace.yaml` includes:
```yaml
packages:
  - 'packages/*'
  - 'apps/*'
  - 'packages/yume-chan/libraries/*'  # This line is required
```

### Error: Frontend Can't Connect to Backend

**Symptoms**: Frontend loads but API calls fail

**Solution**:
1. Check backend is running: `docker logs flashdash | grep backend`
2. Verify API URL in frontend build matches backend
3. Check CORS headers in nginx config

### Error: Build Files Missing

**Symptoms**: Downloads return 404

**Solution**:
```bash
# Verify files exist
./check-builds.sh

# If missing, rebuild
cd frontend/packages/desktop
pnpm build:win
pnpm build:mac
pnpm build:linux

# Copy to downloads
./copy-builds.sh
```

### Error: Port Already in Use

**Symptoms**: Docker container won't start

**Solution**:
```bash
# Check what's using the port
sudo lsof -i :80
sudo lsof -i :8000

# Stop conflicting service or change ports in docker-compose.yml
```

### Error: Permission Denied

**Symptoms**: Can't access USB devices or files

**Solution**:
```bash
# Check Docker permissions
docker exec flashdash ls -la /app/bundles

# Fix permissions
sudo chmod -R 755 bundles downloads logs
```

## Pre-Deployment Checklist

Before deploying, verify:

- [ ] yume-chan packages are committed to git
- [ ] `.gitignore` doesn't exclude workspace packages
- [ ] `pnpm-workspace.yaml` includes yume-chan libraries
- [ ] Build files exist (`./check-builds.sh`)
- [ ] Docker builds successfully locally
- [ ] All environment variables are set

## Quick Fix Script

Create `fix-deployment.sh`:

```bash
#!/bin/bash
set -e

echo "Fixing deployment issues..."

# Check yume-chan packages
if [ ! -f "frontend/packages/yume-chan/libraries/adb/package.json" ]; then
    echo "ERROR: yume-chan packages not found!"
    echo "Please ensure they're committed to git."
    exit 1
fi

# Verify workspace config
if ! grep -q "packages/yume-chan/libraries/\*" frontend/pnpm-workspace.yaml; then
    echo "ERROR: pnpm-workspace.yaml missing yume-chan configuration!"
    exit 1
fi

# Rebuild
echo "Rebuilding Docker..."
docker-compose build --no-cache

echo "✅ Deployment fix complete!"
```

---

**For more details**: See `DEPLOYMENT_FIX.md` and `FINAL_DEPLOYMENT_GUIDE.md`
