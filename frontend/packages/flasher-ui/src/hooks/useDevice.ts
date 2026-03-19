/**
 * useDevice Hook - React hook for device management
 */

import { useEffect, useState } from 'react';
import { DeviceManager } from '@flashdash/device-manager';
import type { DeviceInfo } from '@flashdash/device-manager';

export function useDevice() {
  const [deviceManager] = useState(() => new DeviceManager());
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!DeviceManager.isSupported()) {
      setError('WebUSB is not supported. Please use Chrome/Edge or Chromium-based browser.');
      setLoading(false);
      return;
    }

    // Start device detection
    deviceManager.startDetection();

    // Listen for device changes
    const unsubscribeConnected = deviceManager.onDeviceConnected((device) => {
      setDevices((prev) => {
        const existing = prev.find((d) => d.serial === device.serial);
        if (existing) {
          return prev.map((d) => (d.serial === device.serial ? device : d));
        }
        return [...prev, device];
      });
      setLoading(false);
    });

    const unsubscribeDisconnected = deviceManager.onDeviceDisconnected((serial) => {
      setDevices((prev) => prev.filter((d) => d.serial !== serial));
    });

    // Initial device list
    setDevices(deviceManager.getDevices());
    setLoading(false);

    return () => {
      deviceManager.stopDetection();
      unsubscribeConnected();
      unsubscribeDisconnected();
    };
  }, [deviceManager]);

  const requestDevice = async () => {
    try {
      setError(null);
      await deviceManager.requestDevice();
    } catch (err: any) {
      setError(err.message || 'Failed to request device');
    }
  };

  const connectDevice = async (serial: string) => {
    try {
      setError(null);
      await deviceManager.connectDevice(serial);
    } catch (err: any) {
      setError(err.message || 'Failed to connect device');
    }
  };

  return {
    devices,
    loading,
    error,
    requestDevice,
    connectDevice,
    isSupported: DeviceManager.isSupported(),
  };
}

