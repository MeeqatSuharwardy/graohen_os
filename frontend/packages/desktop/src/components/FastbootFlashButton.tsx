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
import { Loader2, Zap, AlertCircle, CheckCircle2, Smartphone } from 'lucide-react';
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
          if (data.log) {
            setLogs(prev => [...prev, data.log]);
          }
          if (data.status) {
            setStatus(data.status);
            if (data.status === 'completed' || data.status === 'failed') {
              setProcessing(false);
              if (eventSource) eventSource.close();
            }
          }
        } catch (e) {
          console.error('Error parsing SSE data:', e);
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
          setProcessing(false);
          setStatus('completed');
          if (eventSource) eventSource.close();
          clearInterval(pollInterval);
        } else if (job.status === 'failed' || job.status === 'cancelled') {
          setProcessing(false);
          setStatus('failed');
          if (job.logs && job.logs.length > 0) {
            const errorLogs = job.logs.filter((log: string) => 
              log.includes('ERROR') || log.includes('error') || log.includes('failed') || log.includes('Failed')
            );
            if (errorLogs.length > 0) {
              setError(errorLogs[errorLogs.length - 1]);
            }
          }
          if (eventSource) eventSource.close();
          clearInterval(pollInterval);
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

  const handleFlash = async (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    
    if (processing) {
      console.log('Already processing, ignoring click');
      return;
    }
    
    if (device.state !== 'fastboot') {
      setError('Device must be in fastboot mode. Please reboot to fastboot mode first.');
      return;
    }

    setProcessing(true);
    setError(null);
    setLogs(['Starting flash process (bootloader already unlocked)...']);
    setStatus('starting');
    setJobId(null);

    try {
      const deviceSerial = device.serial || device.id;
      console.log('Starting flash for device:', deviceSerial);
      setLogs(prev => [...prev, 'Calling flash endpoint...']);

      // Call the unlock-and-flash endpoint with skip_unlock=true
      // Use longer timeout for this endpoint since bundle detection may take time
      const response = await apiClient.post('/flash/unlock-and-flash', {
        device_serial: deviceSerial,
        skip_unlock: true, // Skip unlock since device is already unlocked
      }, {
        timeout: 120000, // 120 seconds timeout (bundle detection can be slow)
      });

      console.log('API response:', response.data);
      const result = response.data;
      
      if (result.success && result.job_id) {
        console.log('Job started:', result.job_id);
        setJobId(result.job_id);
        setLogs(prev => [...prev, 'Flash process started...']);
        setStatus('running');
      } else {
        throw new Error(result.message || 'Failed to start flash');
      }
    } catch (err: any) {
      console.error('Error in handleFlash:', err);
      
      let errorDetail = err.message || 'Unknown error';
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorDetail = 'Request timed out. The backend may be busy or bundle detection is taking too long. Please try again.';
      } else if (err.response?.data?.detail) {
        errorDetail = err.response.data.detail;
      } else if (err.response?.data?.message) {
        errorDetail = err.response.data.message;
      }
      
      setError(`Failed to start flash: ${errorDetail}`);
      setProcessing(false);
      setStatus('failed');
      setLogs(prev => [...prev, `Error: ${errorDetail}`]);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!processing) {
      setOpen(newOpen);
      if (!newOpen) {
        // Reset state when dialog closes
        setError(null);
        setLogs([]);
        setStatus(null);
        setJobId(null);
      }
    }
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
              <AlertDescription>Flash completed successfully!</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Smartphone className="w-4 h-4" />
              <span className="text-sm font-medium">
                Device: <strong>{device.deviceName || device.codename || device.serial}</strong>
                {device.codename && <span className="ml-2">({device.codename})</span>}
              </span>
            </div>
          </div>

          {processing && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Flashing device...</span>
            </div>
          )}

          {logs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-semibold">Process Logs</h4>
              <div className="bg-muted rounded-lg p-4 font-mono text-xs max-h-96 overflow-y-auto">
                {logs.map((log, idx) => (
                  <div key={idx} className="mb-1">
                    {log.includes('ERROR') || log.includes('error') || log.includes('failed') || log.includes('Failed') ? (
                      <span className="text-destructive">{log}</span>
                    ) : log.includes('Warning') || log.includes('warning') || log.includes('⚠') ? (
                      <span className="text-yellow-600 dark:text-yellow-400">{log}</span>
                    ) : log.includes('✓') || log.includes('success') ? (
                      <span className="text-green-600 dark:text-green-400">{log}</span>
                    ) : (
                      <span>{log}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={processing}
            >
              {processing ? 'Flashing...' : 'Close'}
            </Button>
            {!processing && (
              <Button onClick={handleFlash}>
                <Zap className="w-4 h-4 mr-2" />
                Start Flash
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

