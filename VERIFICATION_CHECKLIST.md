# Deployment Verification Checklist

Use this checklist to verify everything is working after deployment.

## ✅ Downloads Page

- [ ] Navigate to `/downloads` route
- [ ] Page loads without errors
- [ ] Platform detection works (shows recommended build)
- [ ] All three platform cards display (Windows, macOS, Linux)
- [ ] Windows download link works (points to configured URL)
- [ ] "All Downloads" button on landing page works
- [ ] System requirements section displays correctly

## ✅ Electron Builds

- [ ] `build-all.sh` script is executable
- [ ] Windows build completes: `pnpm build:win`
- [ ] macOS build completes: `pnpm build:mac` (macOS only)
- [ ] Linux build completes: `pnpm build:linux`
- [ ] Builds are in `dist/` directory
- [ ] Builds can be copied to `downloads/` folder

## ✅ Docker Deployment

- [ ] Dockerfile builds successfully: `docker build -t flashdash .`
- [ ] docker-compose starts: `docker-compose up -d`
- [ ] Container is running: `docker ps | grep flashdash`
- [ ] Backend health check: `curl http://localhost:8000/health`
- [ ] Frontend accessible: `curl http://localhost/`
- [ ] Web flasher accessible: `curl http://localhost/flash`
- [ ] API proxy works: `curl http://localhost/api/health`
- [ ] Verification script passes: `./docker/verify.sh`

## ✅ API Documentation

- [ ] `API_DOCUMENTATION.md` exists
- [ ] All endpoint sections are present:
  - [ ] Flash endpoints
  - [ ] Devices endpoints
  - [ ] Bundles endpoints
  - [ ] APKs endpoints
  - [ ] Source endpoints
  - [ ] Build endpoints
- [ ] Request/response examples included
- [ ] Error handling documented

## ✅ Vercel Configuration

- [ ] `vercel.json` exists
- [ ] Frontend build configuration correct
- [ ] Route rewrites configured for `/flash`
- [ ] API proxy configured
- [ ] Security headers included

## ✅ File Structure

- [ ] `downloads/` folder exists with subdirectories:
  - [ ] `downloads/windows/`
  - [ ] `downloads/mac/`
  - [ ] `downloads/linux/`
  - [ ] `downloads/README.md`
- [ ] `docker/` folder exists with:
  - [ ] `nginx.conf`
  - [ ] `nginx-site.conf`
  - [ ] `start.sh`
  - [ ] `verify.sh`
- [ ] Root files exist:
  - [ ] `Dockerfile`
  - [ ] `docker-compose.yml`
  - [ ] `vercel.json`
  - [ ] `.dockerignore`
  - [ ] `API_DOCUMENTATION.md`
  - [ ] `DOCKER_DEPLOYMENT.md`
  - [ ] `DEPLOYMENT_SUMMARY.md`

## ✅ Code Integration

- [ ] Downloads page component: `frontend/packages/web/src/pages/Downloads.tsx`
- [ ] Route added to `App.tsx`: `/downloads`
- [ ] Landing page has "All Downloads" button
- [ ] Build script: `frontend/packages/desktop/scripts/build-all.sh`
- [ ] All imports resolve correctly
- [ ] No TypeScript errors
- [ ] No linting errors

## ✅ Environment Variables

- [ ] Windows download URL configured (default or env var)
- [ ] macOS download URL can be set via env var
- [ ] Linux download URL can be set via env var
- [ ] API base URL configured for production

## Quick Test Commands

```bash
# Test Downloads page route
curl http://localhost/ | grep -i downloads

# Test Docker health
./docker/verify.sh

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/devices

# Test frontend build
cd frontend && pnpm build:web

# Test Electron build (Windows)
cd frontend/packages/desktop && pnpm build:win
```

## Post-Deployment

After deployment, verify:

1. **Production URLs work:**
   - Frontend: https://yourdomain.com/
   - Downloads: https://yourdomain.com/downloads
   - Web Flasher: https://yourdomain.com/flash
   - API: https://api.yourdomain.com/health

2. **Download links are accessible:**
   - Windows download URL is reachable
   - macOS download URL is reachable (if configured)
   - Linux download URL is reachable (if configured)

3. **Docker container (if used):**
   - Container logs show no errors
   - Health checks pass
   - All services running

4. **Vercel deployment (if used):**
   - Build completes successfully
   - Routes work correctly
   - Environment variables set

## Troubleshooting

If any item fails:

1. Check logs: `docker-compose logs` or `vercel logs`
2. Verify file paths and permissions
3. Check environment variables
4. Review error messages in browser console
5. Test endpoints individually with curl
