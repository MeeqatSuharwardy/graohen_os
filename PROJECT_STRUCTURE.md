# FlashDash Project Structure

## Complete File Tree

```
repo-root/
├── .gitignore
├── README.md
├── PROJECT_STRUCTURE.md
├── scripts/
│   ├── setup.sh
│   └── dev.sh
│
├── frontend/
│   ├── pnpm-workspace.yaml
│   ├── package.json
│   ├── .env.example
│   │
│   └── packages/
│       ├── ui/
│       │   ├── package.json
│       │   ├── tsconfig.json
│       │   ├── tsconfig.node.json
│       │   ├── tsup.config.ts
│       │   ├── tailwind.config.js
│       │   ├── postcss.config.js
│       │   └── src/
│       │       ├── index.ts
│       │       ├── lib/
│       │       │   └── utils.ts
│       │       ├── components/
│       │       │   ├── button.tsx
│       │       │   ├── card.tsx
│       │       │   ├── input.tsx
│       │       │   ├── label.tsx
│       │       │   ├── badge.tsx
│       │       │   ├── alert.tsx
│       │       │   ├── dialog.tsx
│       │       │   ├── select.tsx
│       │       │   ├── tabs.tsx
│       │       │   ├── progress.tsx
│       │       │   ├── separator.tsx
│       │       │   └── skeleton.tsx
│       │       └── styles/
│       │           └── globals.css
│       │
│       ├── desktop/
│       │   ├── package.json
│       │   ├── tsconfig.json
│       │   ├── tsconfig.node.json
│       │   ├── tsconfig.electron.json
│       │   ├── vite.config.ts
│       │   ├── electron-builder.config.js
│       │   ├── index.html
│       │   ├── electron/
│       │   │   ├── main.ts
│       │   │   ├── preload.ts
│       │   │   └── preload.js
│       │   └── src/
│       │       ├── main.tsx
│       │       ├── App.tsx
│       │       ├── components/
│       │       │   └── Layout.tsx
│       │       ├── pages/
│       │       │   └── Dashboard.tsx
│       │       └── lib/
│       │           └── api.ts
│       │
│       └── web/
│           ├── package.json
│           ├── tsconfig.json
│           ├── tsconfig.node.json
│           ├── vite.config.ts
│           ├── index.html
│           └── src/
│               ├── main.tsx
│               ├── App.tsx
│               ├── components/
│               │   └── Layout.tsx
│               ├── pages/
│               │   ├── Landing.tsx
│               │   ├── Demo.tsx
│               │   └── Dashboard.tsx
│               └── lib/
│                   └── api.ts
│
└── backend/
    └── py-service/
        ├── requirements.txt
        ├── pyproject.toml
        ├── README.md
        ├── .env.example
        └── app/
            ├── __init__.py
            ├── main.py
            ├── config.py
            ├── utils/
            │   ├── __init__.py
            │   ├── tools.py
            │   ├── bundles.py
            │   └── flash.py
            └── routes/
                ├── __init__.py
                ├── devices.py
                ├── bundles.py
                ├── flash.py
                ├── source.py
                └── build.py
```

## Key Features Implemented

### Backend (Python FastAPI)
- ✅ Health check endpoint
- ✅ Tools availability check
- ✅ Device detection (ADB/Fastboot)
- ✅ Device identification (codename detection)
- ✅ Bundle indexing and verification
- ✅ Flash job management with SSE streaming
- ✅ Source status checking
- ✅ Build job placeholder (Linux only)

### Frontend - Desktop (Electron)
- ✅ Electron main process with Python service management
- ✅ IPC bridge for service control
- ✅ Custom protocol handler (`flashdash://open`)
- ✅ Dashboard with device detection
- ✅ Premium dark theme with animations
- ✅ Service status monitoring

### Frontend - Web
- ✅ Premium landing page with OS detection
- ✅ Download CTAs with correct platform links
- ✅ Custom protocol handler fallback
- ✅ Demo mode with mocked data
- ✅ Read-only dashboard (no flashing)

### Shared UI Library
- ✅ Complete shadcn/ui component set
- ✅ TailwindCSS with dark theme
- ✅ Framer Motion animations
- ✅ Responsive design

## Environment Configuration

All paths and settings are configured via `.env` files:
- `backend/py-service/.env` - Backend configuration
- `frontend/packages/desktop/.env` - Desktop app config
- `frontend/packages/web/.env` - Web app config

See `.env.example` files for required variables.

## Next Steps

1. **Configure Environment**: Copy `.env.example` files and set your paths
2. **Install Dependencies**: Run `./scripts/setup.sh` or manual setup
3. **Start Development**: Run `./scripts/dev.sh` or start services manually
4. **Test**: Connect a Pixel device and test device detection
5. **Build**: Use `pnpm -C frontend build` for production builds

## Safety Features

- ✅ Typed confirmation required for flashing
- ✅ Dry-run mode by default
- ✅ Bundle verification (SHA256)
- ✅ Unsupported device detection
- ✅ No runtime downloads (all bundles local)

