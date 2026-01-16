/**
 * WebUSB/WebADB Transport Implementation for Browser
 * 
 * This transport uses @yume-chan/adb and @yume-chan/fastboot for WebUSB-based flashing.
 * It's designed for browser-based flashing (Chrome/Edge/TOR).
 */

import type { FlashTransport, CommandResult } from '../flash-engine';
import type { Adb } from '@yume-chan/adb';

// Lazy import libraries
let AdbClass: typeof Adb | null = null;
let AdbWebUsbBackendManagerClass: any = null;
let FastbootClass: any = null;
let FastbootWebUsbBackendManagerClass: any = null;

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
    throw new Error('ADB libraries not available');
  }
}

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
    throw new Error('Fastboot libraries not available');
  }
}

export class WebUSBTransport implements FlashTransport {
  private deviceSerial: string;
  private currentAdb: Adb | null = null;
  private currentFastboot: any = null;
  private currentMode: 'bootloader' | 'fastbootd' | null = null;

  constructor(deviceSerial: string) {
    this.deviceSerial = deviceSerial;
  }

  private async getUSBDevice(): Promise<USBDevice | null> {
    // Try to get already-paired device
    const devices = await navigator.usb.getDevices();
    let usbDevice = devices.find(d => {
      const deviceSerial = d.serialNumber || `usb-${d.vendorId}-${d.productId}`;
      return deviceSerial === this.deviceSerial;
    });

    // If not found, request device access
    if (!usbDevice) {
      try {
        usbDevice = await navigator.usb.requestDevice({
          filters: [
            { vendorId: 0x18d1 }, // Google devices
          ],
        });
      } catch (error) {
        console.error('Failed to request USB device:', error);
        return null;
      }
    }

    return usbDevice || null;
  }

  async adbCommand(args: string[], timeout: number = 30): Promise<CommandResult> {
    try {
      // Load ADB libraries
      const { Adb, AdbWebUsbBackendManager } = await loadAdbLibraries();
      const usbBackendManager = AdbWebUsbBackendManager.BROWSER;

      // Get or connect ADB
      if (!this.currentAdb) {
        const usbDevice = await this.getUSBDevice();
        if (!usbDevice) {
          return { success: false, stderr: 'USB device not available' };
        }

        const backend = usbBackendManager.getDevice(usbDevice);
        if (!backend) {
          return { success: false, stderr: 'Failed to create ADB backend' };
        }

        const pair = await backend.connect();
        this.currentAdb = new Adb(pair.readable, pair.writable);
      }

      // Execute ADB command
      if (args[0] === 'shell') {
        // Shell command
        const command = args.slice(1).join(' ');
        const result = await this.currentAdb.subprocess.shell(command).then(s => s.stdout.read());
        const output = await result.readAll();
        return {
          success: true,
          stdout: new TextDecoder().decode(output),
        };
      } else if (args[0] === 'reboot' && args[1] === 'bootloader') {
        // Reboot to bootloader
        await this.currentAdb.reboot('bootloader');
        // Close ADB connection
        if (this.currentAdb) {
          await this.currentAdb.close();
          this.currentAdb = null;
        }
        return { success: true, stdout: 'Rebooting to bootloader' };
      } else {
        // Other ADB commands
        return { success: false, stderr: `Unsupported ADB command: ${args.join(' ')}` };
      }
    } catch (error: any) {
      return {
        success: false,
        stderr: error.message || String(error),
      };
    }
  }

