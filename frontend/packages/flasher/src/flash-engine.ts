/**
 * GrapheneOS Flashing Engine - Shared FSM Implementation (TypeScript)
 * 
 * This module provides a finite state machine (FSM) for flashing GrapheneOS.
 * It is designed to be reusable across:
 * - Electron app
 * - Browser/WebUSB flasher
 * 
 * The FSM follows the official GrapheneOS CLI installation sequence:
 * 1. ADB mode: Unlock bootloader (if needed)
 * 2. Fastboot mode: Flash bootloader & radio
 * 3. Reboot to fastbootd: Flash super partition images
 * 4. Final reboot: Complete installation
 * 
 * States:
 * - INIT → ADB → FASTBOOT → FASTBOOT_FLASH → FASTBOOTD → FASTBOOTD_FLASH → FINAL → DONE
 */

export enum FlashState {
  INIT = 'init',
  ADB = 'adb',
  FASTBOOT = 'fastboot',
  FASTBOOT_FLASH = 'fastboot_flash',
  FASTBOOTD = 'fastbootd',
  FASTBOOTD_FLASH = 'fastbootd_flash',
  FINAL = 'final',
  DONE = 'done',
  ERROR = 'error',
}

export interface FlashProgress {
  state: FlashState;
  stepName: string;
  progressPercent: number;
  message: string;
  partition?: string;
  partitionIndex?: number;
  totalPartitions?: number;
  logLines: string[];
}

export interface CommandResult {
  success: boolean;
  stdout?: string;
  stderr?: string;
  returncode?: number;
}

/**
 * Transport abstraction for ADB/Fastboot/WebUSB commands
 */
export interface FlashTransport {
  /**
   * Execute ADB command
   */
  adbCommand(args: string[], timeout?: number): Promise<CommandResult>;

  /**
   * Execute fastboot command in bootloader fastboot mode
   */
  fastbootCommand(args: string[], timeout?: number): Promise<CommandResult>;

  /**
   * Execute fastboot command in fastbootd (userspace) mode
   */
  fastbootdCommand(args: string[], timeout?: number): Promise<CommandResult>;

  /**
   * Wait for device to be available in fastboot mode
   */
  waitForFastboot(timeout?: number): Promise<boolean>;

  /**
   * Wait for device to be available in fastbootd mode
   */
  waitForFastbootd(timeout?: number): Promise<boolean>;
}

/**
 * Build management - handles bundle location and download
 */
export interface BuildManager {
  /**
   * Get path to bundle. Returns null if bundle not found.
   */
  getBundlePath(codename: string, version?: string): Promise<string | null>;

  /**
   * Ensure bundle is available. Downloads if missing. Returns bundle path.
   */
  ensureBundleAvailable(
    codename: string,
    version?: string,
    onProgress?: (progress: number) => void
  ): Promise<string>;

  /**
   * Find all partition files in bundle
   */
  findPartitionFiles(bundlePath: string): Promise<Record<string, any>>;
}

export interface FlashCallbacks {
  onProgress?: (progress: FlashProgress) => void;
  onLog?: (message: string, level: 'info' | 'warning' | 'error') => void;
}

export interface FlashOptions {
  codename: string;
  version?: string;
  skipUnlock?: boolean;
  lockBootloader?: boolean;
}

export interface FlashResult {
  success: boolean;
  error?: string;
  finalState: FlashState;
  bundlePath?: string;
}

/**
 * GrapheneOS Flashing Engine - FSM Implementation
 * 
 * This class implements a finite state machine for flashing GrapheneOS.
 * It is stateless with respect to frontend - all state is explicitly managed.
 */
export class GrapheneOSFlashEngine {
  private transport: FlashTransport;
  private buildManager: BuildManager;
  private deviceSerial: string;
  private currentState: FlashState = FlashState.INIT;
  private progress: FlashProgress;
  private callbacks: FlashCallbacks = {};
  private bundlePath: string | null = null;
  private partitionFiles: Record<string, any> = {};

  constructor(
    transport: FlashTransport,
    buildManager: BuildManager,
    deviceSerial: string
  ) {
    this.transport = transport;
    this.buildManager = buildManager;
    this.deviceSerial = deviceSerial;
    this.progress = {
      state: FlashState.INIT,
      stepName: 'Initializing',
      progressPercent: 0,
      message: '',
      logLines: [],
    };
  }

