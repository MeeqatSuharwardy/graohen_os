/**
 * Build Selector - Select GrapheneOS build to flash
 * Google Pixel Web Flasher style
 */

import React from 'react';

export interface BuildInfo {
  codename: string;
  version: string;
  url: string;
  size: number;
  date?: string;
}

export interface BuildSelectorProps {
  builds: BuildInfo[];
  selectedBuild?: BuildInfo | null;
  onSelectBuild: (build: BuildInfo) => void;
  loading?: boolean;
}

export function BuildSelector({
  builds,
  selectedBuild,
  onSelectBuild,
  loading = false,
}: BuildSelectorProps) {
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Build</h3>

      {loading ? (
        <div className="text-center py-8 text-gray-500">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2">Loading builds...</p>
        </div>
      ) : builds.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No builds available</p>
        </div>
      ) : (
        <div className="space-y-2">
          {builds.map((build) => (
            <button
              key={`${build.codename}-${build.version}`}
              onClick={() => onSelectBuild(build)}
              className={`w-full text-left p-4 rounded-lg border transition-colors ${
                selectedBuild?.version === build.version
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">
                    Version {build.version}
                  </div>
                  {build.date && (
                    <div className="text-sm text-gray-500 mt-1">
                      {new Date(build.date).toLocaleDateString()}
                    </div>
                  )}
                </div>
                <div className="text-sm text-gray-600">
                  {formatFileSize(build.size)}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

