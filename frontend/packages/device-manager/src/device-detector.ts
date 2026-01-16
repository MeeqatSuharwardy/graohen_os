/**
 * Device Detector - WebUSB device detection
 */

import type { DeviceInfo, DeviceConnectionCallback, DeviceDisconnectionCallback } from './types';

export class DeviceDetector {
  private devices: Map<string, DeviceInfo> = new Map();
  private connectionCallbacks: Set<DeviceConnectionCallback> = new Set();
  private disconnectionCallbacks: Set<DeviceDisconnectionCallback> = new Set();
  private watchInterval?: number;

  /**
   * Check if WebUSB is supported in the current browser
   */
  static isSupported(): boolean {
    return 'usb' in navigator && typeof navigator.usb !== 'undefined';
  }

  /**
   * Request USB device access (triggers browser permission dialog)
   */
  async requestDevice(): Promise<USBDevice | null> {
    if (!DeviceDetector.isSupported()) {
      throw new Error('WebUSB is not supported in this browser. Please use Chrome/Edge or Chromium-based browser.');
    }

    try {
      const device = await navigator.usb.requestDevice({
        filters: [
          // Google devices (Pixel, Nexus)
          { vendorId: 0x18d1 },
          // Generic Android devices
          { classCode: 0xff, subclassCode: 0x42 },
        ],
      });
      return device;
    } catch (error: any) {
      if (error.name === 'NotFoundError') {
        return null; // User cancelled selection
      }
      throw error;
    }
  }

  /**
   * Get all previously authorized USB devices
   */
  async getUSBDevices(): Promise<USBDevice[]> {
    if (!DeviceDetector.isSupported()) {
      return [];
    }

    try {
      return await navigator.usb.getDevices();
    } catch (error) {
      console.error('Error getting USB devices:', error);
      return [];
    }
  }

  /**
   * Start watching for device connections/disconnections
   */
  startWatching(intervalMs: number = 2000): void {
    if (this.watchInterval) {
      return;
    }

    this.watchInterval = window.setInterval(async () => {
      await this.checkDevices();
    }, intervalMs);

    // Also listen to USB connect/disconnect events if available
    if (DeviceDetector.isSupported()) {
      navigator.usb.addEventListener('connect', (event: any) => {
        this.handleDeviceConnected(event.device);
      });

      navigator.usb.addEventListener('disconnect', (event: any) => {
        this.handleDeviceDisconnected(event.device);
      });
    }

    // Initial check
    this.checkDevices();
  }

  /**
   * Stop watching for device changes
   */
  stopWatching(): void {
    if (this.watchInterval) {
      clearInterval(this.watchInterval);
      this.watchInterval = undefined;
    }
  }

  /**
   * Check for connected devices
   */
  private async checkDevices(): Promise<void> {
    const usbDevices = await this.getUSBDevices();
    const currentSerials = new Set<string>();

    for (const usbDevice of usbDevices) {
      // Extract serial number (if available)
      const serial = this.getDeviceSerial(usbDevice);
      if (!serial) continue;

      currentSerials.add(serial);

      if (!this.devices.has(serial)) {
        const deviceInfo: DeviceInfo = {
          serial,
          manufacturer: usbDevice.manufacturerName,
          model: usbDevice.productName,
          state: 'disconnected',
          connectionType: 'usb',
          lastSeen: new Date(),
        };

        this.devices.set(serial, deviceInfo);
        this.notifyConnection(deviceInfo);
      } else {
        // Update last seen
        const existing = this.devices.get(serial)!;
        existing.lastSeen = new Date();
      }
    }

    // Check for disconnected devices
    for (const [serial] of this.devices) {
      if (!currentSerials.has(serial)) {
        this.devices.delete(serial);
        this.notifyDisconnection(serial);
      }
    }
  }

  /**
   * Extract device serial number from USB device
   */
  private getDeviceSerial(device: USBDevice): string {
    // Try to get serial number from device
    // Note: This may require device to be opened first
    return device.serialNumber || `usb-${device.vendorId}-${device.productId}`;
  }

  /**
   * Handle device connection event
   */
  private handleDeviceConnected(device: USBDevice): void {
    const serial = this.getDeviceSerial(device);
    const deviceInfo: DeviceInfo = {
      serial,
      manufacturer: device.manufacturerName,
      model: device.productName,
      state: 'disconnected',
      connectionType: 'usb',
      lastSeen: new Date(),
    };

    this.devices.set(serial, deviceInfo);
    this.notifyConnection(deviceInfo);
  }

  /**
   * Handle device disconnection event
   */
  private handleDeviceDisconnected(device: USBDevice): void {
    const serial = this.getDeviceSerial(device);
    this.devices.delete(serial);
    this.notifyDisconnection(serial);
  }

  /**
   * Register callback for device connections
   */
  onDeviceConnected(callback: DeviceConnectionCallback): () => void {
    this.connectionCallbacks.add(callback);
    return () => this.connectionCallbacks.delete(callback);
  }

  /**
   * Register callback for device disconnections
   */
  onDeviceDisconnected(callback: DeviceDisconnectionCallback): () => void {
    this.disconnectionCallbacks.add(callback);
    return () => this.disconnectionCallbacks.delete(callback);
  }

  /**
   * Notify all connection callbacks
   */
  private notifyConnection(device: DeviceInfo): void {
    this.connectionCallbacks.forEach((callback) => callback(device));
  }

  /**
   * Notify all disconnection callbacks
   */
  private notifyDisconnection(serial: string): void {
    this.disconnectionCallbacks.forEach((callback) => callback(serial));
  }

  /**
   * Get all currently tracked devices
   */
  getDevices(): DeviceInfo[] {
    return Array.from(this.devices.values());
  }
}