  setCallbacks(callbacks: FlashCallbacks): void {
    this.callbacks = callbacks;
  }

  private log(message: string, level: 'info' | 'warning' | 'error' = 'info'): void {
    if (this.callbacks.onLog) {
      this.callbacks.onLog(message, level);
    } else {
      console.log(`[${level.toUpperCase()}] ${message}`);
    }
  }

  private updateProgress(
    state: FlashState,
    stepName: string,
    message: string = '',
    progress: number = 0,
    partition?: string,
    partitionIndex?: number,
    totalPartitions?: number
  ): void {
    this.currentState = state;
    this.progress = {
      state,
      stepName,
      progressPercent: progress,
      message,
      partition,
      partitionIndex,
      totalPartitions,
      logLines: message ? [...this.progress.logLines, message] : this.progress.logLines,
    };

    if (this.callbacks.onProgress) {
      this.callbacks.onProgress(this.progress);
    }
  }

  private transition(newState: FlashState, stepName: string, message: string = ''): void {
    const oldState = this.currentState;
    this.currentState = newState;
    const transitionMsg = `[STATE: ${oldState} → ${newState}] ${message}`;
    this.log(transitionMsg, 'info');
    this.updateProgress(newState, stepName, message);
  }

  async executeFlash(options: FlashOptions): Promise<FlashResult> {
    try {
      // INIT → ADB
      this.transition(FlashState.INIT, 'Initializing', 'Starting GrapheneOS flash process');

      // Ensure bundle is available
      this.log(`Ensuring bundle is available: ${options.codename} ${options.version || 'latest'}`);
      const bundlePath = await this.buildManager.ensureBundleAvailable(
        options.codename,
        options.version,
        (p) => this.log(`Download progress: ${p}%`)
      );
      this.bundlePath = bundlePath;

      // Find partition files
      this.log('Scanning bundle for partition files...');
      this.partitionFiles = await this.buildManager.findPartitionFiles(bundlePath);
      this.log(`Found ${Object.keys(this.partitionFiles).length} partition file(s)`);

      // ADB state: Unlock bootloader if needed
      if (!options.skipUnlock) {
        this.transition(FlashState.ADB, 'Unlocking Bootloader', 'Device must be in ADB mode for unlock');
        if (!(await this.unlockBootloader())) {
          return {
            success: false,
            error: 'Failed to unlock bootloader',
            finalState: FlashState.ERROR,
          };
        }
      } else {
        this.log('Skipping bootloader unlock (device already unlocked)');
      }

      // FASTBOOT state: Reboot to fastboot if needed
      this.transition(FlashState.FASTBOOT, 'Entering Fastboot', 'Rebooting to bootloader fastboot mode');
      if (!(await this.enterFastboot())) {
        return {
          success: false,
          error: 'Failed to enter fastboot mode',
          finalState: FlashState.ERROR,
        };
      }

      // FASTBOOT_FLASH state: Flash bootloader, radio, and core partitions
      this.transition(FlashState.FASTBOOT_FLASH, 'Flashing Firmware', 'Flashing in bootloader fastboot mode');
      if (!(await this.flashInBootloaderFastboot())) {
        return {
          success: false,
          error: 'Failed to flash partitions in bootloader fastboot',
          finalState: FlashState.ERROR,
        };
      }

      // FASTBOOTD state: Transition to fastbootd
      this.transition(FlashState.FASTBOOTD, 'Entering Fastbootd', 'Rebooting to fastbootd (userspace fastboot)');
      if (!(await this.enterFastbootd())) {
        return {
          success: false,
          error: 'Failed to enter fastbootd mode',
          finalState: FlashState.ERROR,
        };
      }

      // FASTBOOTD_FLASH state: Flash super partition images
      this.transition(FlashState.FASTBOOTD_FLASH, 'Flashing Super Partition', 'Flashing super images in fastbootd');
      if (!(await this.flashSuperInFastbootd())) {
        return {
          success: false,
          error: 'Failed to flash super partition in fastbootd',
          finalState: FlashState.ERROR,
        };
      }

      // FINAL state: Lock bootloader (optional) and reboot
      this.transition(FlashState.FINAL, 'Finalizing', 'Flash complete, preparing to reboot');

      if (options.lockBootloader) {
        this.log('Locking bootloader (requires verified boot support)...');
        if (!(await this.lockBootloader())) {
          this.log('Warning: Failed to lock bootloader, but flash succeeded', 'warning');
        }
      }

      // Reboot device
      this.log('Rebooting device...');
      const rebootResult = await this.transport.fastbootdCommand(['reboot'], 30);
      if (!rebootResult.success) {
        this.log('Warning: Reboot command failed, but flash succeeded. Manually reboot device.', 'warning');
      }

      // DONE state
      this.transition(FlashState.DONE, 'Complete', 'GrapheneOS flash completed successfully');

      return {
        success: true,
        finalState: FlashState.DONE,
        bundlePath,
      };
    } catch (error: any) {
      this.transition(FlashState.ERROR, 'Error', `Flash failed: ${error.message || String(error)}`);
      console.error('Flash execution failed:', error);
      return {
        success: false,
        error: error.message || String(error),
        finalState: FlashState.ERROR,
      };
    }
  }

