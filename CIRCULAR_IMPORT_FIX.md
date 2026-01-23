# 🔧 Circular Import Fix - bundles.py

## Problem

The server has a circular import in `app/utils/bundles.py`:

```python
# Line 9 (on server)
from ..utils.bundles import (
```

This is trying to import from itself, causing:
```
ImportError: cannot import name 'index_bundles' from partially initialized module 'app.utils.bundles'
```

## Root Cause

The file on the server has an old/bad import statement that doesn't exist in the current codebase. This could be from:
- An old merge conflict
- Manual edit that wasn't synced
- Git merge issue

## Solution

### Option 1: Automated Fix (Recommended)

Run the fix script on the server:

```bash
cd /root/graohen_os
bash fix-bundles-circular-import.sh
```

This script will:
1. Detect the circular import
2. Remove the problematic line
3. Clear Python cache
4. Test the import
5. Restart the service

### Option 2: Manual Fix

```bash
cd /root/graohen_os/backend/py-service

# 1. Check the problematic line
grep -n "from ..utils.bundles import" app/utils/bundles.py

# 2. Remove the line (if found)
sed -i '/from ..utils.bundles import/d' app/utils/bundles.py

# 3. Verify the fix
head -15 app/utils/bundles.py

# Should show:
# import os
# import json
# import httpx
# import hashlib
# import zipfile
# from pathlib import Path
# from typing import List, Dict, Optional, Any
# from datetime import datetime, timedelta
# from ..config import settings

# 4. Clear cache
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null

# 5. Test import
python3 -c "
import sys
sys.path.insert(0, '.')
from app.utils.bundles import index_bundles
print('✅ Import successful')
"

# 6. Restart service
systemctl restart flashdash-backend.service
```

### Option 3: Replace File Entirely

If the file is corrupted, replace it with the correct version:

```bash
cd /root/graohen_os/backend/py-service

# Backup current file
cp app/utils/bundles.py app/utils/bundles.py.backup

# Pull latest from git (if using git)
git checkout app/utils/bundles.py

# OR manually ensure line 9 is:
# from ..config import settings

# Clear cache and restart
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
systemctl restart flashdash-backend.service
```

## Expected File Structure

The first 10 lines of `app/utils/bundles.py` should be:

```python
import os
import json
import httpx
import hashlib
import zipfile
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from ..config import settings
```

**NOT:**
```python
from ..utils.bundles import (  # ❌ WRONG - circular import
```

## Verification

After fixing, verify:

```bash
# 1. Check imports work
cd /root/graohen_os/backend/py-service
python3 -c "
import sys
sys.path.insert(0, '.')
from app.utils.bundles import index_bundles, get_bundle_for_codename
from app.routes import bundles
print('✅ All imports successful')
"

# 2. Check service status
systemctl status flashdash-backend.service --no-pager -l

# 3. Check logs
journalctl -u flashdash-backend.service -n 20 --no-pager
```

## Prevention

To prevent this in the future:

1. **Always sync files properly**:
   ```bash
   git pull  # or rsync/scp from local
   ```

2. **Check for circular imports**:
   ```bash
   grep -r "from.*bundles.*import" app/utils/bundles.py
   ```

3. **Test imports before deploying**:
   ```bash
   python3 -c "from app.utils.bundles import index_bundles"
   ```

---

**Last Updated**: 2025-01-23
**Script**: `fix-bundles-circular-import.sh`
