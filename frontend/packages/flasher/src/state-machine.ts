/**
 * Flash State Machine - Manages flashing workflow states
 */

import type { FlashState, FlashProgress } from './types';

export class FlashStateMachine {
  private currentState: FlashState = 'idle';
  private progress: FlashProgress;
  private stateListeners: Set<(state: FlashState) => void> = new Set();
  private progressListeners: Set<(progress: FlashProgress) => void> = new Set();

  constructor() {
    this.progress = {
      state: 'idle',
      step: 'Ready',
      progress: 0,
      message: 'Waiting to start...',
    };
  }

  /**
   * Get current state
   */
  getState(): FlashState {
    return this.currentState;
  }

  /**
   * Get current progress
   */
  getProgress(): FlashProgress {
    return { ...this.progress };
  }

  /**
   * Transition to new state
   */
  transition(state: FlashState, message: string, progress: number = 0): void {
    this.currentState = state;
    this.progress = {
      ...this.progress,
      state,
      step: this.getStepName(state),
      message,
      progress,
    };

    this.notifyStateListeners(state);
    this.notifyProgressListeners(this.progress);
  }

  /**
   * Update progress without changing state
   */
  updateProgress(progress: number, message?: string): void {
    this.progress = {
      ...this.progress,
      progress,
      message: message || this.progress.message,
    };

    this.notifyProgressListeners(this.progress);
  }

  /**
   * Update current image progress
   */
  updateImageProgress(currentImage: string, currentIndex: number, total: number): void {
    this.progress = {
      ...this.progress,
      currentImage,
      currentImageIndex: currentIndex,
      totalImages: total,
      progress: Math.round((currentIndex / total) * 100),
    };

    this.notifyProgressListeners(this.progress);
  }

  /**
   * Register state change listener
   */
  onStateChange(callback: (state: FlashState) => void): () => void {
    this.stateListeners.add(callback);
    return () => this.stateListeners.delete(callback);
  }

  /**
   * Register progress update listener
   */
  onProgressUpdate(callback: (progress: FlashProgress) => void): () => void {
    this.progressListeners.add(callback);
    return () => this.progressListeners.delete(callback);
  }

  /**
   * Reset state machine
   */
  reset(): void {
    this.transition('idle', 'Ready to start', 0);
  }

  /**
   * Get human-readable step name
   */
  private getStepName(state: FlashState): string {
    const stepNames: Record<FlashState, string> = {
      idle: 'Ready',
      device_connected: 'Device Connected',
      build_selected: 'Build Selected',
      downloading: 'Downloading Build',
      download_complete: 'Download Complete',
      rebooting_to_bootloader: 'Rebooting to Bootloader',
      fastboot_mode: 'Fastboot Mode',
      unlocking_bootloader: 'Unlocking Bootloader',
      flashing: 'Flashing GrapheneOS',
      flash_complete: 'Flash Complete',
      rebooting: 'Rebooting Device',
      complete: 'Complete',
      error: 'Error',
      device_disconnected: 'Device Disconnected',
    };

    return stepNames[state] || state;
  }

  /**
   * Notify state listeners
   */
  private notifyStateListeners(state: FlashState): void {
    this.stateListeners.forEach((callback) => callback(state));
  }

  /**
   * Notify progress listeners
   */
  private notifyProgressListeners(progress: FlashProgress): void {
    this.progressListeners.forEach((callback) => callback(progress));
  }
}

