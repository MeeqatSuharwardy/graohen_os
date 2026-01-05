import { useState, useEffect } from 'react';
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
import { Input } from '@flashdash/ui';
import { Loader2, Zap, AlertCircle, CheckCircle2, X } from 'lucide-react';
import { apiClient } from '../lib/api';

interface FlashDialogProps {
  trigger?: React.ReactNode;
}

export function FlashDialog({ trigger }: FlashDialogProps) {
  const [open, setOpen] = useState(false);
  const [purchaseNumber, setPurchaseNumber] = useState('');
  const [flashing, setFlashing] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deviceInfo, setDeviceInfo] = useState<{ codename?: string; deviceName?: string } | null>(null);

  useEffect(() => {
    if (!jobId) return;
    
    const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:17890';
    const eventSource = new EventSource(`${API_BASE_URL}/flash/jobs/${jobId}/stream`);
    
    const checkStatus = async () => {
      try {
        const response = await apiClient.get(`/flash/jobs/${jobId}`);
        const job = response.data;
        
        // Update status
        if (job.status !== status) {
          setStatus(job.status);
          if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
            setFlashing(false);
            clearInterval(statusInterval);
            eventSource.close();
          }
        }
      } catch (err: any) {
        // If job not found (404), it might have been cleared or never created
        if (err.response?.status === 404) {
          console.warn('Flash job not found, may have completed or been cleared');
          // Don't clear interval immediately, might be a timing issue
        }
        // Ignore other errors, will retry
      }
    };
    
    // Poll for status updates (non-blocking)
    const statusInterval = setInterval(checkStatus, 1000);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.line) {
          // Use functional update to avoid stale closures
          setLogs(prev => {
            // Avoid duplicates
            if (prev.length === 0 || prev[prev.length - 1] !== data.line) {
              return [...prev, data.line];
            }
            return prev;
          });
        }
      } catch (err) {
        console.error('Error parsing SSE message:', err);
      }
    };
    
    eventSource.addEventListener('status', (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus(data.status);
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          setFlashing(false);
          clearInterval(statusInterval);
          eventSource.close();
        }
      } catch (err) {
        console.error('Error parsing status event:', err);
      }
    });
    
    eventSource.addEventListener('log', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.line) {
          setLogs(prev => {
            if (prev.length === 0 || prev[prev.length - 1] !== data.line) {
              return [...prev, data.line];
            }
            return prev;
          });
        }
      } catch (err) {
        console.error('Error parsing log event:', err);
      }
    });
    
    eventSource.onerror = (err) => {
      console.error('EventSource error:', err);
      // Don't close on first error, might be temporary
    };
    
    return () => {
      clearInterval(statusInterval);
      eventSource.close();
    };
  }, [jobId, status]);

  const handleFlash = async () => {
    if (!purchaseNumber.trim()) {
      setError('Please enter a purchase number');
      return;
    }

    setFlashing(true);
    setError(null);
    setLogs([]);
    setStatus(null);
    setDeviceInfo(null);

    try {
      const serial = purchaseNumber.trim();
      
      // First, check device state - get all connected devices
      const devicesResponse = await apiClient.get('/devices');
      const devices = devicesResponse.data;
      
      // Try to find device by serial or id (exact match)
      let device = devices.find((d: any) => d.serial === serial || d.id === serial);
      
      // If not found by exact match, try to find any device in fastboot mode
      // This handles cases where purchase number might be different from serial
      if (!device && devices.length > 0) {
        // If there's only one device, use it
        if (devices.length === 1) {
          device = devices[0];
          setLogs([`Using detected device: ${device.serial} (${device.state} mode)`]);
        } else {
          // Try to find a device in fastboot mode
          device = devices.find((d: any) => d.state === 'fastboot');
          if (device) {
            setLogs([`Found device in fastboot mode: ${device.serial}. Using this device.`]);
          } else {
            // Try to find a device in ADB mode
            device = devices.find((d: any) => d.state === 'device');
            if (device) {
              setLogs([`Found device in ADB mode: ${device.serial}. Will reboot to fastboot.`]);
            }
          }
        }
      }
      
      // Use the actual device serial for flashing
      const deviceSerial = device ? (device.serial || device.id) : serial;
      
      if (!device) {
        setError('Device not detected. Please ensure device is connected and in ADB or Fastboot mode.');
        setFlashing(false);
        return;
      }
      
      // If device is in ADB mode, reboot to bootloader first
      if (device.state === 'device') {
        setStatus('rebooting');
        setLogs(prev => [...prev, 'Device detected in ADB mode. Rebooting to bootloader...']);
        
        try {
          await apiClient.post(`/devices/${deviceSerial}/reboot/bootloader`);
          setLogs(prev => [...prev, 'Reboot command sent. Waiting for device to enter fastboot mode...']);
          
          // Wait a bit for device to reboot
          await new Promise(resolve => setTimeout(resolve, 5000));
          
          // Check again
          const devicesResponse2 = await apiClient.get('/devices');
          const devices2 = devicesResponse2.data;
          const device2 = devices2.find((d: any) => (d.serial === deviceSerial || d.id === deviceSerial));
          
          if (device2 && device2.state !== 'fastboot') {
            setLogs(prev => [...prev, 'Waiting for device to enter fastboot mode. Please ensure device is in fastboot mode.']);
            // Continue anyway - the flash script will handle it
          }
        } catch (rebootErr: any) {
          setLogs(prev => [...prev, `Warning: Could not reboot automatically: ${rebootErr.message}`]);
          setLogs(prev => [...prev, 'Please manually reboot device to fastboot mode (hold Power + Volume Down)']);
        }
      } else if (device.state === 'fastboot') {
        setLogs(prev => [...prev, 'Device detected in fastboot mode. Ready to flash.']);
      }

      // Identify the device using the actual device serial (optional - flash will work without it)
      let deviceInfo: { codename?: string; deviceName?: string } | null = null;
      try {
        const identifyResponse = await apiClient.get(`/devices/${deviceSerial}/identify`);
        deviceInfo = identifyResponse.data;
        if (deviceInfo) {
          setDeviceInfo(deviceInfo);
          setLogs(prev => [...prev, `Device identified: ${deviceInfo!.deviceName || 'Unknown'} (${deviceInfo!.codename || 'Unknown'})`]);
        }
      } catch (identifyErr: any) {
        // If identification fails, we can still try to flash - the backend will find a bundle
        setLogs(prev => [...prev, `Note: Could not identify device codename (this is OK if device is in fastboot mode)`]);
        setLogs(prev => [...prev, 'Will attempt to use available local build...']);
      }

      // Start flash job (bundle_path will be auto-detected)
      setStatus('starting');
      setLogs(prev => [...prev, 'Starting flash process...']);
      
      try {
        const response = await apiClient.post('/flash/start', {
          device_serial: deviceSerial,
          dry_run: false,
          confirmation_token: `FLASH ${deviceSerial}`,
        });

        setJobId(response.data.job_id);
        setStatus('running');
        setLogs(prev => [...prev, `Flash job started: ${response.data.job_id}`]);
      } catch (flashErr: any) {
        const errorDetail = flashErr.response?.data?.detail || flashErr.message || 'Unknown error';
        setError(`Failed to start flash: ${errorDetail}`);
        setFlashing(false);
        setStatus('failed');
        setLogs(prev => [...prev, `Error: ${errorDetail}`]);
        return;
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start flash');
      setFlashing(false);
      setStatus('failed');
    }
  };

  const handleCancel = async () => {
    if (jobId) {
      try {
        await apiClient.post(`/flash/jobs/${jobId}/cancel`);
        setStatus('cancelled');
        setFlashing(false);
      } catch (err) {
        console.error('Failed to cancel:', err);
      }
    }
  };

  const handleClose = () => {
    if (!flashing) {
      setOpen(false);
      setPurchaseNumber('');
      setError(null);
      setLogs([]);
      setStatus(null);
      setJobId(null);
      setDeviceInfo(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
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
            Enter the purchase number (device serial) to automatically flash GrapheneOS
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
                Device identified: <strong>{deviceInfo.deviceName}</strong> ({deviceInfo.codename})
              </AlertDescription>
            </Alert>
          )}

          {!flashing ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Purchase Number (Device Serial)</label>
                <Input
                  type="text"
                  value={purchaseNumber}
                  onChange={(e) => setPurchaseNumber(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && purchaseNumber.trim()) {
                      handleFlash();
                    }
                  }}
                  placeholder="e.g., 100016754321"
                  disabled={flashing}
                />
                <p className="text-xs text-muted-foreground">
                  Enter the device serial number (or purchase number). The app will automatically:
                  <br />• Detect connected devices and use the appropriate one
                  <br />• Reboot to fastboot mode if needed
                  <br />• Find the latest local build for your device
                  <br />• Start flashing GrapheneOS
                  <br />
                  <br />
                  <strong>Tip:</strong> If only one device is connected, you can enter any number - the app will use the detected device.
                </p>
              </div>

              <Button
                onClick={handleFlash}
                disabled={!purchaseNumber.trim()}
                className="w-full"
              >
                <Zap className="w-4 h-4 mr-2" />
                Start Flashing
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="font-medium">
                    {status === 'rebooting' && 'Rebooting to bootloader...'}
                    {status === 'starting' && 'Starting flash...'}
                    {status === 'running' && 'Flashing device...'}
                    {status === 'completed' && 'Flash completed!'}
                    {status === 'failed' && 'Flash failed'}
                    {status === 'cancelled' && 'Flash cancelled'}
                    {!status && 'Preparing...'}
                  </span>
                </div>
                {status === 'running' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancel}
                  >
                    <X className="w-4 h-4 mr-2" />
                    Cancel
                  </Button>
                )}
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

              {(status === 'completed' || status === 'failed' || status === 'cancelled') && (
                <Button
                  onClick={handleClose}
                  className="w-full"
                >
                  Close
                </Button>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

