/**
 * Device Card - Shows device information and connection status
 * Google Pixel Web Flasher style
 */

import React from 'react';

export interface DeviceCardProps {
  deviceSerial: string;
  manufacturer?: string;
  model?: string;
  codename?: string;
  state: 'disconnected' | 'unauthorized' | 'device' | 'fastboot' | 'recovery';
  onConnect?: () => void;
}

export function DeviceCard({
  deviceSerial,
  manufacturer,
  model,
  codename,
  state,
  onConnect,
}: DeviceCardProps) {
  const getStateColor = () => {
    switch (state) {
      case 'device':
      case 'fastboot':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'unauthorized':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'recovery':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {model || manufacturer || 'Android Device'}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {deviceSerial}
          </p>
          {codename && (
            <span className="inline-block mt-2 px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded">
              {codename}
            </span>
          )}
        </div>
        <span className={`px-3 py-1 text-xs font-medium rounded-full border ${getStateColor()}`}>
          {state === 'device' ? 'ADB Mode' : state === 'fastboot' ? 'Fastboot Mode' : state}
        </span>
      </div>

      {state === 'disconnected' && onConnect && (
        <button
          onClick={onConnect}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Connect Device
        </button>
      )}

      {state === 'unauthorized' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="text-sm text-yellow-800">
            Device needs authorization. Please authorize USB debugging on your device.
          </p>
        </div>
      )}
    </div>
  );
}

