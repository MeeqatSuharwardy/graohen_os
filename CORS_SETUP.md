# CORS Configuration - Allow All Origins

## Current Configuration

The backend is configured to allow **all CORS requests** from any origin.

### Configuration Details

**File**: `backend/py-service/app/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=3600,  # Cache preflight for 1 hour
)
```

### What This Means

✅ **All origins allowed** - Any domain can make requests  
✅ **All methods allowed** - GET, POST, PUT, DELETE, OPTIONS, etc.  
✅ **All headers allowed** - Any request header is accepted  
✅ **All headers exposed** - Response headers are accessible  
✅ **OPTIONS preflight handled** - Explicit OPTIONS handler added  

## Testing CORS

### Test from Browser Console

```javascript
// Test GET request
fetch('http://localhost:8000/devices')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);

// Test POST request
fetch('http://localhost:8000/devices', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ test: 'data' })
})
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
```

### Test with curl

```bash
# Test OPTIONS (preflight)
curl -X OPTIONS http://localhost:8000/devices \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v

# Test GET request
curl http://localhost:8000/devices \
  -H "Origin: http://localhost:3000" \
  -v
```

### Expected Headers in Response

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD
Access-Control-Allow-Headers: *
Access-Control-Expose-Headers: *
Access-Control-Max-Age: 3600
```

## Common CORS Issues

### Issue: "No 'Access-Control-Allow-Origin' header"

**Solution**: Restart the backend server after making CORS changes.

```bash
# Stop the server (Ctrl+C)
# Then restart:
cd backend/py-service
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Issue: "Credentials flag is true, but 'Access-Control-Allow-Credentials' header is not set"

**Solution**: If you need credentials, you must specify exact origins instead of `["*"]`:

```python
allow_origins=[
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
],
allow_credentials=True,
```

### Issue: Preflight OPTIONS request fails

**Solution**: The explicit OPTIONS handler should handle this. Make sure the middleware is added before routes.

## Production Considerations

For production, consider restricting origins:

```python
allow_origins=[
    "https://freedomos.vulcantech.co",
    "https://vulcantech.tech",
],
allow_credentials=True,
```

## Verify CORS is Working

1. **Start backend**:
   ```bash
   cd backend/py-service
   source venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

2. **Test endpoint**:
   ```bash
   curl http://localhost:8000/devices -v
   ```

3. **Check headers** - Should see `Access-Control-Allow-Origin: *`

---

**CORS is fully enabled and allows all origins!**
