import { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@flashdash/ui';
import { Badge } from '@flashdash/ui';
import { Alert, AlertDescription } from '@flashdash/ui';
import { Smartphone, Info, CheckCircle2 } from 'lucide-react';

const mockDevices = [
  {
    id: '1',
    serial: 'ABC123XYZ',
    state: 'device' as const,
    codename: 'cheetah',
    deviceName: 'Pixel 7 Pro',
  },
  {
    id: '2',
    serial: 'DEF456UVW',
    state: 'fastboot' as const,
    codename: 'panther',
    deviceName: 'Pixel 7',
  },
];

export function Demo() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <motion.div
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="space-y-4"
      >
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            <strong>Demo Mode:</strong> This is a read-only demonstration with mocked data. 
            Flashing is disabled. Use the desktop app for actual device operations.
          </AlertDescription>
        </Alert>

        <div>
          <h1 className="text-4xl font-bold mb-2">Demo Dashboard</h1>
          <p className="text-muted-foreground">Explore the interface with sample data</p>
        </div>
      </motion.div>

      <Card className="backdrop-blur-sm bg-card/80 border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Smartphone className="w-5 h-5" />
            Mock Devices
          </CardTitle>
          <CardDescription>
            Sample devices for demonstration purposes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockDevices.map((device, index) => (
              <motion.div
                key={device.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
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
                      <Badge variant="outline">{device.codename}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{device.deviceName}</p>
                  </div>
                  <Badge variant="outline" className="opacity-50">
                    <CheckCircle2 className="w-3 h-3 mr-1" />
                    Demo
                  </Badge>
                </div>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

