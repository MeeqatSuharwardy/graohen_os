# Flash Troubleshooting Guide

## Problem: Flash Not Starting

If the flash process isn't starting, follow these debugging steps:

## Step 1: Check Browser Console

Open DevTools (F12) and check the Console tab for errors. Look for:

- `[Flash]` prefixed logs showing the request/response
- `[SSE]` logs showing stream connection status
- `[Log]` logs showing all log messages
- Any red error messages

## Step 2: Verify Request is Sent

Look for these console logs:
```
[Flash] Calling endpoint: https://freedomos.vulcantech.co/flash/device-flash
[Flash] Request body: {...}
[Flash] Response status: 200 OK
[Flash] Success response: {success: true, job_id: "..."}
[Flash] Job ID: <job-id>
```

If you see an error response instead, check the error message.

## Step 3: Check Backend Response

### Common Errors:

**404 - Bundle Not Found**
```
Error: No bundle found for device codename: panther
```
**Solution**: Index bundles on backend:
```bash
curl -X POST https://freedomos.vulcantech.co/bundles/index
```

**500 - Internal Server Error**
```
Error: Failed to start unlock and flash: ...
```
**Solution**: Check backend logs for details. Common causes:
- Bundle path doesn't exist
- flasher.py script not found
- Permission issues

**400 - Bad Request**
```
Error: Could not identify device codename...
```
**Solution**: Ensure device is in fastboot mode and backend can detect it.

## Step 4: Verify Job Was Created

After clicking "Start Flashing", check if you see:
```
Job ID: <uuid>
Job verified. Status: starting
Connecting to log stream...
```

If job verification fails, the backend might not have created the job.

## Step 5: Check SSE Stream Connection

Look for:
```
[SSE] Connecting to: https://freedomos.vulcantech.co/flash/jobs/<job-id>/stream
[SSE] Stream connected successfully
Log stream connected. Waiting for flash to start...
```

If stream doesn't connect:
- Check CORS settings on backend
- Verify backend is running
- Check network tab for failed requests

## Step 6: Check Backend Logs

On the server, check backend logs:
```bash
# If using Docker
docker logs flashdash

# Or check application logs
tail -f /path/to/backend/logs/app.log
```

Look for:
- Job creation logs
- Flash process startup
- Any errors or exceptions

## Step 7: Verify Bundle Exists

Check if bundle is available:
```bash
# Check if bundle is indexed
curl https://freedomos.vulcantech.co/bundles/for/panther

# Should return bundle info with path
```

If bundle not found:
1. Ensure bundle exists at `/root/graohen_os/bundles/panther/2026011300/`
2. Index bundles: `POST /bundles/index`
3. Verify bundle has `image.zip` file

## Step 8: Check Device State

Ensure device is in fastboot mode:
```bash
fastboot devices
# Should show your device
```

If device not in fastboot:
- Click "Reboot to Bootloader" in the app
- Or manually: `adb reboot bootloader`

## Common Issues and Fixes

### Issue 1: "No bundle found"
**Symptoms**: 404 error when starting flash
**Fix**: 
1. Index bundles: `POST /bundles/index`
2. Verify bundle path exists on server
3. Check bundle has `image.zip` file

### Issue 2: "Job created but no logs"
**Symptoms**: Job ID received but SSE stream shows no activity
**Fix**:
1. Check backend logs for flash process errors
2. Verify `flasher.py` script exists and is executable
3. Check if flash process actually started (check processes)

### Issue 3: "SSE stream won't connect"
**Symptoms**: "Connecting to log stream..." but never connects
**Fix**:
1. Check CORS configuration on backend
2. Verify backend URL is correct
3. Check browser console for CORS errors
4. Try polling instead: Check job status manually

### Issue 4: "Flash starts but immediately fails"
**Symptoms**: Job starts but status becomes "failed" quickly
**Fix**:
1. Check backend logs for error details
2. Verify device is in fastboot mode
3. Check fastboot/adb paths in backend config
4. Verify bundle files are complete

## Manual Testing

### Test 1: Check Bundle Endpoint
```bash
curl https://freedomos.vulcantech.co/bundles/for/panther
```

### Test 2: Test Flash Endpoint Directly
```bash
curl -X POST https://freedomos.vulcantech.co/flash/device-flash \
  -H "Content-Type: application/json" \
  -d '{
    "serial": "YOUR_DEVICE_SERIAL",
    "codename": "panther",
    "state": "fastboot",
    "bootloader_unlocked": false
  }'
```

### Test 3: Check Job Status
```bash
curl https://freedomos.vulcantech.co/flash/jobs/<job-id>
```

### Test 4: Test SSE Stream
```bash
curl -N https://freedomos.vulcantech.co/flash/jobs/<job-id>/stream
```

## Debug Mode

Enable detailed logging in the Electron app:
1. Open DevTools (F12)
2. Check "Preserve log" in Console
3. Watch for all `[Flash]`, `[SSE]`, and `[Log]` messages
4. Check Network tab for failed requests

## Still Not Working?

If none of the above helps:

1. **Check Backend Health**:
   ```bash
   curl https://freedomos.vulcantech.co/docs
   ```

2. **Verify Backend Can Access Device**:
   ```bash
   # On server
   fastboot devices
   adb devices
   ```

3. **Check Bundle Structure**:
   ```bash
   # On server
   ls -la /root/graohen_os/bundles/panther/2026011300/
   # Should show: image.zip, flash-all.sh, etc.
   ```

4. **Test flasher.py Manually**:
   ```bash
   # On server
   python backend/flasher.py \
     --bundle-path /root/graohen_os/bundles/panther/2026011300 \
     --device-serial YOUR_SERIAL \
     --confirm
   ```

---

**Last Updated**: 2026-01-23
