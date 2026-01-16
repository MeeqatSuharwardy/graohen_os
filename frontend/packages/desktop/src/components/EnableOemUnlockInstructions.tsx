import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@flashdash/ui';
import { Button } from '@flashdash/ui';
import { Alert, AlertDescription } from '@flashdash/ui';
import { CheckCircle2, Circle, AlertCircle, Smartphone, ChevronRight, Power } from 'lucide-react';
import { apiClient } from '../lib/api';
import { useState } from 'react';

interface EnableOemUnlockInstructionsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
  deviceSerial?: string;
}

export function EnableOemUnlockInstructions({ 
  open, 
  onOpenChange,
  onComplete,
  deviceSerial
}: EnableOemUnlockInstructionsProps) {
  const [rebooting, setRebooting] = useState(false);
  
  const handleRebootToFastboot = async () => {
    if (!deviceSerial) {
      alert('Device serial not available');
      return;
    }
    
    setRebooting(true);
    try {
      await apiClient.post(`/devices/${deviceSerial}/reboot/bootloader`);
      alert('Reboot command sent! Your device should restart to fastboot mode.');
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    } catch (err: any) {
      alert(`Failed to reboot device: ${err.response?.data?.detail || err.message}`);
      setRebooting(false);
    }
  };
  const steps = [
    {
      id: 1,
      title: "Exit Fastboot Mode",
      description: "Reboot your device normally to exit fastboot mode",
      instructions: [
        "On your device screen, use Volume keys to select 'Start' or 'Reboot'",
        "Press Power button to confirm",
        "Wait for device to boot into Android"
      ]
    },
    {
      id: 2,
      title: "Enable Developer Options",
      description: "Unlock developer options on your device",
      instructions: [
        "Open Settings app",
        "Scroll down and tap 'About phone'",
        "Tap 'Build number' 7 times",
        "You'll see a message saying 'You are now a developer!'"
      ]
    },
    {
      id: 3,
      title: "Enable USB Debugging",
      description: "Allow your computer to communicate with your device",
      instructions: [
        "Go back to Settings",
        "Tap 'Developer options' (usually near the bottom)",
        "Enable 'USB debugging'",
        "Tap 'OK' on the warning prompt"
      ]
    },
    {
      id: 4,
      title: "Enable OEM Unlocking",
      description: "Allow bootloader to be unlocked",
      instructions: [
        "Still in Developer options",
        "Enable 'OEM unlocking' (may show as 'Enable OEM unlock')",
        "If prompted, tap 'Enable' to confirm",
        "⚠️ If this option is grayed out, your device may be carrier-locked"
      ]
    },
    {
      id: 5,
      title: "Reboot to Fastboot",
      description: "Return to fastboot mode to unlock and flash",
      instructions: [
        "Keep your device connected via USB",
        deviceSerial ? "Click the 'Reboot to Fastboot' button below" : "Use the 'Reboot to Fastboot' button in the dashboard",
        "OR manually: Power off, then hold Power + Volume Down",
        "Device will show 'Fastboot mode' screen"
      ]
    }
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-amber-500" />
            Enable OEM Unlocking & USB Debugging
          </DialogTitle>
          <DialogDescription>
            Follow these steps to enable OEM unlocking on your device. This is required before you can unlock the bootloader.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          <Alert className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
            <Smartphone className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-blue-900 dark:text-blue-100">
              <strong>Why is this needed?</strong>
              <br />
              OEM unlocking must be enabled in Android settings before the bootloader can be unlocked. 
              This is a security feature that prevents accidental data loss.
            </AlertDescription>
          </Alert>

          <div className="space-y-6">
            {steps.map((step, index) => (
              <div key={step.id} className="space-y-2">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-1">
                    <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                      {step.id}
                    </div>
                  </div>
                  <div className="flex-1 space-y-2">
                    <div>
                      <h3 className="font-semibold text-lg">{step.title}</h3>
                      <p className="text-sm text-muted-foreground">{step.description}</p>
                    </div>
                    <ol className="space-y-2 ml-2">
                      {step.instructions.map((instruction, instIndex) => (
                        <li key={instIndex} className="flex items-start gap-2 text-sm">
                          <ChevronRight className="w-4 h-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                          <span className={instruction.includes('⚠️') ? 'text-amber-600 dark:text-amber-400 font-medium' : ''}>
                            {instruction}
                          </span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
                {index < steps.length - 1 && (
                  <div className="ml-4 border-l-2 border-muted h-4"></div>
                )}
              </div>
            ))}
          </div>

          <Alert className="bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <AlertDescription className="text-amber-900 dark:text-amber-100">
              <strong>Important Notes:</strong>
              <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                <li>Keep your device connected via USB during this process</li>
                <li>If "OEM unlocking" is grayed out, your device may be carrier-locked</li>
                <li>Some carrier-locked devices cannot be unlocked</li>
                <li>After enabling, you'll need to reboot to fastboot mode</li>
              </ul>
            </AlertDescription>
          </Alert>

          {deviceSerial && (
            <Alert className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
              <Power className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-900 dark:text-blue-100">
                <div className="flex items-center justify-between">
                  <div>
                    <strong>Reboot to Fastboot</strong>
                    <p className="text-sm mt-1">After completing steps 1-4, click here to reboot your device to fastboot mode</p>
                  </div>
                  <Button
                    onClick={handleRebootToFastboot}
                    disabled={rebooting}
                    variant="outline"
                    className="ml-4"
                  >
                    {rebooting ? (
                      <>Rebooting...</>
                    ) : (
                      <>
                        <Power className="w-4 h-4 mr-2" />
                        Reboot to Fastboot
                      </>
                    )}
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}

          <div className="flex gap-2 pt-4">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="flex-1"
            >
              Close
            </Button>
            <Button
              onClick={() => {
                onOpenChange(false);
                onComplete?.();
              }}
              className="flex-1"
            >
              I've Completed These Steps
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

