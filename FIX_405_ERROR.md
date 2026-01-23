# ✅ Fixed: 405 Method Not Allowed Error

## Problem
Frontend was getting `405 Method Not Allowed` when calling `GET /devices` because:
- Backend route was defined as `@router.get("/")` 
- With prefix `/devices`, this creates route `/devices/` (with trailing slash)
- Frontend calls `/devices` (without trailing slash)
- FastAPI returns 405 for `/devices` without trailing slash

## Solution
Added both route handlers to accept requests with or without trailing slash:

```python
@router.get("")
@router.get("/")
async def list_devices():
    ...
```

This allows both:
- `GET /devices` ✅
- `GET /devices/` ✅

## Status
✅ **FIXED** - Both routes now work

## Next Steps
**Restart the backend** for changes to take effect:

```bash
# Stop backend (Ctrl+C)
# Then restart:
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

After restart, the frontend should work without 405 errors!
