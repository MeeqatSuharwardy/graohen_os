import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@flashdash/ui';
import { Button } from '@flashdash/ui';
import { Badge } from '@flashdash/ui';
import { Alert, AlertDescription, AlertTitle } from '@flashdash/ui';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@flashdash/ui';
import { Activity, Smartphone, AlertTriangle, Download, Monitor, Globe } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../lib/api';

const isDemoMode = import.meta.env.VITE_WEB_DEMO_MODE === 'true';

interface Device {
  id: string;
  serial: string;
  state: 'device' | 'fastboot' | 'unauthorized' | 'offline';
  codename?: string;
  deviceName?: string;
}

function detectOS(): 'windows' | 'mac' | 'linux' | 'unknown' {
  const userAgent = navigator.userAgent.toLowerCase();
  if (userAgent.includes('win')) return 'windows';
  if (userAgent.includes('mac')) return 'mac';
  if (userAgent.includes('linux')) return 'linux';
  return 'unknown';
}

const getDownloadBaseUrl = () => {
  return import.meta.env.VITE_DOWNLOAD_BASE_URL || 'https://os.fxmail.ai/download';
};

function getDownloadUrl(os: string): string {
  const baseUrl = getDownloadBaseUrl();
  const winUrl = import.meta.env.VITE_DESKTOP_DOWNLOAD_WIN || `${baseUrl}/@flashdashdesktop%20Setup%201.0.0.exe`;
  const macUrl = import.meta.env.VITE_DESKTOP_DOWNLOAD_MAC || `${baseUrl}/FlashDash-1.0.0.dmg`;
  const linuxUrl = import.meta.env.VITE_DESKTOP_DOWNLOAD_LINUX || `${baseUrl}/flashdash-1.0.0.AppImage`;

  switch (os) {
    case 'windows':
      return winUrl;
    case 'mac':
      return macUrl;
    case 'linux':
      return linuxUrl;
    default:
      return '#';
  }
}

export function Dashboard() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (isDemoMode) {
      navigate('/demo');
      return;
    }

    checkBackend();
    refreshDevices();
    const interval = setInterval(refreshDevices, 3000);
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    try {
      await apiClient.get('/health');
      setError(null);
    } catch {
      setError('Backend service unreachable');
      setShowDownloadModal(true);
    }
  };

  const refreshDevices = async () => {
    if (isDemoMode) return;
    
    try {
      const response = await apiClient.get('/devices');
      setDevices(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch devices');
      if (err.code === 'ECONNREFUSED') {
        setShowDownloadModal(true);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDesktop = () => {
    const protocol = import.meta.env.VITE_DESKTOP_PROTOCOL || 'flashdash://open';
    window.location.href = protocol;
  };

  if (isDemoMode) {
    return null; // Will redirect
  }

  return (
    <div className="container mx-auto p-4 sm:p-6 space-y-4 sm:space-y-6">
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4 sm:mb-6"
      >
        <div className="flex-1">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-2">Flash Dashboard</h1>
          <p className="text-sm sm:text-base text-muted-foreground">Web dashboard (read-only). Use desktop app or browser for flashing.</p>
        </div>
        <Button
          size="lg"
          className="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
          onClick={() => {
            const webFlasherUrl = import.meta.env.VITE_WEB_FLASHER_URL || 
              (import.meta.env.PROD 
                ? `${window.location.origin}/flash` 
                : 'http://localhost:5175');
            window.open(webFlasherUrl, '_blank');
          }}
        >
          <Globe className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
          <span className="text-sm sm:text-base">Flash Online (Browser)</span>
        </Button>
      </motion.div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="backdrop-blur-sm bg-card/80 border-border/50">
        <CardHeader className="p-4 sm:p-6">
          <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <Smartphone className="w-4 h-4 sm:w-5 sm:h-5" />
            Connected Devices
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            {devices.length === 0
              ? 'No devices detected. Connect a Pixel device via USB and enable USB debugging.'
              : `${devices.length} device(s) detected`}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-4 sm:p-6 pt-0">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Activity className="w-5 h-5 sm:w-6 sm:h-6 animate-spin text-muted-foreground" />
            </div>
          ) : devices.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Smartphone className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm sm:text-base">No devices found</p>
            </div>
          ) : (
            <div className="space-y-3 sm:space-y-4">
              {devices.map((device) => (
                <motion.div
                  key={device.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ scale: 1.01 }}
                  className="p-3 sm:p-4 rounded-lg border bg-card/50 backdrop-blur-sm"
                >
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="font-semibold text-sm sm:text-base truncate">{device.serial}</span>
                        <Badge variant={device.state === 'device' ? 'default' : 'secondary'} className="text-xs">
                          {device.state}
                        </Badge>
                        {device.codename && (
                          <Badge variant="outline" className="text-xs">{device.codename}</Badge>
                        )}
                      </div>
                      {device.deviceName && (
                        <p className="text-xs sm:text-sm text-muted-foreground truncate">{device.deviceName}</p>
                      )}
                    </div>
                    <Badge variant="outline" className="opacity-50 text-xs whitespace-nowrap">
                      Read-only
                    </Badge>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showDownloadModal} onOpenChange={setShowDownloadModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Backend Service Unavailable</DialogTitle>
            <DialogDescription>
              The Python backend service is not running. Please use the desktop app for full functionality.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col sm:flex-row gap-2 mt-4">
            <Button onClick={handleOpenDesktop} variant="outline" className="w-full sm:w-auto">
              <Monitor className="w-4 h-4 mr-2" />
              <span className="text-sm sm:text-base">Open Desktop App</span>
            </Button>
            <Button onClick={() => window.open(getDownloadUrl(detectOS()), '_blank')} className="w-full sm:w-auto">
              <Download className="w-4 h-4 mr-2" />
              <span className="text-sm sm:text-base">Download Desktop App</span>
            </Button>
            <Button onClick={() => navigate('/demo')} variant="ghost" className="w-full sm:w-auto">
              <span className="text-sm sm:text-base">View Demo</span>
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

