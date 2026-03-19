/**
 * Electron/Node.js Transport Implementation
 * 
 * This transport uses Node.js child_process to execute ADB and Fastboot commands.
 * It's designed for Electron app where we have access to system commands.
 */

import type { FlashTransport, CommandResult } from '../flash-engine';
import { spawn, exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface ElectronTransportOptions {
  adbPath?: string;
  fastbootPath?: string;
  deviceSerial?: string;
}

export class ElectronTransport implements FlashTransport {
  private adbPath: string;
  private fastbootPath: string;
  private deviceSerial?: string;

  constructor(options: ElectronTransportOptions = {}) {
    this.adbPath = options.adbPath || 'adb';
    this.fastbootPath = options.fastbootPath || 'fastboot';
    this.deviceSerial = options.deviceSerial;
  }

  private async runCommand(
    cmd: string[],
    timeout: number = 30
  ): Promise<CommandResult> {
    const command = cmd.join(' ');
    
    try {
      const { stdout, stderr } = await execAsync(command, {
        timeout: timeout * 1000,
        maxBuffer: 10 * 1024 * 1024, // 10MB
      });

      return {
        success: true,
        stdout: stdout || '',
        stderr: stderr || '',
        returncode: 0,
      };
    } catch (error: any) {
      return {
        success: error.code === 0, // execAsync throws even on success sometimes
        stdout: error.stdout || '',
        stderr: error.stderr || error.message || '',
        returncode: error.code || -1,
      };
    }
  }

  async adbCommand(args: string[], timeout: number = 30): Promise<CommandResult> {
    const cmd = [this.adbPath];
    if (this.deviceSerial) {
      cmd.push('-s', this.deviceSerial);
    }
    cmd.push(...args);

    return this.runCommand(cmd, timeout);
  }

  async fastbootCommand(args: string[], timeout: number = 30): Promise<CommandResult> {
    const cmd = [this.fastbootPath];
    if (this.deviceSerial) {
      cmd.push('-s', this.deviceSerial);
    }
    cmd.push(...args);

    return this.runCommand(cmd, timeout);
  }

  async fastbootdCommand(args: string[], timeout: number = 30): Promise<CommandResult> {
    // Fastbootd uses the same fastboot binary, but device is in different mode
    // The fastboot binary automatically detects which mode the device is in
    return this.fastbootCommand(args, timeout);
  }

  async waitForFastboot(timeout: number = 90): Promise<boolean> {
    const startTime = Date.now();
    const checkInterval = 2000; // Check every 2 seconds

    while (Date.now() - startTime < timeout * 1000) {
      try {
        const result = await this.fastbootCommand(['devices'], 5);
        if (result.success) {
          const output = result.stdout || result.stderr || '';
          // Look for device in fastboot mode
          if (this.deviceSerial) {
            if (output.includes(`${this.deviceSerial}\tfastboot`)) {
              return true;
            }
          } else {
            // If no serial specified, check for any fastboot device
            const lines = output.split('\n').filter(l => l.trim() && !l.includes('List of devices'));
            if (lines.some(l => l.includes('fastboot'))) {
              return true;
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
    const startTime = Date.now();
    const checkInterval = 2000;

    while (Date.now() - startTime < timeout * 1000) {
      try {
        // Check if device is in fastbootd by querying is-userspace variable
        const result = await this.fastbootdCommand(['getvar', 'is-userspace'], 5);
        if (result.success) {
          const output = (result.stdout || result.stderr || '').toLowerCase();
          if (output.includes('is-userspace: yes') || output.includes('is-userspace:yes')) {
            return true;
          }
        }

        // Also check devices list
        const devicesResult = await this.fastbootdCommand(['devices'], 5);
        if (devicesResult.success && this.deviceSerial) {
          const output = devicesResult.stdout || devicesResult.stderr || '';
          if (output.includes(this.deviceSerial)) {
            // Verify it's actually fastbootd
            const verifyResult = await this.fastbootdCommand(['getvar', 'is-userspace'], 5);
            if (verifyResult.success) {
              const verifyOutput = (verifyResult.stdout || verifyResult.stderr || '').toLowerCase();
              if (verifyOutput.includes('is-userspace: yes')) {
                return true;
              }
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
}

