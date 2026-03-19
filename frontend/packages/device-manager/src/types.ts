/**
 * Type definitions for device manager
 */

export interface DeviceInfo {
  serial: string;
  manufacturer?: string;
  model?: string;
  codename?: string;
  state: 'disconnected' | 'unauthorized' | 'device' | 'fastboot' | 'recovery';
  connectionType: 'usb' | 'wireless';
  lastSeen?: Date;
}

export interface DeviceProperties {
  codename: string;
  deviceName: string;
  version?: string;
  buildId?: string;
  unlocked?: boolean;
  slotCount?: number;
}

export interface ConnectionOptions {
  timeout?: number;
  retryAttempts?: number;
}

export type DeviceConnectionCallback = (device: DeviceInfo) => void;
export type DeviceDisconnectionCallback = (serial: string) => void;