  private async unlockBootloader(): Promise<boolean> {
    this.log('Checking bootloader unlock status...');
    // Try to check if already unlocked (may fail if device not in ADB mode)
    const result = await this.transport.adbCommand(['shell', 'getprop', 'ro.boot.flash.locked'], 10);
    
    if (result.success && result.stdout?.includes('0')) {
      this.log('Bootloader is already unlocked');
      return true;
    }

    // Request unlock
    this.log('Bootloader is locked. Requesting unlock...');
    this.log('ACTION REQUIRED: Check device screen and confirm unlock (Volume Up + Power)', 'warning');
    
    const unlockResult = await this.transport.fastbootCommand(['flashing', 'unlock'], 60);
    
    if (!unlockResult.success) {
      this.log(`Unlock command failed: ${unlockResult.stderr || 'Unknown error'}`, 'error');
      return false;
    }

    // Wait for unlock completion
    this.log('Waiting for unlock to complete (device will reboot)...');
    await this.sleep(5000);

    // Verify unlock by checking fastboot state
    if (!(await this.transport.waitForFastboot(60))) {
      this.log('Warning: Device did not return to fastboot after unlock', 'warning');
      return false;
    }

    this.log('Bootloader unlocked successfully');
    return true;
  }

  private async enterFastboot(): Promise<boolean> {
    // If device is already in fastboot, skip reboot
    const testResult = await this.transport.fastbootCommand(['getvar', 'product'], 5);
    if (testResult.success) {
      this.log('Device is already in fastboot mode');
      return true;
    }

    // Reboot to bootloader
    this.log('Rebooting device to bootloader fastboot mode...');
    const result = await this.transport.adbCommand(['reboot', 'bootloader'], 60);
    
    if (!result.success) {
      this.log('Failed to reboot to bootloader via ADB, device may already be in fastboot', 'warning');
    }

    // Wait for fastboot
    this.log('Waiting for device to enter fastboot mode (this may take up to 60 seconds)...');
    if (!(await this.transport.waitForFastboot(90))) {
      return false;
    }

    this.log('Device successfully entered fastboot mode');
    return true;
  }

