/**
 * Device Manager - WebADB integration for device operations
 */

import type { DeviceInfo, DeviceProperties, ConnectionOptions } from './types';
import { DeviceDetector } from './device-detector';

export interface ADBDevice {
  serial: string;
  state: 'device' | 'offline' | 'unauthorized' | 'fastboot';
}

export class DeviceManager {
  private detector: DeviceDetector;
  private adbDevices: Map<string, ADBDevice> = new Map();
  private connectedDevice: any = null; // WebADB AdbDaemonWebSocketConnection

  constructor() {
    this.detector = new DeviceDetector();
  }

  /**
   * Check if WebUSB is supported
   */
  static isSupported(): boolean {
    return DeviceDetector.isSupported();
  }

  /**
   * Request device connection (triggers browser permission)
   */
  async requestDevice(): Promise<USBDevice | null> {
    return this.detector.requestDevice();
  }

  /**
   * Connect to device via WebADB
   */
  async connectDevice(serial: string, options: ConnectionOptions = {}): Promise<void> {
    if (!DeviceManager.isSupported()) {
      throw new Error('WebUSB is not supported. Please use Chrome/Edge or Chromium-based browser.');
    }

    try {
      // Note: Full WebADB implementation would use @yume-chan/adb-backend-webusb
      // This is a simplified version - full implementation would require proper WebADB setup
      const usbDevices = await (this.detector as any).getUSBDevices();
      const device = usbDevices.find(d => this.detector.getDeviceSerial(d) === serial);

      if (!device) {
        throw new Error(`Device ${serial} not found`);
      }

      // TODO: Implement full WebADB connection using @yume-chan/adb-backend-webusb
      // For now, we'll use a placeholder that indicates the device is available
      this.connectedDevice = { serial, device };

      // Update device state
      const deviceInfo = this.detector.getDevices().find(d => d.serial === serial);
      if (deviceInfo) {
        deviceInfo.state = 'device';
      }
    } catch (error: any) {
      throw new Error(`Failed to connect to device: ${error.message}`);
    }
  }

  /**
   * Get device properties via ADB
   */
  async getDeviceProperties(serial: string): Promise<DeviceProperties | null> {
    if (!this.connectedDevice || this.connectedDevice.serial !== serial) {
      await this.connectDevice(serial);
    }

    // TODO: Implement actual ADB command execution via WebADB
    // This would use: await adb.getProp('ro.product.device')
    
    // Placeholder implementation
    return {
      codename: 'unknown',
      deviceName: 'Unknown Device',
    };
  }

  /**
   * Reboot device to bootloader
   */
  async rebootToBootloader(serial: string): Promise<void> {
    // TODO: Implement via WebADB
    // await adb.reboot('bootloader')
    throw new Error('Not implemented - requires WebADB setup');
  }

  /**
   * Check if device is in fastboot mode
   */
  async isFastbootMode(serial: string): Promise<boolean> {
    // TODO: Check via WebUSB/Fastboot backend
    return false;
  }

  /**
   * Start device detection
   */
  startDetection(): void {
    this.detector.startWatching(2000);
  }

  /**
   * Stop device detection
   */
  stopDetection(): void {
    this.detector.stopWatching();
  }

  /**
   * Get all detected devices
   */
  getDevices(): DeviceInfo[] {
    return this.detector.getDevices();
  }

  /**
   * Register device connection callback
   */
  onDeviceConnected(callback: (device: DeviceInfo) => void): () => void {
    return this.detector.onDeviceConnected(callback);
  }

  /**
   * Register device disconnection callback
   */
  onDeviceDisconnected(callback: (serial: string) => void): () => void {
    return this.detector.onDeviceDisconnected(callback);
  }

  /**
   * Disconnect current device
   */
  disconnect(): void {
    this.connectedDevice = null;
  }
}

