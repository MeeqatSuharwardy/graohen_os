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
import { Loader2, Unlock, AlertCircle, CheckCircle2, Smartphone } from 'lucide-react';
import { apiClient } from '../lib/api';
import { EnableOemUnlockInstructions } from './EnableOemUnlockInstructions';

interface Device {
  id: string;
  serial: string;
  state: 'device' | 'fastboot' | 'unauthorized' | 'offline';
  codename?: string;
  deviceName?: string;
}

interface UnlockAndFlashButtonProps {
  device: Device;
  trigger?: React.ReactNode;
}

export function UnlockAndFlashButton({ device, trigger }: UnlockAndFlashButtonProps) {
  const [open, setOpen] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [showOemInstructions, setShowOemInstructions] = useState(false);

  // Poll for job status and logs if we have a job ID
  useEffect(() => {
    if (!jobId || !processing) return;

    let eventSource: EventSource | null = null;

    // Try SSE streaming first
    try {
      const baseUrl = apiClient.defaults.baseURL || 'http://127.0.0.1:17890';
      const streamUrl = `${baseUrl}/flash/jobs/${jobId}/stream`;
      
      eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.line) {
            setLogs(prev => [...prev, data.line]);
          }
        } catch (err) {
          // Ignore parse errors
        }
      };

      eventSource.addEventListener('log', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.line) {
            setLogs(prev => [...prev, data.line]);
          }
        } catch (err) {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener('status', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.status === 'completed') {
            setProcessing(false);
            setStatus('completed');
            eventSource?.close();
          } else if (data.status === 'failed' || data.status === 'cancelled') {
            setProcessing(false);
            setStatus('failed');
            eventSource?.close();
          }
        } catch (err) {
          // Ignore parse errors
        }
      });

      eventSource.addEventListener('close', () => {
        eventSource?.close();
      });

      eventSource.onerror = () => {
        // Fallback to polling if SSE fails
        eventSource?.close();
        eventSource = null;
      };
    } catch (err) {
      console.warn('SSE not available, using polling');
    }

    // Fallback: Poll for job status and logs
    const pollInterval = setInterval(async () => {
      try {
        console.log('Polling job status for:', jobId);
        const response = await apiClient.get(`/flash/jobs/${jobId}`);
        const job = response.data;

        console.log('Job status:', job.status, 'Log count:', job.logs?.length || 0);

        // Update logs if available
        if (job.logs && Array.isArray(job.logs)) {
          console.log('📋 Updating logs:', job.logs.length, 'lines');
          if (job.logs.length > 0) {
            console.log('📄 Logs content:');
            job.logs.forEach((log: string, idx: number) => {
              if (log.includes('ERROR') || log.includes('error') || log.includes('failed') || log.includes('Failed')) {
                console.error(`  [${idx}] ❌ ${log}`);
              } else if (log.includes('Warning') || log.includes('warning') || log.includes('⚠')) {
                console.warn(`  [${idx}] ⚠️  ${log}`);
              } else {
                console.log(`  [${idx}] ℹ️  ${log}`);
              }
            });
          }
          setLogs(job.logs);
        }

        if (job.status === 'completed') {
          console.log('✅ Job completed successfully');
          setProcessing(false);
          setStatus('completed');
          if (eventSource) eventSource.close();
          clearInterval(pollInterval);
        } else if (job.status === 'failed' || job.status === 'cancelled') {
          console.error('❌ Job failed or cancelled:', job.status);
          console.error('📋 Final logs:', job.logs);
          if (job.logs && job.logs.length > 0) {
            const errorLogs = job.logs.filter((log: string) => 
              log.includes('ERROR') || log.includes('error') || log.includes('failed') || log.includes('Failed')
            );
            if (errorLogs.length > 0) {
              console.error('🚨 Error logs:');
              errorLogs.forEach((log: string) => console.error('  ', log));
              
              // Check if error is about OEM unlocking being disabled
              const oemUnlockError = errorLogs.some((log: string) => 
                log.includes('OEM unlocking is disabled') || 
                log.includes('unlock is not allowed') ||
                log.includes('flashing unlock is not allowed')
              );
              
              if (oemUnlockError) {
                setShowOemInstructions(true);
              }
            }
          }
          setProcessing(false);
          setStatus('failed');
          if (eventSource) eventSource.close();
          clearInterval(pollInterval);
        }
      } catch (err: any) {
        console.error('Error polling job status:', err);
        // Don't stop polling on error, might be temporary
      }
    }, 1000); // Poll every second for better reliability

    return () => {
      if (eventSource) eventSource.close();
      clearInterval(pollInterval);
    };
  }, [jobId, processing]);

  const handleUnlockAndFlash = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    
    // Prevent double-clicks - check processing state FIRST before any async operations
    if (processing) {
      console.log('Already processing, ignoring click');
      return;
    }
    
    console.log('handleUnlockAndFlash called', { device });
    
    if (device.state !== 'fastboot') {
      setError('Device must be in fastboot mode. Please reboot to fastboot mode first.');
      return;
    }

    // Set processing IMMEDIATELY to prevent double-clicks
    setProcessing(true);
    setError(null);
    setLogs(['Starting unlock and flash process...']);
    setStatus('starting');
    setJobId(null);

    try {
      const deviceSerial = device.serial || device.id;
      console.log('Starting unlock and flash for device:', deviceSerial);

      // Call the unlock-and-flash endpoint
      console.log('Calling API endpoint: /flash/unlock-and-flash');
      const response = await apiClient.post('/flash/unlock-and-flash', {
        device_serial: deviceSerial,
        skip_unlock: false, // Always attempt unlock
      });

      console.log('API response:', response.data);
      const result = response.data;
      
      if (result.success && result.job_id) {
        console.log('Job started:', result.job_id);
        const newJobId = result.job_id;
        setJobId(newJobId);
        setLogs(prev => [...prev, 'Unlock and flash process started...', 'Waiting for device confirmation...']);
        setStatus('running');
        
        // Immediately fetch initial logs
        setTimeout(async () => {
          try {
            const logResponse = await apiClient.get(`/flash/jobs/${newJobId}`);
            if (logResponse.data.logs && Array.isArray(logResponse.data.logs)) {
              setLogs(logResponse.data.logs);
            }
          } catch (err) {
            console.error('Error fetching initial logs:', err);
          }
        }, 500);
      } else {
        throw new Error(result.message || 'Failed to start unlock and flash');
      }
    } catch (err: any) {
      console.error('Error in handleUnlockAndFlash:', err);
      const errorDetail = err.response?.data?.detail || err.message || 'Unknown error';
      setError(`Failed to start unlock and flash: ${errorDetail}`);
      setProcessing(false);
      setStatus('failed');
      setLogs(prev => [...prev, `Error: ${errorDetail}`]);
    }
  };


  const handleOpenChange = (newOpen: boolean) => {
    console.log('Dialog open state change:', newOpen, 'processing:', processing);
    if (!processing) {
      setOpen(newOpen);
      if (!newOpen) {
        // Reset state when closing
        setError(null);
        setLogs([]);
        setStatus(null);
        setJobId(null);
      }
    } else if (!newOpen) {
      // Don't allow closing while processing
      console.log('Prevented dialog close while processing');
    }
  };

  // Show button only if device is in fastboot mode
  if (device.state !== 'fastboot') {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {trigger || (
          <Button onClick={() => console.log('Dialog trigger clicked')}>
            <Unlock className="w-4 h-4 mr-2" />
            Unlock & Flash
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Unlock Bootloader & Flash GrapheneOS</DialogTitle>
          <DialogDescription>
            This will unlock the bootloader (requires physical confirmation on device) and flash GrapheneOS.
            <strong className="block mt-2 text-destructive">
              ⚠️ This will factory reset your device and erase all data!
            </strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {device && (
            <Alert>
              <Smartphone className="h-4 w-4" />
              <AlertDescription>
                Device: <strong>{device.deviceName || device.codename || device.serial}</strong>
                {device.codename && <span className="ml-2">({device.codename})</span>}
                <span className="ml-2 text-xs text-muted-foreground">({device.serial})</span>
              </AlertDescription>
            </Alert>
          )}

          {!processing ? (
            <div className="space-y-4">
              <div className="text-center py-6">
                <Unlock className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground mb-4">
                  Ready to unlock bootloader and flash GrapheneOS.
                </p>
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-left space-y-2">
                  <p className="text-sm font-semibold text-destructive">⚠️ Important:</p>
                  <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                    <li>Device must be in fastboot mode (already detected)</li>
                    <li>OEM unlocking must be enabled in Developer options</li>
                    <li>You will need to confirm unlock on your device screen</li>
                    <li>All data will be permanently erased</li>
                    <li>Ensure your device is charged (at least 50%)</li>
                  </ul>
                </div>
              </div>

              <div className="space-y-2">
                <Button
                  onClick={(e) => handleUnlockAndFlash(e)}
                  className="w-full"
                  size="lg"
                  variant="default"
                  disabled={processing}
                >
                  <Unlock className="w-4 h-4 mr-2" />
                  Unlock & Flash Now
                </Button>
                
                <Button
                  onClick={() => setShowOemInstructions(true)}
                  variant="outline"
                  className="w-full"
                  size="sm"
                >
                  <Smartphone className="w-4 h-4 mr-2" />
                  Show Instructions: Enable OEM Unlocking & USB Debugging
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="font-medium">
                    {status === 'starting' && 'Starting process...'}
                    {status === 'running' && 'Unlocking bootloader & flashing...'}
                    {status === 'completed' && 'Completed!'}
                    {status === 'failed' && 'Failed'}
                    {!status && 'Processing...'}
                  </span>
                </div>
              </div>

              {status === 'running' && (
                <Alert className="border-amber-500 bg-amber-50 dark:bg-amber-950">
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                  <AlertDescription className="space-y-2">
                    <div>
                      <strong className="text-amber-900 dark:text-amber-100">
                        ⚠️ ACTION REQUIRED - Check Your Device Screen NOW!
                      </strong>
                    </div>
                    <div className="text-sm space-y-1 mt-2">
                      <p className="font-semibold">You should see an unlock confirmation prompt on your device.</p>
                      <ol className="list-decimal list-inside space-y-1 ml-2">
                        <li>Use <strong>Volume Up/Down</strong> to select <strong>"Yes"</strong></li>
                        <li>Press <strong>Power</strong> to confirm</li>
                      </ol>
                      <p className="mt-2 italic">
                        Waiting for your confirmation... This may take up to 6 minutes.
                      </p>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {logs.length > 0 && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Process Logs</label>
                  <div className="p-4 rounded-lg border bg-muted/50 font-mono text-xs max-h-[300px] overflow-y-auto">
                    {logs.map((log, index) => {
                      // Highlight important messages
                      const isImportant = log.includes('ACTION REQUIRED') || 
                                         log.includes('Check your device') ||
                                         log.includes('waiting') ||
                                         log.includes('unlocked successfully');
                      return (
                        <div 
                          key={index} 
                          className={`mb-1 ${isImportant ? 'font-semibold text-amber-600 dark:text-amber-400' : ''}`}
                        >
                          {log}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {status === 'completed' && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertDescription>
                    Unlock and flash completed successfully! Your device should now be rebooting into GrapheneOS.
                  </AlertDescription>
                </Alert>
              )}

              {status === 'failed' && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="space-y-2">
                      <p>Unlock and flash failed. Check the logs above for details.</p>
                      {logs.some(log => 
                        log.includes('OEM unlocking is disabled') || 
                        log.includes('unlock is not allowed') ||
                        log.includes('flashing unlock is not allowed')
                      ) && (
                        <div className="pt-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setShowOemInstructions(true)}
                            className="w-full"
                          >
                            <Smartphone className="w-4 h-4 mr-2" />
                            Show Instructions to Enable OEM Unlocking
                          </Button>
                        </div>
                      )}
                    </div>
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </div>
        
        <EnableOemUnlockInstructions
          open={showOemInstructions}
          onOpenChange={setShowOemInstructions}
          deviceSerial={device.serial || device.id}
          onComplete={() => {
            setShowOemInstructions(false);
            // Optionally refresh device status
            if (window.location) {
              window.location.reload();
            }
          }}
        />
      </DialogContent>
    </Dialog>
  );
}

