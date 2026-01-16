/**
 * Device Manager - WebADB integration for device operations
 * Uses @yume-chan/adb libraries for WebUSB/WebADB communication
 */

import type { DeviceInfo, DeviceProperties, ConnectionOptions } from './types';
import { DeviceDetector } from './device-detector';
import type { Adb } from '@yume-chan/adb';

// Lazy import ADB libraries (they may not be available in all environments)
let AdbClass: typeof Adb | null = null;
let AdbWebUsbBackendManagerClass: any = null;

async function loadAdbLibraries() {
  if (AdbClass && AdbWebUsbBackendManagerClass) {
    return { Adb: AdbClass, AdbWebUsbBackendManager: AdbWebUsbBackendManagerClass };
  }

  try {
    const adbModule = await import('@yume-chan/adb');
    const webusbModule = await import('@yume-chan/adb-backend-webusb');
    
    AdbClass = adbModule.Adb;
    AdbWebUsbBackendManagerClass = webusbModule.AdbWebUsbBackendManager;
    
    return {
      Adb: AdbClass,
      AdbWebUsbBackendManager: AdbWebUsbBackendManagerClass,
    };
  } catch (error) {
    console.error('Failed to load ADB libraries:', error);
    throw new Error('ADB libraries not available. Please install @yume-chan/adb and @yume-chan/adb-backend-webusb');
  }
}

export interface ADBDevice {
  serial: string;
  state: 'device' | 'offline' | 'unauthorized' | 'fastboot';
  adb?: Adb;
}

export class DeviceManager {
  private detector: DeviceDetector;
  private adbDevices: Map<string, ADBDevice> = new Map();
  private connectedAdbInstances: Map<string, Adb> = new Map();
  private detectionStarted: boolean = false;
  private usbBackendManager: any = null;

  constructor() {
    this.detector = new DeviceDetector();
    this.initializeUsbManager();
  }

  /**
   * Initialize WebUSB backend manager
   */
  private async initializeUsbManager() {
    try {
      const { AdbWebUsbBackendManager } = await loadAdbLibraries();
      this.usbBackendManager = AdbWebUsbBackendManager.BROWSER;
    } catch (error) {
      console.warn('WebUSB backend manager not available:', error);
    }
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
   * Start device detection
   */
  startDetection(): void {
    if (this.detectionStarted) {
      return;
    }
    this.detector.startWatching(2000);
    this.detectionStarted = true;
  }

  /**
   * Stop device detection
   */
  stopDetection(): void {
    if (!this.detectionStarted) {
      return;
    }
    this.detector.stopWatching();
    this.detectionStarted = false;
  }

  /**
   * Register callback for device connections
   */
  onDeviceConnected(callback: (device: DeviceInfo) => void): () => void {
    return this.detector.onDeviceConnected(callback);
  }

  /**
   * Register callback for device disconnections
   */
  onDeviceDisconnected(callback: (serial: string) => void): () => void {
    return this.detector.onDeviceDisconnected(callback);
  }

  /**
   * Get all detected devices
   */
  getDevices(): DeviceInfo[] {
    return this.detector.getDevices();
  }

  /**
   * Connect to device via WebADB
   * Returns Adb instance for device operations
   */
  async connectDevice(serial: string, options: ConnectionOptions = {}): Promise<Adb> {
    if (!DeviceManager.isSupported()) {
      throw new Error('WebUSB is not supported. Please use Chrome/Edge or Chromium-based browser.');
    }

    // Check if already connected
    if (this.connectedAdbInstances.has(serial)) {
      const adb = this.connectedAdbInstances.get(serial)!;
      return adb;
    }

    try {
      const { Adb } = await loadAdbLibraries();

      if (!this.usbBackendManager) {
        await this.initializeUsbManager();
      }

      if (!this.usbBackendManager) {
        throw new Error('WebUSB backend manager not available');
      }

      // Get USB device
      const usbDevices = await this.detector.getUSBDevices();
      const usbDevice = usbDevices.find(d => {
        const deviceSerial = d.serialNumber || `usb-${d.vendorId}-${d.productId}`;
        return deviceSerial === serial;
      });

      if (!usbDevice) {
        throw new Error(`USB device ${serial} not found. Please request device access first.`);
      }

      // Create WebUSB backend
      const backend = this.usbBackendManager.getDevice(usbDevice);
      if (!backend) {
        throw new Error(`Could not create ADB backend for device ${serial}`);
      }

      // Connect via WebADB
      const pair = await backend.connect();
      const adb = new Adb(pair.readable, pair.writable);

      // Store connection
      this.connectedAdbInstances.set(serial, adb);

      // Update device state
      const deviceInfo = this.detector.getDevices().find(d => d.serial === serial);
      if (deviceInfo) {
        deviceInfo.state = 'device';
      }

      return adb;
    } catch (error: any) {
      throw new Error(`Failed to connect to device via WebADB: ${error.message}`);
    }
  }

  /**
   * Get device properties via ADB
   */
  async getDeviceProperties(serial: string): Promise<DeviceProperties | null> {
    try {
      const adb = await this.connectDevice(serial);

      // Get device properties via ADB
      const codename = await adb.getProp('ro.product.device');
      const deviceName = await adb.getProp('ro.product.model');
      const buildId = await adb.getProp('ro.build.id');
      const buildVersion = await adb.getProp('ro.build.version.release');

      // Update device info with properties
      const deviceInfo = this.detector.getDevices().find(d => d.serial === serial);
      if (deviceInfo && codename) {
        deviceInfo.codename = codename;
        deviceInfo.model = deviceName || deviceInfo.model;
      }

      return {
        codename: codename || 'unknown',
        deviceName: deviceName || 'Unknown Device',
        version: buildVersion || undefined,
        buildId: buildId || undefined,
      };
    } catch (error: any) {
      console.error(`Failed to get device properties for ${serial}:`, error);
      return null;
    }
  }

  /**
   * Execute ADB shell command
   */
  async executeCommand(serial: string, command: string): Promise<string> {
    try {
      const adb = await this.connectDevice(serial);
      const process = await adb.subprocess.shell(command);
      
      // Read output
      const reader = process.stdout.getReader();
      let output = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        output += new TextDecoder().decode(value);
      }
      
      return output.trim();
    } catch (error: any) {
      throw new Error(`ADB command failed: ${error.message}`);
    }
  }

