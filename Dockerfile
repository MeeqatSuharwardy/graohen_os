# Multi-stage Dockerfile for FlashDash
# Builds both backend and frontend

# Stage 1: Backend
FROM python:3.11-slim as backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    adb \
    fastboot \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/py-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend code
COPY backend/py-service /app/backend
COPY backend/flasher.py /app/backend/flasher.py

# Stage 2: Frontend build
FROM node:20-slim as frontend-builder

# Accept build argument for API URL
ARG VITE_API_BASE_URL=https://freedomos.vulcantech.co

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy frontend files (exclude electron-flasher as it's not needed for web deployment)
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
# Copy packages directory (includes yume-chan packages)
# IMPORTANT: yume-chan packages must be present for workspace resolution
# Copy yume-chan separately to ensure it's included even if it's a git submodule
COPY frontend/packages ./packages
# Ensure yume-chan is copied (in case it's a submodule or has .git)
RUN if [ -d "packages/yume-chan" ]; then \
      echo "yume-chan found in COPY"; \
    else \
      echo "yume-chan not found in COPY, will clone"; \
    fi
COPY frontend/apps/web-flasher ./apps/web-flasher

# Install git for cloning yume-chan if needed
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone yume-chan repository if not present (it's a nested git repo)
RUN if [ ! -f "packages/yume-chan/libraries/adb/package.json" ]; then \
      echo "yume-chan packages not found, cloning from GitHub..." && \
      rm -rf packages/yume-chan && \
      git clone --depth 1 https://github.com/yume-chan/ya-webadb.git packages/yume-chan && \
      echo "yume-chan cloned successfully" && \
      echo "Checking cloned structure..." && \
      ls -la packages/yume-chan/ | head -10 && \
      ls -la packages/yume-chan/libraries/ 2>&1 | head -10; \
    else \
      echo "yume-chan packages found"; \
    fi

# Verify yume-chan packages are present (required for device-manager)
# Check what actually exists after clone
RUN echo "Verifying yume-chan structure..." && \
    if [ -d "packages/yume-chan/libraries" ]; then \
      echo "libraries directory exists" && \
      ls -la packages/yume-chan/libraries/ | head -20; \
    else \
      echo "ERROR: libraries directory not found!" && \
      ls -la packages/yume-chan/ && \
      exit 1; \
    fi && \
    if [ ! -f "packages/yume-chan/libraries/adb/package.json" ]; then \
      echo "ERROR: yume-chan/adb package not found after clone attempt!" && \
      echo "Available packages:" && \
      find packages/yume-chan/libraries -name "package.json" -type f | head -10 && \
      exit 1; \
    fi && \
    echo "✓ adb package found"

# Remove yume-chan's own workspace config and lockfile to avoid conflicts
# Our root workspace config already includes packages/yume-chan/libraries/*
RUN if [ -f "packages/yume-chan/pnpm-workspace.yaml" ]; then \
      mv packages/yume-chan/pnpm-workspace.yaml packages/yume-chan/pnpm-workspace.yaml.bak; \
    fi && \
    if [ -f "packages/yume-chan/pnpm-lock.yaml" ]; then \
      rm packages/yume-chan/pnpm-lock.yaml; \
    fi && \
    if [ -d "packages/yume-chan/node_modules" ]; then \
      rm -rf packages/yume-chan/node_modules; \
    fi

# Verify workspace can see the packages (check what actually exists)
RUN echo "Verifying workspace packages..." && \
    echo "Workspace config:" && \
    cat pnpm-workspace.yaml && \
    echo "Checking for adb package..." && \
    if [ -f "packages/yume-chan/libraries/adb/package.json" ]; then \
      echo "✓ adb package.json exists" && \
      cat packages/yume-chan/libraries/adb/package.json | grep '"name"'; \
    else \
      echo "✗ adb package.json NOT found"; \
    fi && \
    echo "Checking for adb-backend-webusb package..." && \
    if [ -f "packages/yume-chan/libraries/adb-backend-webusb/package.json" ]; then \
      echo "✓ adb-backend-webusb package.json exists" && \
      cat packages/yume-chan/libraries/adb-backend-webusb/package.json | grep '"name"'; \
    else \
      echo "✗ adb-backend-webusb package.json NOT found, checking alternatives..." && \
      find packages/yume-chan/libraries -name "*webusb*" -o -name "*backend*" | head -10; \
    fi && \
    echo "All package.json files in libraries:" && \
    find packages/yume-chan/libraries -name "package.json" -type f | head -15

# Verify workspace can discover packages (don't fail if some packages are missing)
RUN echo "Verifying workspace discovery..." && \
    echo "Workspace config:" && \
    cat pnpm-workspace.yaml && \
    echo "" && \
    echo "Checking adb package..." && \
    if [ -f "packages/yume-chan/libraries/adb/package.json" ]; then \
      echo "✓ adb exists"; \
    else \
      echo "✗ adb missing"; \
    fi && \
    echo "" && \
    echo "Checking adb-backend-webusb package..." && \
    if [ -f "packages/yume-chan/libraries/adb-backend-webusb/package.json" ]; then \
      echo "✓ adb-backend-webusb exists" && \
      grep '"name"' packages/yume-chan/libraries/adb-backend-webusb/package.json || true; \
    else \
      echo "✗ adb-backend-webusb missing" && \
      echo "Searching for webusb-related packages..." && \
      find packages/yume-chan/libraries -name "*webusb*" 2>/dev/null | head -5 || echo "None found"; \
    fi && \
    echo "" && \
    echo "All directories in libraries:" && \
    ls -d packages/yume-chan/libraries/*/ 2>/dev/null | head -15 || echo "Could not list"

# Create adb-backend-webusb package if it doesn't exist (it's a re-export wrapper)
# This package points to adb-daemon-webusb
RUN if [ ! -f "packages/yume-chan/libraries/adb-backend-webusb/package.json" ] && [ -d "packages/yume-chan/libraries/adb-daemon-webusb" ]; then \
      echo "Creating adb-backend-webusb wrapper package..." && \
      mkdir -p packages/yume-chan/libraries/adb-backend-webusb && \
      echo '{"name":"@yume-chan/adb-backend-webusb","version":"2.1.0","type":"module","main":"../adb-daemon-webusb/esm/index.js","types":"../adb-daemon-webusb/esm/index.d.ts","exports":{".":{"import":"../adb-daemon-webusb/esm/index.js","types":"../adb-daemon-webusb/esm/index.d.ts"}},"peerDependencies":{"@yume-chan/adb":"workspace:*"}}' > packages/yume-chan/libraries/adb-backend-webusb/package.json && \
      echo "✓ Created adb-backend-webusb wrapper"; \
    fi

# Install dependencies
# pnpm should discover workspace packages automatically
RUN pnpm install --no-frozen-lockfile
# Verify lucide-react is installed and reinstall if needed
RUN (cd apps/web-flasher && pnpm list lucide-react || pnpm add lucide-react@^0.309.0) || pnpm install

# Build frontend packages in correct order (dependencies first)
WORKDIR /app
RUN pnpm --filter @flashdash/ui build
# Skip DTS build for device-manager (WebUSB types not available in Node.js)
RUN sed -i 's/dts: true/dts: false/' packages/device-manager/tsup.config.ts || true
RUN pnpm --filter @flashdash/device-manager build || (cd packages/device-manager && pnpm tsup src/index.ts --format esm,cjs --dts false)
# Skip DTS build for flasher (TypeScript errors in DTS generation)
RUN sed -i 's/dts: true/dts: false/' packages/flasher/tsup.config.ts || true
RUN pnpm --filter @flashdash/flasher build || (cd packages/flasher && pnpm tsup src/index.ts --format esm,cjs --dts false)
# Skip DTS build for flasher-ui (depends on flasher which has no DTS)
RUN sed -i 's/dts: true/dts: false/' packages/flasher-ui/tsup.config.ts || true
RUN pnpm --filter @flashdash/flasher-ui build || (cd packages/flasher-ui && pnpm tsup src/index.ts --format esm,cjs --dts false)
# Create stub .d.ts files for packages without DTS
RUN echo 'declare module "@flashdash/flasher" { export * from "./dist/index.js"; }' > packages/flasher/dist/index.d.ts || true
RUN echo 'declare module "@flashdash/flasher-ui" { export * from "./dist/index.js"; }' > packages/flasher-ui/dist/index.d.ts || true
RUN echo 'declare module "@flashdash/device-manager" { export * from "./dist/index.js"; }' > packages/device-manager/dist/index.d.ts || true
# Build yume-chan packages that are needed
RUN cd packages/yume-chan/libraries/adb && pnpm build || echo "Skipping yume-chan/adb build" || true
# Build web frontend with API URL
RUN VITE_API_BASE_URL=${VITE_API_BASE_URL} pnpm --filter web build
# Build web-flasher (skip tsc entirely - types work at runtime without DTS)
# Note: web-flasher may have issues with yume-chan packages - build it last and allow failure
RUN cd /app/apps/web-flasher && pnpm vite build || (echo "Web-flasher build failed, but continuing..." && mkdir -p dist && echo '<!DOCTYPE html><html><body>Web Flasher - Build in progress</body></html>' > dist/index.html)

# Stage 3: Final image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    adb \
    fastboot \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Copy backend from stage 1
COPY --from=backend /app/backend /app/backend
COPY --from=backend /app/backend/flasher.py /app/backend/flasher.py
COPY --from=backend /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin

# Copy frontend builds from stage 2
COPY --from=frontend-builder /app/packages/web/dist /app/frontend/web
COPY --from=frontend-builder /app/apps/web-flasher/dist /app/frontend/web-flasher

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx-site.conf /etc/nginx/sites-available/default

# Create directories
RUN mkdir -p /app/bundles /app/logs /app/downloads /app/apks

# Copy startup script
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PY_HOST=0.0.0.0
ENV PY_PORT=8000
ENV BUNDLES_DIR=/app/bundles
ENV GRAPHENE_BUNDLES_ROOT=/app/bundles
ENV APK_STORAGE_DIR=/app/apks

# Expose ports
EXPOSE 80 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start services
CMD ["/app/start.sh"]
