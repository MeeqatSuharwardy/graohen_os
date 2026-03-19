/**
 * Type definitions for flasher package
 */

export type FlashState =
  | 'idle'
  | 'device_connected'
  | 'build_selected'
  | 'downloading'
  | 'download_complete'
  | 'rebooting_to_bootloader'
  | 'fastboot_mode'
  | 'unlocking_bootloader'
  | 'flashing'
  | 'flash_complete'
  | 'rebooting'
  | 'complete'
  | 'error'
  | 'device_disconnected';

export interface FlashProgress {
  state: FlashState;
  step: string;
  progress: number; // 0-100
  message: string;
  currentImage?: string;
  totalImages?: number;
  currentImageIndex?: number;
}

export interface BuildInfo {
  codename: string;
  version: string;
  url: string;
  size: number;
  sha256?: string;
}

export interface FlashOptions {
  deviceSerial: string;
  build: BuildInfo;
  skipUnlock?: boolean;
  onProgress?: (progress: FlashProgress) => void;
  onLog?: (message: string, level?: 'info' | 'warning' | 'error') => void;
}

export interface DownloadProgress {
  downloaded: number;
  total: number;
  progress: number; // 0-100
}