  private async flashInBootloaderFastboot(): Promise<boolean> {
    this.log('='.repeat(60));
    this.log('Starting partition flashing in bootloader fastboot mode');
    this.log('Sequence: bootloader → radio → core partitions');
    this.log('='.repeat(60));

    // Step 1: Flash bootloader (if present)
    if (this.partitionFiles['bootloader']) {
      const bootloaderFile = Array.isArray(this.partitionFiles['bootloader'])
        ? this.partitionFiles['bootloader'][0]
        : this.partitionFiles['bootloader'];

      this.log(`Flashing bootloader: ${bootloaderFile.name || bootloaderFile}`);
      this.updateProgress(
        FlashState.FASTBOOT_FLASH,
        'Flashing Bootloader',
        `Flashing bootloader: ${bootloaderFile.name || bootloaderFile}`,
        5,
        'bootloader'
      );

      const result = await this.transport.fastbootCommand(['flash', 'bootloader', String(bootloaderFile)], 120);
      if (!result.success) {
        this.log(`Failed to flash bootloader: ${result.stderr || 'Unknown error'}`, 'error');
        return false;
      }

      this.log('✓ Bootloader flashed');

      // CRITICAL: Reboot bootloader ONCE after bootloader flash (FIRST reboot)
      this.log('Rebooting bootloader (required after bootloader flash)...');
      this.log('This is the FIRST reboot - radio will be flashed next');

      const rebootResult = await this.transport.fastbootCommand(['reboot', 'bootloader'], 60);
      if (!rebootResult.success) {
        this.log(`Failed to reboot bootloader: ${rebootResult.stderr || 'Unknown error'}`, 'error');
        return false;
      }

      // Wait for fastboot
      this.log('Waiting for device to return to fastboot (USB disconnect/reconnect is normal)...');
      if (!(await this.transport.waitForFastboot(90))) {
        this.log('Warning: Device not detected in fastboot, attempting to continue...', 'warning');
        const testResult = await this.transport.fastbootCommand(['getvar', 'product'], 5);
        if (!testResult.success) {
          this.log('Device is not responding in fastboot mode', 'error');
          return false;
        }
      }
    }

    // Step 2: Flash radio (if present)
    if (this.partitionFiles['radio']) {
      const radioFile = Array.isArray(this.partitionFiles['radio'])
        ? this.partitionFiles['radio'][0]
        : this.partitionFiles['radio'];

      this.log(`Flashing radio: ${radioFile.name || radioFile}`);
      this.updateProgress(
        FlashState.FASTBOOT_FLASH,
        'Flashing Radio',
        `Flashing radio: ${radioFile.name || radioFile}`,
        15,
        'radio'
      );

      const result = await this.transport.fastbootCommand(['flash', 'radio', String(radioFile)], 120);
      if (!result.success) {
        this.log(`Failed to flash radio: ${result.stderr || 'Unknown error'}`, 'error');
        return false;
      }

      this.log('✓ Radio flashed');

      // CRITICAL: Reboot bootloader ONCE after radio flash (LAST reboot before fastbootd)
      this.log('Rebooting bootloader after radio flash (required by GrapheneOS)...');
      this.log('This is the LAST reboot - core partitions will be flashed next, then transition to fastbootd');

      const rebootResult = await this.transport.fastbootCommand(['reboot', 'bootloader'], 60);
      if (!rebootResult.success) {
        this.log(`Failed to reboot bootloader: ${rebootResult.stderr || 'Unknown error'}`, 'error');
        return false;
      }

      // Wait for fastboot
      this.log('Waiting for device to return to fastboot (USB disconnect/reconnect is normal)...');
      this.log('After this wait, core partitions will be flashed WITHOUT any more reboots');

      if (!(await this.transport.waitForFastboot(90))) {
        this.log('Warning: Device not detected in fastboot, attempting to continue...', 'warning');
        const testResult = await this.transport.fastbootCommand(['getvar', 'product'], 5);
        if (!testResult.success) {
          this.log('Device is not responding in fastboot mode', 'error');
          return false;
        }
      }
    }

    // Step 3: Flash core partitions (NO REBOOT between any of these)
    this.log('='.repeat(60));
    this.log('Flashing core partitions (NO MORE REBOOTS until fastbootd transition)');
    this.log('='.repeat(60));

    const corePartitions = [
      ['boot', 'boot.img'],
      ['init_boot', 'init_boot.img'],
      ['dtbo', 'dtbo.img'],
      ['vendor_kernel_boot', 'vendor_kernel_boot.img'],
      ['pvmfw', 'pvmfw.img'],
      ['vendor_boot', 'vendor_boot.img'],
      ['vbmeta', 'vbmeta.img'],
    ];

    let coreFlashCount = 0;
    const coreTotal = corePartitions.filter(([name, filename]) => {
      return this.partitionFiles[name] || (this.bundlePath && this.fileExists(`${this.bundlePath}/${filename}`));
    }).length;

    for (const [partitionName, filename] of corePartitions) {
      let partitionFile = this.partitionFiles[partitionName];
      if (!partitionFile && this.bundlePath) {
        partitionFile = this.fileExists(`${this.bundlePath}/${filename}`) ? `${this.bundlePath}/${filename}` : null;
      }

      if (!partitionFile) {
        this.log(`Skipping ${partitionName} (file not found)`);
        continue;
      }

      partitionFile = Array.isArray(partitionFile) ? partitionFile[0] : partitionFile;

      coreFlashCount++;
      this.log(`Flashing ${partitionName} (${coreFlashCount}/${coreTotal})...`);
      this.updateProgress(
        FlashState.FASTBOOT_FLASH,
        `Flashing ${partitionName}`,
        `Flashing ${partitionName}: ${partitionFile}`,
        20 + Math.floor((coreFlashCount / coreTotal) * 30),
        partitionName,
        coreFlashCount,
        coreTotal
      );

      const result = await this.transport.fastbootCommand(['flash', partitionName, String(partitionFile)], 120);
      if (!result.success) {
        this.log(`Failed to flash ${partitionName}: ${result.stderr || 'Unknown error'}`, 'error');
        return false;
      }

      this.log(`✓ ${partitionName} flashed`);
    }

    this.log('✓ All core partitions flashed successfully');
    return true;
  }