  /**
   * Reboot device to bootloader
   */
  async rebootToBootloader(serial: string): Promise<void> {
    try {
      const adb = await this.connectDevice(serial);
      await adb.reboot('bootloader');
      
      // Update device state
      const deviceInfo = this.detector.getDevices().find(d => d.serial === serial);
      if (deviceInfo) {
        deviceInfo.state = 'fastboot';
      }
    } catch (error: any) {
      throw new Error(`Failed to reboot to bootloader: ${error.message}`);
    }
  }

  /**
   * Reboot device
   */
  async rebootDevice(serial: string): Promise<void> {
    try {
      const adb = await this.connectDevice(serial);
      await adb.reboot();
    } catch (error: any) {
      throw new Error(`Failed to reboot device: ${error.message}`);
    }
  }

  /**
   * Check if device is in fastboot mode
   */
  async isFastbootMode(serial: string): Promise<boolean> {
    // Fastboot mode check would require WebUSB Fastboot backend
    // For now, check if ADB connection fails (indicates fastboot mode)
    try {
      await this.connectDevice(serial);
      return false; // ADB works, so not in fastboot
    } catch {
      return true; // ADB fails, likely in fastboot
    }
  }

  /**
   * Disconnect device
   */
  async disconnectDevice(serial: string): Promise<void> {
    const adb = this.connectedAdbInstances.get(serial);
    if (adb) {
      try {
        await adb.close();
      } catch (error) {
        console.error(`Error closing ADB connection for ${serial}:`, error);
      }
      this.connectedAdbInstances.delete(serial);
    }

    // Update device state
    const deviceInfo = this.detector.getDevices().find(d => d.serial === serial);
    if (deviceInfo) {
      deviceInfo.state = 'disconnected';
    }
  }

  /**
   * Get ADB instance for device (if connected)
   */
  getAdbInstance(serial: string): Adb | null {
    return this.connectedAdbInstances.get(serial) || null;
  }
}
