/**
 * Build Manager for Frontend
 * 
 * Handles bundle location and download for frontend applications.
 * Can fetch bundles from backend API or use local file system (Electron).
 */

import type { BuildManager } from '../flash-engine';

export interface FrontendBuildManagerOptions {
  apiBaseUrl?: string;
  bundleDownloadUrl?: (codename: string, version: string) => string;
}

export class FrontendBuildManager implements BuildManager {
  private apiBaseUrl: string;
  private bundleDownloadUrl?: (codename: string, version: string) => string;

  constructor(options: FrontendBuildManagerOptions = {}) {
    this.apiBaseUrl = options.apiBaseUrl || 'http://127.0.0.1:17890';
    this.bundleDownloadUrl = options.bundleDownloadUrl;
  }

  async getBundlePath(codename: string, version?: string): Promise<string | null> {
    try {
      // Query backend API for bundle information
      const url = version
        ? `${this.apiBaseUrl}/bundles/for/${codename}?version=${version}`
        : `${this.apiBaseUrl}/bundles/for/${codename}`;

      const response = await fetch(url);
      if (!response.ok) {
        return null;
      }

      const data = await response.json();
      return data.path || null;
    } catch (error) {
      console.error('Failed to get bundle path:', error);
      return null;
    }
  }

  async ensureBundleAvailable(
    codename: string,
    version?: string,
    onProgress?: (progress: number) => void
  ): Promise<string> {
    // Check if bundle exists
    let bundlePath = await this.getBundlePath(codename, version);

    if (!bundlePath) {
      // Bundle not found - download it
      console.log(`Bundle not found, downloading: ${codename} ${version || 'latest'}`);

      // Find latest version if not specified
      if (!version) {
        try {
          const response = await fetch(`${this.apiBaseUrl}/bundles/find-latest/${codename}`);
          if (response.ok) {
            const data = await response.json();
            version = data.version;
          }
        } catch (error) {
          console.error('Failed to find latest version:', error);
        }
      }

      // Start download
      if (version) {
        bundlePath = await this.downloadBundle(codename, version, onProgress);
      } else {
        throw new Error(`Could not determine bundle version for ${codename}`);
      }
    }

    // Find install directory within bundle
    return this.findInstallDirectory(bundlePath);
  }

  private async downloadBundle(
    codename: string,
    version: string,
    onProgress?: (progress: number) => void
  ): Promise<string> {
    try {
      // Start download via backend API
      const response = await fetch(`${this.apiBaseUrl}/bundles/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codename, version }),
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      const data = await response.json();
      const downloadId = data.download_id;

      // Poll for download progress
      return new Promise((resolve, reject) => {
        const pollInterval = setInterval(async () => {
          try {
            const statusResponse = await fetch(`${this.apiBaseUrl}/bundles/download/${downloadId}/status`);
            if (!statusResponse.ok) {
              clearInterval(pollInterval);
              reject(new Error('Failed to get download status'));
              return;
            }

            const status = await statusResponse.json();
            const progress = status.progress || 0;

            if (onProgress) {
              onProgress(progress);
            }

            if (status.status === 'completed') {
              clearInterval(pollInterval);
              resolve(status.bundle_path);
            } else if (status.status === 'failed') {
              clearInterval(pollInterval);
              reject(new Error(status.error || 'Download failed'));
            }
          } catch (error) {
            clearInterval(pollInterval);
            reject(error);
          }
        }, 1000); // Poll every second
      });
    } catch (error) {
      throw new Error(`Bundle download failed: ${error}`);
    }
  }

  private async findInstallDirectory(bundlePath: string): Promise<string> {
    // In browser, we can't directly check file system
    // We'll assume the path is correct, or fetch bundle info from backend
    try {
      // Query backend for bundle info which should include install directory
      const response = await fetch(`${this.apiBaseUrl}/bundles/info?path=${encodeURIComponent(bundlePath)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.install_directory) {
          return data.install_directory;
        }
      }
    } catch (error) {
      console.warn('Failed to get bundle info, using path as-is:', error);
    }

    // Fallback: assume bundle path is the install directory
    // In Electron, we could check file system directly
    return bundlePath;
  }

  async findPartitionFiles(bundlePath: string): Promise<Record<string, any>> {
    // Query backend API for partition files
    try {
      const response = await fetch(
        `${this.apiBaseUrl}/bundles/partitions?path=${encodeURIComponent(bundlePath)}`
      );

      if (response.ok) {
        const data = await response.json();
        return data.partition_files || {};
      }
    } catch (error) {
      console.error('Failed to get partition files:', error);
    }

    // Fallback: return empty (actual implementation would need file system access)
    return {};
  }
}

