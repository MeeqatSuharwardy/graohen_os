/**
 * Flasher Page - Main flash wizard page
 * Google Pixel Web Flasher style
 */

import { useState, useEffect } from 'react';
import { DeviceCard, BuildSelector, ProgressBar, FlashSteps, WarningBanner, LogViewer } from '@flashdash/flasher-ui';
import { useDevice } from '@flashdash/flasher-ui/hooks/useDevice';
import { useFlasher } from '@flashdash/flasher-ui/hooks/useFlasher';
import type { BuildInfo } from '@flashdash/flasher-ui/components/BuildSelector';
import type { FlashState } from '@flashdash/flasher';

export function FlasherPage() {
  const { devices, loading, error, requestDevice, isSupported } = useDevice();
  const { isFlashing, progress, error: flashError, startFlash, cancelFlash } = useFlasher();
  const [selectedBuild, setSelectedBuild] = useState<BuildInfo | null>(null);
  const [availableBuilds, setAvailableBuilds] = useState<BuildInfo[]>([]);
  const [logs, setLogs] = useState<Array<{ message: string; level?: 'info' | 'warning' | 'error' }>>([]);

  // Sample builds (in production, fetch from API or metadata)
  useEffect(() => {
    // TODO: Fetch builds from API or metadata
    setAvailableBuilds([
      {
        codename: 'panther',
        version: '2025122500',
        url: 'https://releases.grapheneos.org/panther-factory-2025122500.zip',
        size: 2000000000, // 2GB
        date: '2025-12-25',
      },
    ]);
  }, []);

  const handleStartFlash = async () => {
    if (!devices.length || !selectedBuild) return;

    const device = devices[0];
    
    await startFlash({
      deviceSerial: device.serial,
      build: selectedBuild,
      skipUnlock: false,
      onProgress: (prog) => {
        setLogs((prev) => [...prev, { message: prog.message, level: 'info' }]);
      },
      onLog: (message, level) => {
        setLogs((prev) => [...prev, { message, level: level || 'info' }]);
      },
    });
  };

  const flashSteps = [
    { state: 'device_connected' as FlashState, label: 'Connect Device', description: 'Connect your Pixel device' },
    { state: 'build_selected' as FlashState, label: 'Select Build', description: 'Choose GrapheneOS build' },
    { state: 'downloading' as FlashState, label: 'Download Build', description: 'Download factory image' },
    { state: 'fastboot_mode' as FlashState, label: 'Enter Fastboot', description: 'Reboot to bootloader' },
    { state: 'flashing' as FlashState, label: 'Flash GrapheneOS', description: 'Flashing images...' },
    { state: 'complete' as FlashState, label: 'Complete', description: 'Flash completed' },
  ];

  const showWarning = isFlashing && progress?.state && ['flashing', 'unlocking_bootloader', 'fastboot_mode'].includes(progress.state);

  if (!isSupported) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-8 shadow-sm text-center">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          WebUSB Not Supported
        </h2>
        <p className="text-gray-600 mb-4">
          This app requires Chrome, Edge, or a Chromium-based browser with WebUSB support.
        </p>
        <p className="text-sm text-gray-500">
          Please use Chrome/Edge or download the desktop Electron app.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {showWarning && (
        <WarningBanner show={showWarning} message="⚠️ Do not disconnect your device" />
      )}

      <DeviceCard
        deviceSerial={devices[0]?.serial || ''}
        manufacturer={devices[0]?.manufacturer}
        model={devices[0]?.model}
        codename={devices[0]?.codename}
        state={devices[0]?.state || 'disconnected'}
        onConnect={requestDevice}
      />

      {devices.length > 0 && (
        <>
          <BuildSelector
            builds={availableBuilds}
            selectedBuild={selectedBuild}
            onSelectBuild={setSelectedBuild}
            loading={false}
          />

          {selectedBuild && (
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
              <button
                onClick={handleStartFlash}
                disabled={isFlashing || !selectedBuild}
                className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {isFlashing ? 'Flashing...' : 'Start Flashing'}
              </button>
              {isFlashing && (
                <button
                  onClick={cancelFlash}
                  className="w-full mt-2 px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          )}

          {progress && (
            <>
              <ProgressBar
                progress={progress.progress}
                message={progress.message}
                showPercentage={true}
                animated={true}
              />

              <FlashSteps currentState={progress.state} steps={flashSteps} />
            </>
          )}

          {logs.length > 0 && (
            <LogViewer logs={logs} maxLines={50} autoScroll={true} />
          )}
        </>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <p className="font-medium">Error</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      {flashError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          <p className="font-medium">Flash Error</p>
          <p className="text-sm mt-1">{flashError}</p>
        </div>
      )}
    </div>
  );
}
