# Fix: Frontend Local Development Error

## Error
```
ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL  @flashdash/web-flasher@1.0.0 dev: `vite`
spawn ENOENT
WARN   Local package.json exists, but node_modules missing, did you mean to install?
```

## Solution

### Step 1: Install Dependencies

```bash
cd frontend
pnpm install
```

### Step 2: Create Environment File

```bash
echo "VITE_API_BASE_URL=http://localhost:8000" > apps/web-flasher/.env
```

### Step 3: Start Frontend

```bash
# Option 1: Using pnpm filter
pnpm --filter @flashdash/web-flasher dev

# Option 2: Using the start script
cd /Users/vt_dev/upwork_graphene/graohen_os
./start-frontend.sh

# Option 3: Using the fix script
./fix-frontend-setup.sh
```

## Quick Fix Script

Run this to fix everything at once:

```bash
cd /Users/vt_dev/upwork_graphene/graohen_os
./fix-frontend-setup.sh
```

Then start the frontend:

```bash
cd frontend
pnpm --filter @flashdash/web-flasher dev
```

## Verify Setup

After running `pnpm install`, check:

```bash
# Check node_modules exists
ls -la frontend/apps/web-flasher/node_modules

# Check .env file
cat frontend/apps/web-flasher/.env

# Should show:
# VITE_API_BASE_URL=http://localhost:8000
```

## Common Issues

### Issue: `spawn ENOENT` error
**Solution**: Make sure `vite` is installed. Run `pnpm install` again.

### Issue: `node_modules missing`
**Solution**: 
```bash
cd frontend
rm -rf node_modules apps/*/node_modules packages/*/node_modules
pnpm install
```

### Issue: Port already in use
**Solution**: 
```bash
# Find process using port 5173
lsof -i :5173

# Kill process or use different port
# Vite will automatically use next available port
```

## Complete Local Setup

### Terminal 1: Backend
```bash
cd /Users/vt_dev/upwork_graphene/graohen_os/backend/py-service
source venv/bin/activate  # or create venv first
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd /Users/vt_dev/upwork_graphene/graohen_os/frontend
pnpm --filter @flashdash/web-flasher dev
```

## Expected Output

When frontend starts successfully, you should see:

```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

Then open `http://localhost:5173` in your browser.
