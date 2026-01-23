# 🔧 Backend Import Error Fix

## Problem

The backend service is failing with a circular import error:

```
ImportError: cannot import name 'index_bundles' from partially initialized module 'app.utils.bundles'
```

## Root Cause

This is typically caused by:
1. **Python cache files** (`.pyc` files) containing old code
2. **Stale bytecode** in `__pycache__` directories
3. **File system sync issues** between local and server

## Solution

### Quick Fix (Run on Server)

```bash
cd /root/graohen_os/backend/py-service

# Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# Restart service
systemctl restart flashdash-backend.service

# Check status
systemctl status flashdash-backend.service
```

### Automated Fix Script

Use the provided script:

```bash
# On server
cd /root/graohen_os
bash fix-backend-import-error.sh
```

### Manual Verification

Test imports manually:

```bash
cd /root/graohen_os/backend/py-service
source venv/bin/activate

python3 -c "
import sys
sys.path.insert(0, '.')
from app.utils.bundles import index_bundles
from app.routes import bundles
print('✅ Imports successful')
"
```

## Verification

After fixing, check service logs:

```bash
# View recent logs
journalctl -u flashdash-backend.service -n 50 --no-pager

# Follow logs in real-time
journalctl -u flashdash-backend.service -f
```

## Expected Output

After restart, you should see:

```
✅ flashdash-backend.service: Started successfully
✅ Application startup complete
```

## Prevention

To prevent this issue:

1. **Always clear cache after code changes**:
   ```bash
   find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
   ```

2. **Restart service after updates**:
   ```bash
   systemctl restart flashdash-backend.service
   ```

3. **Use git to track changes**:
   ```bash
   git status
   git diff
   ```

## Troubleshooting

If the issue persists:

1. **Check file permissions**:
   ```bash
   ls -la /root/graohen_os/backend/py-service/app/utils/bundles.py
   ls -la /root/graohen_os/backend/py-service/app/routes/bundles.py
   ```

2. **Verify Python path**:
   ```bash
   cd /root/graohen_os/backend/py-service
   source venv/bin/activate
   python3 -c "import sys; print('\n'.join(sys.path))"
   ```

3. **Check for syntax errors**:
   ```bash
   python3 -m py_compile app/utils/bundles.py
   python3 -m py_compile app/routes/bundles.py
   ```

4. **Verify imports manually**:
   ```bash
   cd /root/graohen_os/backend/py-service
   source venv/bin/activate
   python3 -c "from app.utils.bundles import index_bundles; print('OK')"
   ```

---

**Last Updated**: 2025-01-23
**Script**: `fix-backend-import-error.sh`