  async fastbootCommand(args: string[], timeout: number = 30): Promise<CommandResult> {
    try {
      // Load Fastboot libraries
      const { Fastboot, FastbootWebUsbBackendManager } = await loadFastbootLibraries();
      const usbBackendManager = FastbootWebUsbBackendManager.BROWSER;

      // Get or connect Fastboot
      if (!this.currentFastboot || this.currentMode !== 'bootloader') {
        const usbDevice = await this.getUSBDevice();
        if (!usbDevice) {
          return { success: false, stderr: 'USB device not available' };
        }

        const backend = usbBackendManager.getDevice(usbDevice);
        if (!backend) {
          return { success: false, stderr: 'Failed to create Fastboot backend' };
        }

        const pair = await backend.connect();
        this.currentFastboot = new Fastboot(pair.readable, pair.writable);
        this.currentMode = 'bootloader';
      }

      // Execute Fastboot command
      if (args[0] === 'flash' && args.length >= 3) {
        // Flash command
        const partition = args[1];
        const file = args[2]; // File path or blob URL
        // Note: Actual file upload would need to be handled separately
        // This is a placeholder - you'd need to read the file and upload it
        return { success: false, stderr: 'Flash command requires file upload implementation' };
      } else if (args[0] === 'reboot' && args[1] === 'bootloader') {
        // Reboot bootloader
        await this.currentFastboot.reboot('bootloader');
        await this.currentFastboot.close();
        this.currentFastboot = null;
        this.currentMode = null;
        return { success: true, stdout: 'Rebooting bootloader' };
      } else if (args[0] === 'reboot' && args[1] === 'fastboot') {
        // Reboot to fastbootd
        await this.currentFastboot.reboot('fastboot');
        await this.currentFastboot.close();
        this.currentFastboot = null;
        this.currentMode = null;
        return { success: true, stdout: 'Rebooting to fastbootd' };
      } else if (args[0] === 'getvar') {
        // Get variable
        const varName = args[1];
        const value = await this.currentFastboot.getVariable(varName);
        return { success: true, stdout: `${varName}: ${value}` };
      } else if (args[0] === 'flashing' && args[1] === 'unlock') {
        // Unlock bootloader
        await this.currentFastboot.unlock();
        return { success: true, stdout: 'Bootloader unlocked' };
      } else if (args[0] === 'flashing' && args[1] === 'lock') {
        // Lock bootloader
        await this.currentFastboot.lock();
        return { success: true, stdout: 'Bootloader locked' };
      } else {
        return { success: false, stderr: `Unsupported fastboot command: ${args.join(' ')}` };
      }
    } catch (error: any) {
      return {
        success: false,
        stderr: error.message || String(error),
      };
    }
  }

  async fastbootdCommand(args: string[], timeout: number = 30): Promise<CommandResult> {
    // Fastbootd uses the same transport as fastboot, but device is in different mode
    // The @yume-chan/fastboot library automatically handles this
    return this.fastbootCommand(args, timeout);
  }

  async waitForFastboot(timeout: number = 90): Promise<boolean> {
    const startTime = Date.now();
    const checkInterval = 2000; // Check every 2 seconds

    while (Date.now() - startTime < timeout * 1000) {
      try {
        // Try to connect to fastboot
        const { Fastboot, FastbootWebUsbBackendManager } = await loadFastbootLibraries();
        const usbBackendManager = FastbootWebUsbBackendManager.BROWSER;

        const usbDevice = await this.getUSBDevice();
        if (usbDevice) {
          const backend = usbBackendManager.getDevice(usbDevice);
          if (backend) {
            // Try to connect (this will fail if device not in fastboot)
            try {
              const pair = await backend.connect();
              const fastboot = new Fastboot(pair.readable, pair.writable);
              // Test connection
              await fastboot.getVariable('product');
              await fastboot.close();
              return true;
            } catch {
              // Device not in fastboot yet
            }
          }
        }
      } catch {
        // Continue waiting
      }

      await this.sleep(checkInterval);
    }

    return false;
  }

  async waitForFastbootd(timeout: number = 60): Promise<boolean> {
    // Similar to waitForFastboot, but check for fastbootd mode
    const startTime = Date.now();
    const checkInterval = 2000;

    while (Date.now() - startTime < timeout * 1000) {
      try {
        const { Fastboot, FastbootWebUsbBackendManager } = await loadFastbootLibraries();
        const usbBackendManager = FastbootWebUsbBackendManager.BROWSER;

        const usbDevice = await this.getUSBDevice();
        if (usbDevice) {
          const backend = usbBackendManager.getDevice(usbDevice);
          if (backend) {
            try {
              const pair = await backend.connect();
              const fastboot = new Fastboot(pair.readable, pair.writable);
              // Check if in fastbootd (is-userspace should be yes)
              const isUserspace = await fastboot.getVariable('is-userspace');
              await fastboot.close();
              if (isUserspace === 'yes') {
                return true;
              }
            } catch {
              // Continue waiting
            }
          }
        }
      } catch {
        // Continue waiting
      }

      await this.sleep(checkInterval);
    }

    return false;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async close(): Promise<void> {
    if (this.currentAdb) {
      await this.currentAdb.close();
      this.currentAdb = null;
    }
    if (this.currentFastboot) {
      await this.currentFastboot.close();
      this.currentFastboot = null;
    }
    this.currentMode = null;
  }
}

