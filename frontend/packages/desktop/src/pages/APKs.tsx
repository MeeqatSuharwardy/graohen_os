import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@flashdash/ui';
import { Button } from '@flashdash/ui';
import { Badge } from '@flashdash/ui';
import { Alert, AlertDescription, AlertTitle } from '@flashdash/ui';
import { Activity, Smartphone, AlertTriangle, CheckCircle2, Package, Download } from 'lucide-react';
import { apiClient } from '../lib/api';

interface APK {
  filename: string;
  size: number;
  upload_time: string;
}

interface Device {
  id: string;
  serial: string;
  state: 'device' | 'fastboot' | 'unauthorized' | 'offline';
  codename?: string;
  device_name?: string;
}

export function APKs() {
  const [apks, setApks] = useState<APK[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadAPKs();
    loadDevices();
    const interval = setInterval(() => {
      loadAPKs();
      loadDevices();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadAPKs = async () => {
    try {
      const response = await apiClient.get('/apks/list');
      setApks(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load APKs');
    } finally {
      setLoading(false);
    }
  };

  const loadDevices = async () => {
    try {
      const response = await apiClient.get('/devices');
      setDevices(response.data.filter((d: Device) => d.state === 'device'));
    } catch (err: any) {
      // Ignore device loading errors
    }
  };

  const handleInstall = async (apkFilename: string, deviceSerial: string) => {
    setInstalling((prev) => ({ ...prev, [apkFilename]: true }));
    setError(null);
    setSuccess(null);

    try {
      await apiClient.post('/apks/install', {
        device_serial: deviceSerial,
        apk_filename: apkFilename,
      });

      setSuccess(`APK ${apkFilename} installed successfully on ${deviceSerial}`);
      setTimeout(() => setSuccess(null), 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || `Failed to install ${apkFilename}`);
      setTimeout(() => setError(null), 5000);
    } finally {
      setInstalling((prev) => ({ ...prev, [apkFilename]: false }));
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-4xl font-bold mb-2">APK Installer</h1>
          <p className="text-muted-foreground">Install APKs on connected Android devices</p>
        </div>
      </motion.div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="bg-green-50 border-green-200 text-green-800">
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      <Card className="backdrop-blur-sm bg-card/80 border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="w-5 h-5" />
            Available APKs
          </CardTitle>
          <CardDescription>
            APKs uploaded via the backend upload form. Click install to install on a connected device.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Activity className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : apks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No APKs available.</p>
              <p className="text-sm mt-2">Upload APKs via the backend form at /apks/upload</p>
            </div>
          ) : (
            <div className="space-y-4">
              {apks.map((apk) => (
                <motion.div
                  key={apk.filename}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 rounded-lg border bg-card/50 backdrop-blur-sm"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold">{apk.filename}</span>
                        <Badge variant="outline">{formatFileSize(apk.size)}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Uploaded: {formatDate(apk.upload_time)}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      {devices.length > 0 ? (
                        devices.map((device) => (
                          <Button
                            key={device.serial}
                            size="sm"
                            onClick={() => handleInstall(apk.filename, device.serial)}
                            disabled={installing[apk.filename]}
                          >
                            {installing[apk.filename] ? (
                              <>
                                <Activity className="w-4 h-4 mr-2 animate-spin" />
                                Installing...
                              </>
                            ) : (
                              <>
                                <Download className="w-4 h-4 mr-2" />
                                Install on {device.serial.slice(0, 8)}...
                              </>
                            )}
                          </Button>
                        ))
                      ) : (
                        <Button size="sm" disabled>
                          <Smartphone className="w-4 h-4 mr-2" />
                          No devices connected
                        </Button>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="backdrop-blur-sm bg-card/80 border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smartphone className="w-5 h-5" />
            Connected Devices (ADB Mode)
          </CardTitle>
          <CardDescription>
            Devices must be in ADB mode (not fastboot) to install APKs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {devices.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Smartphone className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No devices in ADB mode detected.</p>
              <p className="text-sm mt-2">Connect a device via USB and enable USB debugging.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {devices.map((device) => (
                <div key={device.serial} className="p-3 rounded-lg border bg-card/50">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold">{device.serial}</span>
                      {device.codename && (
                        <Badge variant="outline" className="ml-2">{device.codename}</Badge>
                      )}
                      {device.device_name && (
                        <p className="text-sm text-muted-foreground">{device.device_name}</p>
                      )}
                    </div>
                    <Badge variant="default">ADB Mode</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

