/**
 * Download Manager - Handles build download with progress tracking
 */

import type { BuildInfo, DownloadProgress } from './types';

export class DownloadManager {
  private abortController: AbortController | null = null;
  private progressListeners: Set<(progress: DownloadProgress) => void> = new Set();

  /**
   * Download build from URL
   */
  async download(
    build: BuildInfo,
    onProgress?: (progress: DownloadProgress) => void
  ): Promise<Blob> {
    this.abortController = new AbortController();

    if (onProgress) {
      this.progressListeners.add(onProgress);
    }

    try {
      const response = await fetch(build.url, {
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      const contentLength = response.headers.get('content-length');
      const total = contentLength ? parseInt(contentLength, 10) : build.size;

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      let downloaded = 0;

      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        chunks.push(value);
        downloaded += value.length;

        const progress: DownloadProgress = {
          downloaded,
          total,
          progress: Math.round((downloaded / total) * 100),
        };

        this.notifyProgress(progress);
      }

      // Combine chunks into single blob
      const blob = new Blob(chunks);

      return blob;
    } finally {
      this.abortController = null;
    }
  }

  /**
   * Cancel download
   */
  cancel(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Verify SHA256 checksum
   */
  async verifyChecksum(blob: Blob, expectedSha256: string): Promise<boolean> {
    const arrayBuffer = await blob.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');

    return hashHex.toLowerCase() === expectedSha256.toLowerCase();
  }

  /**
   * Extract ZIP file
   */
  async extractZip(blob: Blob): Promise<Map<string, Blob>> {
    // Note: This requires a ZIP extraction library
    // For now, return a placeholder
    // In production, use a library like 'jszip' or 'fflate'
    throw new Error('ZIP extraction not yet implemented - use a library like jszip');
  }

  /**
   * Register progress listener
   */
  onProgress(callback: (progress: DownloadProgress) => void): () => void {
    this.progressListeners.add(callback);
    return () => this.progressListeners.delete(callback);
  }

  /**
   * Notify progress listeners
   */
  private notifyProgress(progress: DownloadProgress): void {
    this.progressListeners.forEach((callback) => callback(progress));
  }
}

