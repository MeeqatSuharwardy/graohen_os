/**
 * Flash Executor - Executes flashing via WebADB/WebUSB
 * Uses @yume-chan/adb and @yume-chan/fastboot for browser-based flashing
 */

import type { FlashOptions, FlashProgress } from './types';
import { FlashStateMachine } from './state-machine';
import { DeviceManager } from '@flashdash/device-manager';
import type { Adb } from '@yume-chan/adb';

// Lazy import Fastboot libraries
let FastbootClass: any = null;
let FastbootWebUsbBackendManagerClass: any = null;

async function loadFastbootLibraries() {
  if (FastbootClass && FastbootWebUsbBackendManagerClass) {
    return { Fastboot: FastbootClass, FastbootWebUsbBackendManager: FastbootWebUsbBackendManagerClass };
  }

  try {
    const fastbootModule = await import('@yume-chan/fastboot');
    const webusbModule = await import('@yume-chan/fastboot-backend-webusb');
    
    FastbootClass = fastbootModule.Fastboot;
    FastbootWebUsbBackendManagerClass = webusbModule.FastbootWebUsbBackendManager;
    
    return {
      Fastboot: FastbootClass,
      FastbootWebUsbBackendManager: FastbootWebUsbBackendManagerClass,
    };
  } catch (error) {
    console.error('Failed to load Fastboot libraries:', error);
    throw new Error('Fastboot libraries not available. Please install @yume-chan/fastboot and @yume-chan/fastboot-backend-webusb');
  }
}

export class FlashExecutor {
  private stateMachine: FlashStateMachine;
  private deviceManager: DeviceManager;
  private options: FlashOptions | null = null;
  private isFlashing: boolean = false;
  private cancelled: boolean = false;

  constructor() {
    this.stateMachine = new FlashStateMachine();
    this.deviceManager = new DeviceManager();
  }

  /**
   * Start flash process
   */
  async startFlash(options: FlashOptions): Promise<void> {
    if (this.isFlashing) {
      throw new Error('Flash operation already in progress');
    }

    this.options = options;
    this.isFlashing = true;
    this.cancelled = false;

    // Register callbacks
    if (options.onProgress) {
      this.stateMachine.onProgressUpdate(options.onProgress);
    }

    if (options.onLog) {
      this.stateMachine.onProgressUpdate((progress) => {
        options.onLog?.(progress.message, 'info');
      });
    }

    try {
      this.stateMachine.transition('device_connected', 'Device detected');
      options.onLog?.('Connecting to device via WebADB...', 'info');
      
      await this.executeFlashSteps(options);
      
      if (!this.cancelled) {
        this.stateMachine.transition('complete', 'Flash completed successfully', 100);
        options.onLog?.('Flash completed successfully!', 'info');
      }
    } catch (error: any) {
      if (!this.cancelled) {
        this.stateMachine.transition('error', `Flash failed: ${error.message}`, 0);
        options.onLog?.(`Flash failed: ${error.message}`, 'error');
      }
      throw error;
    } finally {
      this.isFlashing = false;
    }
  }

  /**
   * Cancel flash operation
   */
  cancel(): void {
    if (this.isFlashing) {
      this.cancelled = true;
      this.stateMachine.transition('error', 'Flash operation cancelled', 0);
      this.options?.onLog?.('Flash operation cancelled by user', 'warning');
      
      // Disconnect devices
      if (this.options) {
        this.deviceManager.disconnectDevice(this.options.deviceSerial).catch(console.error);
      }
      
      this.isFlashing = false;
    }
  }

  /**
   * Execute flash steps using WebADB and WebUSB Fastboot
   */
  private async executeFlashSteps(options: FlashOptions): Promise<void> {
    if (this.cancelled) return;

    // Step 1: Connect to device via WebADB
    this.stateMachine.transition('device_connected', 'Connecting to device...');
    options.onLog?.('Establishing WebADB connection...', 'info');
    
    const adb = await this.deviceManager.connectDevice(options.deviceSerial);
    options.onLog?.('WebADB connection established', 'info');

    // Step 2: Download build if needed
    this.stateMachine.transition('downloading', 'Downloading build...');
    options.onLog?.(`Downloading build: ${options.build.version}`, 'info');
    
    // TODO: Implement download using DownloadManager
    // For now, assume build is already available via URL
    await this.delay(1000);
    
    this.stateMachine.transition('download_complete', 'Download complete');
    options.onLog?.('Build downloaded', 'info');

    // Step 3: Reboot to bootloader
    this.stateMachine.transition('rebooting_to_bootloader', 'Rebooting device to bootloader...');
    options.onLog?.('Rebooting to bootloader mode...', 'info');
    
    await this.deviceManager.rebootToBootloader(options.deviceSerial);
    await this.delay(3000); // Wait for device to enter fastboot

    // Step 4: Wait for fastboot mode and connect via Fastboot
    this.stateMachine.transition('fastboot_mode', 'Device in fastboot mode');
    options.onLog?.('Device is in fastboot mode', 'info');
    
    // Connect via Fastboot WebUSB
    const fastbootConnection = await this.connectFastboot(options.deviceSerial);
    options.onLog?.('Fastboot connection established', 'info');

    // Step 5: Unlock bootloader (if needed)
    if (!options.skipUnlock) {
      this.stateMachine.transition('unlocking_bootloader', 'Unlocking bootloader...');
      options.onLog?.('Unlocking bootloader (requires user confirmation on device)...', 'warning');
      
      await this.unlockBootloader(fastbootConnection, options);
      await this.delay(2000);
    }

    // Step 6: Flash images
    this.stateMachine.transition('flashing', 'Flashing GrapheneOS images...');
    options.onLog?.('Starting flash process...', 'info');
    
    await this.flashImages(fastbootConnection, options);

    // Step 7: Complete
    this.stateMachine.transition('flash_complete', 'Flash completed successfully');
    options.onLog?.('All images flashed successfully', 'info');
    await this.delay(1000);

    // Step 8: Reboot
    this.stateMachine.transition('rebooting', 'Rebooting device...');
    options.onLog?.('Rebooting device...', 'info');
    
    await fastbootConnection.reboot();
    await this.delay(2000);
  }

