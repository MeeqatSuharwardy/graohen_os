import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@flashdash/ui';
import { Button } from '@flashdash/ui';
import { Badge } from '@flashdash/ui';
import { Alert, AlertDescription, AlertTitle } from '@flashdash/ui';
import { Activity, Smartphone, Download, AlertTriangle, CheckCircle2, Zap, Unlock, Power } from 'lucide-react';
import { apiClient } from '../lib/api';
import { DownloadDialog } from '../components/DownloadDialog';
import { FlashDialog } from '../components/FlashDialog';
import { UnlockAndFlashButton } from '../components/UnlockAndFlashButton';

interface Device {
  id: string;
  serial: string;
  state: 'device' | 'fastboot' | 'unauthorized' | 'offline';
  codename?: string;
  deviceName?: string;
}

export function Dashboard() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [serviceStatus, setServiceStatus] = useState<{ running: boolean } | null>(null);

  useEffect(() => {
    checkServiceStatus();
    refreshDevices();
    const interval = setInterval(refreshDevices, 3000);
    return () => clearInterval(interval);
  }, []);

  const checkServiceStatus = async () => {
    // Check directly via API - backend should be running separately
    try {
      await apiClient.get('/health');
      setServiceStatus({ running: true });
    } catch {
      setServiceStatus({ running: false });
    }
  };

  const refreshDevices = async () => {
    try {
      const response = await apiClient.get('/devices');
      setDevices(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch devices');
    } finally {
      setLoading(false);
    }
  };

  const handleIdentify = async (deviceId: string) => {
    try {
      const response = await apiClient.get(`/devices/${deviceId}/identify`);
      refreshDevices();
    } catch (err: any) {
      setError(err.message || 'Failed to identify device');
    }
  };

  const handleRebootToBootloader = async (deviceId: string) => {
    try {
      await apiClient.post(`/devices/${deviceId}/reboot/bootloader`);
      setError(null);
      // Refresh devices after a delay to see the state change
      setTimeout(() => {
        refreshDevices();
      }, 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to reboot to bootloader');
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-4xl font-bold mb-2">Flash Dashboard</h1>
          <p className="text-muted-foreground">Detect and flash GrapheneOS to Pixel devices</p>
        </div>
        {serviceStatus && (
          <Badge variant={serviceStatus.running ? 'default' : 'destructive'}>
            {serviceStatus.running ? (
              <>
                <CheckCircle2 className="w-3 h-3 mr-1" />
                Service Running
              </>
            ) : (
              <>
                <AlertTriangle className="w-3 h-3 mr-1" />
                Service Offline
              </>
            )}
          </Badge>
        )}
      </motion.div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card className="backdrop-blur-sm bg-card/80 border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Flash GrapheneOS
          </CardTitle>
          <CardDescription>
            Enter purchase number to automatically flash using local build
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FlashDialog
            trigger={
              <Button className="w-full">
                <Zap className="w-4 h-4 mr-2" />
                Flash Device
              </Button>
            }
          />
        </CardContent>
      </Card>

      <Card className="backdrop-blur-sm bg-card/80 border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smartphone className="w-5 h-5" />
            Connected Devices
          </CardTitle>
          <CardDescription>
            {devices.length === 0
              ? 'No devices detected. Connect a Pixel device via USB and enable USB debugging.'
              : `${devices.length} device(s) detected`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Activity className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : devices.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Smartphone className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No devices found</p>
            </div>
          ) : (
            <div className="space-y-4">
              {devices.map((device) => (
                <motion.div
                  key={device.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  whileHover={{ scale: 1.02 }}
                  className="p-4 rounded-lg border bg-card/50 backdrop-blur-sm"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold">{device.serial}</span>
                        <Badge variant={device.state === 'device' ? 'default' : 'secondary'}>
                          {device.state}
                        </Badge>
                        {device.codename && (
                          <Badge variant="outline">{device.codename}</Badge>
                        )}
                      </div>
                      {device.deviceName && (
                        <p className="text-sm text-muted-foreground">{device.deviceName}</p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {!device.codename && device.state === 'device' && (
                        <Button
                          size="sm"
                          onClick={() => handleIdentify(device.id)}
                        >
                          Identify
                        </Button>
                      )}
                      {device.codename && (
                        <>
                          {device.state === 'fastboot' ? (
                            <UnlockAndFlashButton
                              device={device}
                              trigger={
                                <Button size="sm" className="bg-primary">
                                  <Unlock className="w-4 h-4 mr-2" />
                                  Unlock & Flash
                                </Button>
                              }
                            />
                          ) : (
                            <>
                              {device.state === 'device' && (
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  onClick={() => handleRebootToBootloader(device.id)}
                                >
                                  <Power className="w-4 h-4 mr-2" />
                                  Reboot to Fastboot
                                </Button>
                              )}
                              <DownloadDialog
                                codename={device.codename}
                                deviceName={device.deviceName}
                                trigger={
                                  <Button size="sm" variant="outline">
                                    <Download className="w-4 h-4 mr-2" />
                                    Download Build
                                  </Button>
                                }
                              />
                              <FlashDialog
                                device={device}
                                trigger={
                                  <Button size="sm">
                                    <Zap className="w-4 h-4 mr-2" />
                                    Flash
                                  </Button>
                                }
                              />
                            </>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

