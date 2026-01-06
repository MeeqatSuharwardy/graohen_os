import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@flashdash/ui';
import { Button } from '@flashdash/ui';
import { Alert, AlertDescription } from '@flashdash/ui';
import { Loader2, Zap, AlertCircle, CheckCircle2, Smartphone } from 'lucide-react';
import { apiClient } from '../lib/api';

interface Device {
  id: string;
  serial: string;
  state: 'device' | 'fastboot' | 'unauthorized' | 'offline';
  codename?: string;
  deviceName?: string;
}

interface FlashDialogProps {
  trigger?: React.ReactNode;
  device?: Device; // Optional: pre-select a specific device
}

export function FlashDialog({ trigger, device: preselectedDevice }: FlashDialogProps) {
  const [open, setOpen] = useState(false);
  const [flashing, setFlashing] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deviceInfo, setDeviceInfo] = useState<{ codename?: string; deviceName?: string; serial?: string } | null>(null);

  const handleFlash = async () => {
    setFlashing(true);
    setError(null);
    setLogs([]);
    setStatus(null);
    setDeviceInfo(null);

    try {
      let device: Device | null = null;
      
      if (preselectedDevice) {
        // Use the preselected device
        device = preselectedDevice;
        setLogs([`Using device: ${device.serial} (${device.state} mode)`]);
      } else {
        // Auto-detect device
        setLogs(['Detecting connected devices...']);
        
        // Get all connected devices
        const devicesResponse = await apiClient.get('/devices');
        const devices = devicesResponse.data;
        
        if (!devices || devices.length === 0) {
          setError('No devices detected. Please ensure device is connected via USB and in ADB or Fastboot mode.');
          setFlashing(false);
          setLogs(prev => [...prev, '✗ No devices found']);
          return;
        }

        // Find device - prioritize fastboot mode, then ADB mode
        device = devices.find((d: any) => d.state === 'fastboot');
        if (!device) {
          device = devices.find((d: any) => d.state === 'device');
        }
        if (!device && devices.length > 0) {
          device = devices[0]; // Use first device as fallback
        }

        if (!device) {
          setError('No suitable device found. Please ensure device is in ADB or Fastboot mode.');
          setFlashing(false);
          setLogs(prev => [...prev, '✗ No suitable device found']);
          return;
        }

        setLogs(prev => [...prev, `Device detected: ${device!.serial} (${device!.state} mode)`]);
      }

      // At this point, device should not be null (we return early if it is)
      if (!device) {
        setError('No device found');
        setFlashing(false);
        return;
      }

      const deviceSerial = device.serial || device.id;

      // Identify device to get codename
      if (device.codename) {
        setDeviceInfo({
          codename: device.codename,
          deviceName: device.deviceName || device.codename,
          serial: deviceSerial
        });
        setLogs(prev => [...prev, `Device identified: ${device.deviceName || device.codename} (${device.codename})`]);
      } else {
        // Try to identify
        try {
          const identifyResponse = await apiClient.get(`/devices/${deviceSerial}/identify`);
          setDeviceInfo({
            ...identifyResponse.data,
            serial: deviceSerial
          });
          setLogs(prev => [...prev, `Device identified: ${identifyResponse.data.deviceName} (${identifyResponse.data.codename})`]);
        } catch (identifyErr: any) {
          setLogs(prev => [...prev, 'Note: Could not identify device codename. Will try to use available local build.']);
        }
      }

      // If device is in ADB mode, reboot to bootloader first
      if (device.state === 'device') {
        setStatus('rebooting');
        setLogs(prev => [...prev, 'Device in ADB mode. Rebooting to bootloader...']);
        
        try {
          await apiClient.post(`/devices/${deviceSerial}/reboot/bootloader`);
          setLogs(prev => [...prev, 'Reboot command sent. Waiting for device to enter fastboot mode...']);
          
          // Wait for device to reboot
          await new Promise(resolve => setTimeout(resolve, 5000));
          
          // Check again
          const devicesResponse2 = await apiClient.get('/devices');
          const devices2 = devicesResponse2.data;
          const device2 = devices2.find((d: any) => (d.serial === deviceSerial || d.id === deviceSerial));
          
          if (device2 && device2.state !== 'fastboot') {
            setLogs(prev => [...prev, 'Warning: Device may not have entered fastboot mode. Continuing anyway...']);
          } else if (device2) {
            setLogs(prev => [...prev, 'Device successfully entered fastboot mode.']);
          }
        } catch (rebootErr: any) {
          setLogs(prev => [...prev, `Warning: Could not reboot automatically: ${rebootErr.message}. Please manually reboot to fastboot mode.`]);
          // Continue anyway - user can manually reboot
        }
      }

      // Execute flash - backend will auto-detect bundle
      setStatus('running');
      setLogs(prev => [...prev, 'Starting flash process...']);
      
      try {
        const response = await apiClient.post('/flash/execute', {
          device_serial: deviceSerial,
          dry_run: false,
          confirmation_token: `FLASH ${deviceSerial}`,
        });

        const result = response.data;
        
        // Always show all logs from the result
        if (result.logs && Array.isArray(result.logs)) {
          setLogs(result.logs);
        } else {
          setLogs([result.message || 'Flash executed']);
        }
        
        if (result.success) {
          setStatus('completed');
          setLogs(prev => [...prev, '✓ Flash completed successfully!']);
        } else {
          setStatus('failed');
          const errorMsg = result.message || result.error || 'Flash failed';
          setError(errorMsg);
          if (result.logs && result.logs.length > 0) {
            const hasError = result.logs.some((log: string) => log.includes(errorMsg));
            if (!hasError) {
              setLogs(prev => [...prev, `✗ Error: ${errorMsg}`]);
            }
          } else {
            setLogs([`✗ Flash failed: ${errorMsg}`]);
          }
        }
        
        setFlashing(false);
      } catch (flashErr: any) {
        const errorDetail = flashErr.response?.data?.detail || flashErr.message || 'Unknown error';
        setError(`Failed to execute flash: ${errorDetail}`);
        setFlashing(false);
        setStatus('failed');
        setLogs(prev => [...prev, `Error: ${errorDetail}`]);
        return;
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start flash');
      setFlashing(false);
      setStatus('failed');
      setLogs(prev => [...prev, `Error: ${err.response?.data?.detail || err.message || 'Unknown error'}`]);
    }
  };

  const handleClose = () => {
    if (!flashing) {
      setOpen(false);
      setError(null);
      setLogs([]);
      setStatus(null);
      setDeviceInfo(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        {trigger || (
          <Button>
            <Zap className="w-4 h-4 mr-2" />
            Flash Device
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Flash GrapheneOS</DialogTitle>
          <DialogDescription>
            {preselectedDevice 
              ? `Flash ${preselectedDevice.deviceName || preselectedDevice.codename || preselectedDevice.serial} using local build`
              : 'Automatically detect device and flash using local build'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {deviceInfo && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                Device: <strong>{deviceInfo.deviceName}</strong> ({deviceInfo.codename})
                {deviceInfo.serial && <span className="ml-2 text-xs text-muted-foreground">({deviceInfo.serial})</span>}
              </AlertDescription>
            </Alert>
          )}

          {!flashing ? (
            <div className="space-y-4">
              <div className="text-center py-6">
                <Smartphone className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground mb-4">
                  Connect your device via USB and ensure it's in ADB or Fastboot mode.
                  <br />
                  The app will automatically:
                </p>
                <ul className="text-sm text-muted-foreground text-left max-w-md mx-auto space-y-2">
                  <li>• Detect connected device</li>
                  <li>• Reboot to fastboot mode if needed</li>
                  <li>• Find local build from bundles folder</li>
                  <li>• Flash GrapheneOS</li>
                </ul>
              </div>

              <Button
                onClick={handleFlash}
                className="w-full"
                size="lg"
              >
                <Zap className="w-4 h-4 mr-2" />
                Flash Device
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="font-medium">
                    {status === 'rebooting' && 'Rebooting to bootloader...'}
                    {status === 'running' && 'Flashing device...'}
                    {status === 'completed' && 'Flash completed!'}
                    {status === 'failed' && 'Flash failed'}
                    {!status && 'Preparing...'}
                  </span>
                </div>
              </div>

              {logs.length > 0 && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Flash Logs</label>
                  <div className="p-4 rounded-lg border bg-muted/50 font-mono text-xs max-h-[300px] overflow-y-auto">
                    {logs.map((log, index) => (
                      <div key={index} className="mb-1">
                        {log}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {status === 'completed' && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>
                    Flash completed successfully! Your device should now be running GrapheneOS.
                  </AlertDescription>
                </Alert>
              )}

              {status === 'failed' && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Flash failed. Check the logs above for details.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
