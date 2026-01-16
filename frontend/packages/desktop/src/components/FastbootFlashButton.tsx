import { useState, useEffect, useRef } from 'react';
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
import { Progress } from '@flashdash/ui';
import { Loader2, Zap, AlertCircle, CheckCircle2, Smartphone, Wifi, WifiOff, Activity, Download } from 'lucide-react';
import { apiClient } from '../lib/api';

interface Device {
  id: string;
  serial: string;
  state: 'device' | 'fastboot' | 'unauthorized' | 'offline';
  codename?: string;
  deviceName?: string;
}

interface FastbootFlashButtonProps {
  device: Device;
  trigger?: React.ReactNode;
}

export function FastbootFlashButton({ device, trigger }: FastbootFlashButtonProps) {
  const [open, setOpen] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [deviceConnected, setDeviceConnected] = useState<boolean>(true);
  const [progress, setProgress] = useState<number>(0);
  const [currentStep, setCurrentStep] = useState<string>('');
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  // Download states
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const [bundleAvailable, setBundleAvailable] = useState<boolean | null>(null);
  
  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Poll device connection status while flashing - but don't let disconnection stop the process
  useEffect(() => {
    if (!processing || !open) return;

    const devicePollInterval = setInterval(async () => {
      try {
        const response = await apiClient.get('/devices/');
        const devices: Device[] = response.data || [];
        const deviceSerial = device.serial || device.id;
        
        // Look for device in any state during flashing (fastboot, device, or even if it temporarily disconnects)
        const foundDevice = devices.find(d => 
          d.serial === deviceSerial || d.id === deviceSerial
        );
        
        if (foundDevice) {
          // Device found - update connection status
          const isConnected = foundDevice.state === 'fastboot' || foundDevice.state === 'device';
          const wasConnected = deviceConnected;
          setDeviceConnected(isConnected);
          
          // Log reconnection if device was disconnected and is now back
          if (!wasConnected && isConnected) {
            setLogs(prev => [...prev, `✓ Device reconnected (state: ${foundDevice.state})`]);
          }
        } else {
          // Device not found - might be temporarily disconnected during fastboot operations
          // Update connection status to show "Disconnected" in UI
          const wasConnected = deviceConnected;
          setDeviceConnected(false);
          
          // Log disconnect only once when it first happens
          if (wasConnected) {
            setLogs(prev => [...prev, `⚠ Device disconnected (common during fastboot operations - it will reconnect)`]);
          }
          // Don't interrupt flash process - device will reconnect during flash operations
        }
      } catch (err) {
        // Don't assume disconnected on error - network issues might be temporary
        // Only log if this is a persistent issue
        console.warn('Could not check device status:', err);
      }
    }, 3000); // Check every 3 seconds (reduced frequency to avoid too many requests)

    return () => clearInterval(devicePollInterval);
  }, [processing, open, device.serial, device.id, deviceConnected]);

  // Check if bundle is available
  const checkBundleAvailability = async (): Promise<boolean> => {
    try {
      const codename = device.codename || 'panther'; // Default to panther for Pixel 7
      const response = await apiClient.get(`/bundles/for/${codename}`);
      return !!response.data?.path;
    } catch (err: any) {
      console.log('Bundle not found:', err.response?.data?.detail || err.message);
      return false;
    }
  };

  // Reset state when dialog opens/closes and check bundle availability
  useEffect(() => {
    if (!open) {
      // Reset all states when dialog closes
      setProcessing(false);
      setDownloading(false);
      setDownloadProgress(0);
      setProgress(0);
      setCurrentStep('');
      setError(null);
      setLogs([]);
      setStatus(null);
      setJobId(null);
      setBundleAvailable(null);
      setDeviceConnected(true);
    } else if (open && bundleAvailable === null) {
      // When dialog opens, check if bundle exists
      checkBundleAvailability().then(exists => {
        setBundleAvailable(exists);
      }).catch(() => {
        setBundleAvailable(false);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Calculate progress and current step from logs
  useEffect(() => {
    if (!logs.length || (!processing && !downloading)) return;

    // Parse logs to determine progress
    let calculatedProgress = 0;
    let step = '';

    // Flash workflow steps (approximate progress based on actual workflow)
    const steps = [
      { keyword: 'preflight', progress: 2, label: 'Preflight checks' },
      { keyword: 'validate', progress: 5, label: 'Validating device state' },
      { keyword: 'reboot_fastboot', progress: 8, label: 'Rebooting to bootloader' },
      { keyword: 'Locating bundle', progress: 10, label: 'Locating bundle directory' },
      { keyword: 'Found.*partition', progress: 12, label: 'Found partition files' },
      { keyword: 'Verifying device product', progress: 15, label: 'Verifying device' },
      { keyword: 'Flashing bootloader', progress: 30, label: 'Flashing bootloader' },
      { keyword: 'Waiting for device', progress: 35, label: 'Waiting for device reconnect' },
      { keyword: 'Device.*detected', progress: 40, label: 'Device reconnected' },
      { keyword: 'Flashing radio', progress: 50, label: 'Flashing radio' },
      { keyword: 'Erasing AVB', progress: 55, label: 'Erasing AVB custom key' },
      { keyword: 'Flashing.*avb', progress: 57, label: 'Flashing AVB key' },
      { keyword: 'Erasing fips', progress: 60, label: 'Erasing partitions' },
      { keyword: 'Validating android-info', progress: 65, label: 'Validating requirements' },
      { keyword: 'Flashing boot', progress: 70, label: 'Flashing boot partition' },
      { keyword: 'Flashing init_boot', progress: 72, label: 'Flashing init_boot' },
      { keyword: 'Flashing vendor_boot', progress: 74, label: 'Flashing vendor_boot' },
      { keyword: 'Flashing dtbo', progress: 76, label: 'Flashing dtbo' },
      { keyword: 'Flashing vbmeta', progress: 78, label: 'Flashing vbmeta' },
      { keyword: 'Erasing userdata', progress: 82, label: 'Erasing userdata' },
      { keyword: 'Erasing metadata', progress: 84, label: 'Erasing metadata' },
      { keyword: 'Flashing super', progress: 88, label: 'Flashing super partition' },
      { keyword: 'Device rebooting', progress: 98, label: 'Rebooting device' },
      { keyword: 'completed successfully', progress: 100, label: 'Flash completed' },
    ];

    // Find the latest step (check logs in reverse order to get most recent)
    for (let i = logs.length - 1; i >= 0; i--) {
      const log = logs[i].toLowerCase();
      for (const stepInfo of steps) {
        // Support both exact keyword match and regex match
        const keyword = stepInfo.keyword.toLowerCase();
        const regex = new RegExp(keyword.replace(/\*/g, '.*'), 'i');
        if (log.includes(keyword) || regex.test(log)) {
          if (stepInfo.progress > calculatedProgress) {
            calculatedProgress = stepInfo.progress;
            step = stepInfo.label || stepInfo.keyword;
          }
        }
      }
    }

    // If we see specific partition names, be more granular
    if (logs.some(l => l.includes('super') && (l.includes('Flashing') || l.includes('flash')))) {
      const superMatches = logs.filter(l => 
        (l.includes('super') && (l.includes('Flashing') || l.includes('flash'))) ||
        /super_\d+\.img/.test(l)
      );
      // Extract super partition number from logs (super_1.img through super_14.img = 14 parts)
      const superNumbers = superMatches
        .map(l => {
          const match = l.match(/super_(\d+)/i);
          return match ? parseInt(match[1]) : 0;
        })
        .filter(n => n > 0 && n <= 14);
      const uniqueSuperNumbers = [...new Set(superNumbers)];
      const superProgress = Math.min(88 + (uniqueSuperNumbers.length / 14) * 10, 98);
      if (superProgress > calculatedProgress) {
        calculatedProgress = superProgress;
        step = `Flashing super partition (${uniqueSuperNumbers.length}/14)`;
      }
    }

    // If we're waiting for device, show that as current step
    if (logs.some(l => l.includes('Waiting for device') || l.includes('Waiting for device to return'))) {
      step = 'Waiting for device to reconnect...';
    }

    setProgress(calculatedProgress);
    if (step) {
      setCurrentStep(step);
    }

    // Check for completion
    if (logs.some(l => l.includes('completed successfully') || l.includes('Flash completed'))) {
      setProgress(100);
      setCurrentStep('Flash completed successfully');
      setStatus('completed');
      setProcessing(false);
    }

    // Check for failures
    if (logs.some(l => l.includes('ERROR') || l.includes('failed') || l.includes('Failed'))) {
      const errorLogs = logs.filter(l => 
        l.includes('ERROR') || l.includes('error') || l.includes('failed') || l.includes('Failed')
      );
      if (errorLogs.length > 0) {
        setError(errorLogs[errorLogs.length - 1]);
      }
    }
  }, [logs, processing]);

  // Poll for job status and logs if we have a job ID
  useEffect(() => {
    if (!jobId) return;

    let eventSource: EventSource | null = null;

    // Try SSE streaming first
    try {
      const baseUrl = apiClient.defaults.baseURL || 'http://127.0.0.1:17890';
      const streamUrl = `${baseUrl}/flash/jobs/${jobId}/stream`;
      
      eventSource = new EventSource(streamUrl);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.log || data.line) {
            const logLine = data.log || data.line;
            setLogs(prev => {
              // Avoid duplicates
              if (prev.length > 0 && prev[prev.length - 1] === logLine) {
                return prev;
              }
              return [...prev, logLine];
            });
          }
          if (data.status) {
            setStatus(data.status);
            if (data.status === 'completed') {
              setProcessing(false);
              setCurrentStep('Flash completed successfully');
              setProgress(100);
              setLogs(prev => [...prev, '✅ Flash process completed successfully!']);
              // Keep dialog open - let user close manually
              if (eventSource) eventSource.close();
            } else if (data.status === 'failed' || data.status === 'cancelled') {
              setProcessing(false);
              setCurrentStep('Flash failed');
              // Keep dialog open - let user close manually to see all logs
              if (eventSource) eventSource.close();
            } else if (data.status === 'running') {
              // Update progress if available
              if (data.progress !== undefined) {
                setProgress(data.progress);
              }
            }
          }
        } catch (e) {
          // If parsing fails, try adding as plain text
          if (event.data) {
            setLogs(prev => [...prev, event.data]);
          }
        }
      };

      eventSource.onerror = (err) => {
        console.warn('SSE connection error, falling back to polling:', err);
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
      };
    } catch (e) {
      console.warn('Failed to establish SSE connection, using polling:', e);
    }

    // Polling as fallback
    const pollInterval = setInterval(async () => {
      try {
        const response = await apiClient.get(`/flash/jobs/${jobId}`, {
          timeout: 60000, // 60 seconds timeout for polling
        });
        const job = response.data;

        if (job.logs && Array.isArray(job.logs)) {
          setLogs(job.logs);
        }

        if (job.status === 'completed') {
          setStatus('completed');
          setProcessing(false);
          setCurrentStep('Flash completed successfully');
          setProgress(100);
          setLogs(prev => [...prev, '✅ Flash process completed successfully!']);
          // Keep dialog open - let user close manually
          if (eventSource) eventSource.close();
          clearInterval(pollInterval);
        } else if (job.status === 'failed' || job.status === 'cancelled') {
          setStatus('failed');
          setProcessing(false);
          setCurrentStep('Flash failed');
          if (job.logs && job.logs.length > 0) {
            const errorLogs = job.logs.filter((log: string) => 
              log.includes('ERROR') || log.includes('error') || log.includes('failed') || log.includes('Failed')
            );
            if (errorLogs.length > 0) {
              setError(errorLogs[errorLogs.length - 1]);
            }
            // Add all logs including errors
            setLogs(job.logs);
          }
          // Keep dialog open - let user close manually to see all logs
          if (eventSource) eventSource.close();
          clearInterval(pollInterval);
        } else if (job.status === 'running') {
          // Update progress if available
          if (job.progress !== undefined) {
            setProgress(job.progress);
          }
          // Keep processing state and continue logging
        }
      } catch (err: any) {
        // Don't log timeout errors as errors - they're expected during long operations
        if (err.code !== 'ECONNABORTED' && !err.message?.includes('timeout')) {
          console.error('Error polling job status:', err);
        }
      }
    }, 2000);

    return () => {
      if (eventSource) eventSource.close();
      clearInterval(pollInterval);
    };
  }, [jobId, processing]);

  // Download bundle if not available
  const downloadBundle = async (): Promise<string | null> => {
    try {
      const codename = device.codename || 'panther';
      
      // First, find the latest version
      let version: string;
      try {
        const latestResponse = await apiClient.get(`/bundles/find-latest/${codename}`);
        version = latestResponse.data.version;
        setLogs(prev => [...prev, `Latest version found: ${version}`]);
      } catch (err: any) {
        throw new Error(`Could not find latest version: ${err.response?.data?.detail || err.message}`);
      }

      // Start download
      setLogs(prev => [...prev, `Starting download of GrapheneOS ${version}...`]);
      const downloadResponse = await apiClient.post('/bundles/download', {
        codename,
        version,
      });
      
      const downloadId = downloadResponse.data.download_id;
      setDownloading(true);
      setDownloadProgress(0);
      
      // Poll for download progress
      const pollDownload = async (): Promise<string> => {
        return new Promise((resolve, reject) => {
          const interval = setInterval(async () => {
            try {
              const statusResponse = await apiClient.get(`/bundles/download/${downloadId}/status`);
              const status = statusResponse.data;
              
              if (status.status === 'downloading') {
                setDownloadProgress(status.progress || 0);
              } else if (status.status === 'completed') {
                setDownloadProgress(100);
                setDownloading(false);
                clearInterval(interval);
                setLogs(prev => [...prev, `✓ Download completed successfully`]);
                setBundleAvailable(true);
                resolve(status.result?.path || '');
              } else if (status.status === 'error') {
                setDownloading(false);
                clearInterval(interval);
                reject(new Error(status.error || 'Download failed'));
              }
            } catch (err: any) {
              clearInterval(interval);
              reject(err);
            }
          }, 1000); // Poll every second
        });
      };
      
      return await pollDownload();
    } catch (err: any) {
      setDownloading(false);
      const errorMsg = err.response?.data?.detail || err.message || 'Download failed';
      setError(`Failed to download bundle: ${errorMsg}`);
      setLogs(prev => [...prev, `❌ Download error: ${errorMsg}`]);
      throw err;
    }
  };

  // Start flash process
  const startFlashProcess = async () => {
    try {
      const deviceSerial = device.serial || device.id;
      console.log('Starting flash for device:', deviceSerial);
      setLogs(prev => [...prev, 'Starting flash process...']);

      // Call the unlock-and-flash endpoint with skip_unlock=true
      const response = await apiClient.post('/flash/unlock-and-flash', {
        device_serial: deviceSerial,
        skip_unlock: true, // Skip unlock since device is already unlocked
      }, {
        timeout: 120000, // 120 seconds timeout
      });

      console.log('API response:', response.data);
      const result = response.data;
      
      if (result.success && result.job_id) {
        console.log('Job started:', result.job_id);
        setJobId(result.job_id);
        setLogs(prev => [...prev, '✓ Flash process started...']);
        setStatus('running');
      } else {
        throw new Error(result.message || 'Failed to start flash');
      }
    } catch (err: any) {
      console.error('Error in startFlashProcess:', err);
      
      let errorDetail = err.message || 'Unknown error';
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorDetail = 'Request timed out. The backend may be busy. Please try again.';
      } else if (err.response?.data?.detail) {
        errorDetail = err.response.data.detail;
      } else if (err.response?.data?.message) {
        errorDetail = err.response.data.message;
      }
      
      setError(`Failed to start flash: ${errorDetail}`);
      setProcessing(false);
      setStatus('failed');
      setLogs(prev => [...prev, `❌ Error: ${errorDetail}`]);
      throw err;
    }
  };

  const handleFlash = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    
    if (processing || downloading) {
      console.log('Already processing, ignoring click');
      return;
    }
    
    if (device.state !== 'fastboot') {
      setError('Device must be in fastboot mode. Please reboot to fastboot mode first.');
      return;
    }

    setProcessing(true);
    setError(null);
    
    // Add initial log with device state warning if needed
    const initialLogs = ['Checking for bundle availability...'];
    if (device.state !== 'fastboot') {
      initialLogs.push(`⚠ Warning: Device state is "${device.state}" (expected "fastboot"). Attempting flash anyway...`);
    }
    setLogs(initialLogs);
    setStatus('starting');
    setJobId(null);
    setProgress(0);
    setCurrentStep('Checking bundle...');
    setDeviceConnected(true);

    try {
      // Step 1: Check if bundle is available
      const bundleExists = await checkBundleAvailability();
      
      if (!bundleExists) {
        setLogs(prev => [...prev, 'Bundle not found. Starting download...']);
        setCurrentStep('Downloading bundle...');
        
        try {
          await downloadBundle();
          // Download completed, wait a moment then proceed
          setLogs(prev => [...prev, 'Bundle ready. Starting flash...']);
          setCurrentStep('Starting flash...');
          await new Promise(resolve => setTimeout(resolve, 1000)); // Brief pause
        } catch (downloadErr) {
          // Download error already logged and displayed
          setProcessing(false);
          setStatus('failed');
          return;
        }
      } else {
        setLogs(prev => [...prev, '✓ Bundle found. Proceeding to flash...']);
        setBundleAvailable(true);
      }
      
      // Step 2: Start flash process
      setCurrentStep('Initializing flash process...');
      await startFlashProcess();
      
    } catch (err: any) {
      console.error('Error in handleFlash:', err);
      
      if (!error) {
        // Only set generic error if we don't already have a specific one
        const errorDetail = err.response?.data?.detail || err.message || 'Unknown error';
        setError(`Failed to start flash: ${errorDetail}`);
        setLogs(prev => [...prev, `❌ Error: ${errorDetail}`]);
      }
      
      setProcessing(false);
      setStatus('failed');
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    // CRITICAL: Always allow user to manually close the dialog
    // But NEVER close automatically - user must explicitly close even during device disconnects
    setOpen(newOpen);
    
    // Only reset state when user explicitly closes AND process is complete/failed
    // If process is still running or device disconnected, keep the dialog open to show continuous logs
    if (!newOpen) {
      // Only reset if not actively processing AND not downloading AND status is not running
      if (!processing && !downloading && status !== 'running' && status !== 'starting') {
        setError(null);
        setLogs([]);
        setStatus(null);
        setJobId(null);
        setProgress(0);
        setCurrentStep('');
        setDeviceConnected(true);
        setDownloading(false);
        setDownloadProgress(0);
      } else if (processing || downloading || status === 'running') {
        // If still processing/downloading, log but allow close
        // Don't reset state - user can reopen to see logs
        // The flash will continue in the background
        console.log('Flash is still in progress, but dialog closed by user');
        setLogs(prev => [...prev, '⚠ Dialog closed by user, but flash process continues in background']);
      }
    }
    // If opening, don't do anything - let the dialog stay open
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {trigger}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Flash GrapheneOS
          </DialogTitle>
          <DialogDescription>
            Flash GrapheneOS to your device. Bootloader must already be unlocked.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {status === 'completed' && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>✓ Flash completed successfully! Device is rebooting into GrapheneOS.</AlertDescription>
            </Alert>
          )}

          {/* Device Info and Connection Status */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Smartphone className="w-4 h-4" />
                <span className="text-sm font-medium">
                  Device: <strong>{device.deviceName || device.codename || device.serial}</strong>
                  {device.codename && <span className="ml-2">({device.codename})</span>}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {deviceConnected ? (
                  <>
                    <Wifi className="w-4 h-4 text-green-600 dark:text-green-400" />
                    <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                      Device: {device.deviceName || 'Pixel 7'} ({device.codename || 'panther'}) Connected
                    </span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4 text-yellow-600 dark:text-yellow-400 animate-pulse" />
                    <span className="text-xs text-yellow-600 dark:text-yellow-400 font-medium">
                      Device: {device.deviceName || 'Pixel 7'} ({device.codename || 'panther'}) Disconnected
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Download Progress */}
          {downloading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  Downloading GrapheneOS bundle...
                </span>
                <span className="font-medium">{downloadProgress.toFixed(1)}%</span>
              </div>
              <Progress value={downloadProgress} className="h-2" />
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Activity className="w-3 h-3" />
                <span>Download in progress - this may take several minutes</span>
              </div>
            </div>
          )}

          {/* Flash Progress Bar */}
          {processing && !downloading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {currentStep || 'Starting flash process...'}
                </span>
                <span className="font-medium">{progress}%</span>
              </div>
              <Progress value={progress} className="h-2" />
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Activity className="w-3 h-3" />
                <span>Flashing in progress - keep device connected</span>
              </div>
            </div>
          )}

          {processing && !currentStep && !downloading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Initializing flash process...</span>
            </div>
          )}

          {/* Real-time Logs */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold">Process Logs</h4>
              {logs.length > 0 && (
                <span className="text-xs text-muted-foreground">{logs.length} lines</span>
              )}
            </div>
            <div className="bg-muted rounded-lg p-4 font-mono text-xs max-h-96 overflow-y-auto">
              {logs.length === 0 ? (
                <div className="text-muted-foreground italic">Waiting for logs...</div>
              ) : (
                <>
                  {logs.map((log, idx) => {
                    // Parse JSON log if present
                    let logMessage = log;
                    let logLevel = 'info';
                    try {
                      const parsed = JSON.parse(log);
                      if (parsed.message) {
                        logMessage = parsed.message;
                        logLevel = parsed.status || 'info';
                      }
                    } catch {
                      // Not JSON, use as-is
                    }

                    return (
                      <div key={idx} className="mb-1 flex items-start gap-2">
                        <span className="text-muted-foreground shrink-0">[{idx + 1}]</span>
                        <span className={
                          logLevel === 'error' || logMessage.includes('ERROR') || logMessage.includes('error') || logMessage.includes('failed') || logMessage.includes('Failed') 
                            ? 'text-destructive' 
                            : logLevel === 'warning' || logMessage.includes('Warning') || logMessage.includes('warning') || logMessage.includes('⚠')
                            ? 'text-yellow-600 dark:text-yellow-400'
                            : logLevel === 'success' || logMessage.includes('✓') || logMessage.includes('success')
                            ? 'text-green-600 dark:text-green-400'
                            : logMessage.includes('Waiting for device') || logMessage.includes('USB disconnect')
                            ? 'text-blue-600 dark:text-blue-400'
                            : ''
                        }>
                          {logMessage}
                        </span>
                      </div>
                    );
                  })}
                  <div ref={logsEndRef} />
                </>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => handleOpenChange(false)}
              // Always allow closing - user can manually close to see logs later
            >
              {downloading 
                ? 'Downloading... (Flash will continue)' 
                : processing 
                ? 'Close Dialog (Logs preserved)' 
                : 'Close'}
            </Button>
            {!processing && !downloading && status !== 'completed' && status !== 'failed' && (
              <Button onClick={handleFlash}>
                <Zap className="w-4 h-4 mr-2" />
                Start Flash
              </Button>
            )}
            {(status === 'completed' || status === 'failed') && (
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Done
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