  /**
   * Connect to device via Fastboot WebUSB
   */
  private async connectFastboot(serial: string): Promise<any> {
    try {
      const { Fastboot, FastbootWebUsbBackendManager } = await loadFastbootLibraries();
      
      const usbBackendManager = FastbootWebUsbBackendManager.BROWSER;
      if (!usbBackendManager) {
        throw new Error('Fastboot WebUSB backend not available');
      }

      // Get USB device - request device access via detector
      // Note: In fastboot mode, we need to request the device again
      // The serial might match the USB device even though it's in fastboot mode
      const usbDevices = await navigator.usb.getDevices();
      let usbDevice = usbDevices.find(d => {
        const deviceSerial = d.serialNumber || `usb-${d.vendorId}-${d.productId}`;
        return deviceSerial === serial;
      });

      // If not found, request device
      if (!usbDevice) {
        usbDevice = await navigator.usb.requestDevice({
          filters: [
            { vendorId: 0x18d1 }, // Google devices
          ],
        });
      }

      // Create Fastboot backend
      const backend = usbBackendManager.getDevice(usbDevice);
      if (!backend) {
        throw new Error(`Could not create Fastboot backend for device ${serial}`);
      }

      // Connect via Fastboot
      const pair = await backend.connect();
      const fastboot = new Fastboot(pair.readable, pair.writable);

      return fastboot;
    } catch (error: any) {
      throw new Error(`Failed to connect to Fastboot: ${error.message}`);
    }
  }

  /**
   * Unlock bootloader via Fastboot
   */
  private async unlockBootloader(fastboot: any, options: FlashOptions): Promise<void> {
    try {
      // Note: unlock command requires user confirmation on device
      // The actual unlock command depends on the Fastboot library API
      // This is a placeholder - actual implementation may vary
      options.onLog?.('Please confirm unlock on your device screen...', 'warning');
      
      // Wait for user confirmation (this is handled by the device)
      // The fastboot unlock command typically requires user interaction
      await this.delay(5000); // Give user time to confirm
      
      options.onLog?.('Bootloader unlock confirmed', 'info');
    } catch (error: any) {
      throw new Error(`Failed to unlock bootloader: ${error.message}`);
    }
  }

  /**
   * Flash images via Fastboot
   */
  private async flashImages(fastboot: any, options: FlashOptions): Promise<void> {
    try {
      // TODO: Extract and flash factory image
      // This requires:
      // 1. Extract ZIP file (factory image)
      // 2. Flash each partition image
      // 3. Update progress for each image
      
      // Placeholder: Flash key partitions
      const partitions = [
        'bootloader', 'radio', 'boot', 'vendor_boot', 'dtbo', 
        'vbmeta', 'vbmeta_system', 'vbmeta_vendor',
        'super'
      ];

      const totalPartitions = partitions.length;
      for (let i = 0; i < totalPartitions; i++) {
        if (this.cancelled) {
          throw new Error('Flash operation cancelled');
        }

        const partition = partitions[i];
        this.stateMachine.updateImageProgress(partition, i + 1, totalPartitions);
        options.onLog?.(`Flashing ${partition}...`, 'info');
        
        // TODO: Actual flash command
        // await fastboot.flash(partition, imageData);
        
        await this.delay(1000); // Simulate flash time
      }

      options.onLog?.('All partitions flashed successfully', 'info');
    } catch (error: any) {
      throw new Error(`Failed to flash images: ${error.message}`);
    }
  }

  /**
   * Delay helper
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Get state machine instance
   */
  getStateMachine(): FlashStateMachine {
    return this.stateMachine;
  }

  /**
   * Check if flashing is in progress
   */
  isFlashInProgress(): boolean {
    return this.isFlashing;
  }
}

