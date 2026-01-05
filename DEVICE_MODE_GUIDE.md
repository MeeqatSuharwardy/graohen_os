# Device Mode Guide for Flashing GrapheneOS

## Required Mode: Fastboot (Bootloader)

For flashing GrapheneOS, your Pixel device **must be in Fastboot mode** (also called Bootloader mode).

## Automatic Mode Detection & Reboot

The app will automatically:
1. **Detect** if your device is in ADB mode
2. **Reboot** it to Fastboot mode automatically
3. **Wait** for the device to enter Fastboot mode
4. **Start** the flashing process

## Manual Method (If Automatic Fails)

If the automatic reboot doesn't work, you can manually put your device in Fastboot mode:

### Method 1: Using ADB (Device is ON and connected)
```bash
adb reboot bootloader
```

### Method 2: Hardware Buttons (Device is OFF)
1. **Turn off** your Pixel device completely
2. **Hold** the **Power button** + **Volume Down** button simultaneously
3. Keep holding until you see the **Fastboot/Bootloader** screen (usually shows an Android robot with "Start" text)
4. Release the buttons

### Method 3: Hardware Buttons (Device is ON)
1. **Press and hold** **Power button** until the power menu appears
2. **Long press** on "Power off" or "Restart"
3. When the device starts rebooting, **immediately hold** **Volume Down** button
4. Keep holding until you see the Fastboot screen

## Verifying Fastboot Mode

You can verify your device is in Fastboot mode by:

1. **Visual Check**: The screen should show:
   - Android robot icon
   - "FASTBOOT MODE" or "BOOTLOADER" text
   - Menu options (Start, Restart bootloader, Recovery mode, etc.)

2. **Command Check**:
   ```bash
   fastboot devices
   ```
   Should show your device serial number.

3. **In the App**: The device should appear with state "fastboot" in the Connected Devices list.

## Device States

- **`device`**: Device is in ADB mode (normal Android mode with USB debugging)
- **`fastboot`**: Device is in Fastboot/Bootloader mode (required for flashing)
- **`unauthorized`**: Device needs USB debugging authorization
- **`offline`**: Device is not responding

## Troubleshooting

### Device Not Detected
- Ensure USB debugging is enabled (Settings > Developer options > USB debugging)
- Try a different USB cable
- Try a different USB port
- On Windows: Install proper USB drivers

### Can't Enter Fastboot Mode
- Make sure the device is completely off before using hardware buttons
- Try the ADB method: `adb reboot bootloader`
- Some devices require holding buttons for 10-15 seconds

### Stuck in Fastboot Mode
- Use the volume buttons to navigate to "Start" or "Restart bootloader"
- Press Power button to select
- Or use: `fastboot reboot`

## After Flashing

Once flashing completes:
- The device will automatically reboot
- First boot may take 5-10 minutes (optimizing apps)
- You'll see the GrapheneOS setup screen

