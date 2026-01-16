/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_WEB_DEMO_MODE?: string;
  readonly VITE_DESKTOP_DOWNLOAD_WIN?: string;
  readonly VITE_DESKTOP_DOWNLOAD_MAC?: string;
  readonly VITE_DESKTOP_DOWNLOAD_LINUX?: string;
  readonly VITE_DESKTOP_PROTOCOL?: string;
  readonly VITE_WEB_FLASHER_URL?: string;
  readonly DEV: boolean;
  readonly MODE: string;
  readonly PROD: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