  private async enterFastbootd(): Promise<boolean> {
    this.log('Rebooting to fastbootd (userspace fastboot)...');
    this.log('This transition is required for flashing super partition images');

    const result = await this.transport.fastbootCommand(['reboot', 'fastboot'], 60);
    if (!result.success) {
      this.log(`Failed to reboot to fastbootd: ${result.stderr || 'Unknown error'}`, 'error');
      return false;
    }

    // Wait for fastbootd
    this.log('Waiting for device to enter fastbootd mode (this may take up to 60 seconds)...');
    this.log('USB disconnect/reconnect is normal during this transition');

    if (!(await this.transport.waitForFastbootd(90))) {
      this.log('Warning: Device not detected in fastbootd, attempting to continue...', 'warning');
      const testResult = await this.transport.fastbootdCommand(['getvar', 'is-userspace'], 5);
      if (!testResult.success || !testResult.stdout?.toLowerCase().includes('yes')) {
        this.log('Device is not in fastbootd mode', 'error');
        return false;
      }
    }

    this.log('Device successfully entered fastbootd mode');
    return true;
  }

  private async flashSuperInFastbootd(): Promise<boolean> {
    this.log('='.repeat(60));
    this.log('Flashing super partition in fastbootd mode');
    this.log('Super images MUST be flashed in fastbootd (not bootloader fastboot)');
    this.log('='.repeat(60));

    // Find super images
    let superImages: any[] = [];
    if (this.partitionFiles['super']) {
      superImages = Array.isArray(this.partitionFiles['super'])
        ? this.partitionFiles['super']
        : [this.partitionFiles['super']];
    } else if (this.bundlePath) {
      // Try to find super_*.img files (would need file system access)
      // For now, assume they're in partitionFiles
      this.log('Warning: Super images not found in partition files', 'warning');
    }

    if (superImages.length === 0) {
      this.log('Error: No super partition images found', 'error');
      return false;
    }

    const totalSuper = superImages.length;
    this.log(`Found ${totalSuper} super partition image(s)`);

    // Flash each super image sequentially
    for (let idx = 0; idx < superImages.length; idx++) {
      const superImg = superImages[idx];
      const num = idx + 1;

      this.log(`Flashing super ${num}/${totalSuper}: ${superImg.name || superImg}`);
      this.updateProgress(
        FlashState.FASTBOOTD_FLASH,
        `Flashing Super ${num}/${totalSuper}`,
        `Flashing ${superImg.name || superImg}`,
        60 + Math.floor((num / totalSuper) * 35),
        'super',
        num,
        totalSuper
      );

      const result = await this.transport.fastbootdCommand(['flash', 'super', String(superImg)], 300);
      if (!result.success) {
        this.log(`Failed to flash super ${num}/${totalSuper}: ${result.stderr || 'Unknown error'}`, 'error');
        return false;
      }

      this.log(`✓ Super ${num}/${totalSuper} flashed`);
    }

    this.log('✓ All super partition images flashed successfully');
    return true;
  }

  private async lockBootloader(): Promise<boolean> {
    const result = await this.transport.fastbootdCommand(['flashing', 'lock'], 30);
    if (!result.success) {
      return false;
    }

    this.log('Bootloader locked successfully');
    return true;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private fileExists(path: string): boolean {
    // This is a placeholder - actual implementation depends on environment
    // In browser, we can't check file system directly
    // In Electron/Node.js, use fs.existsSync
    return false;
  }
}

