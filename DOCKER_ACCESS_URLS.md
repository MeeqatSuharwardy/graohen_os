# Docker Access URLs

## ✅ Working URLs

### Frontend (Main Web App)
- **URL**: http://localhost/
- **Status**: ✅ Working
- **Assets**: ✅ CSS and JS files loading correctly

### Backend API
- **Base URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs
- **Status**: ✅ Working

### Web Flasher
- **URL**: http://localhost/flash
- **Status**: ⚠️ Fallback page (build had issues)

## API Endpoints

### Via Nginx Proxy (http://localhost)
- **Devices**: http://localhost/devices
- **Bundles**: http://localhost/bundles
- **Flash**: http://localhost/flash/execute
- **Health**: http://localhost/health
- **Tools Check**: http://localhost/tools/check

### Direct Backend (http://localhost:8000)
- **Devices**: http://localhost:8000/devices
- **Bundles**: http://localhost:8000/bundles
- **Flash**: http://localhost:8000/flash/execute
- **Health**: http://localhost:8000/health
- **Tools Check**: http://localhost:8000/tools/check

## Quick Test

```bash
# Test frontend
curl http://localhost/

# Test backend
curl http://localhost:8000/health

# Test assets
curl http://localhost/assets/index-DMFSSwUO.css
curl http://localhost/assets/index-DvW-wTnM.js
```

## Browser Access

Open in your browser:
- **Frontend**: http://localhost/
- **Backend API Docs**: http://localhost:8000/docs

---

**All services are operational!** ✅
