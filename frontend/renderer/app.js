/**
 * FlashDash Client - Renderer Process
 * 
 * This script runs in the renderer process (browser context).
 * It has NO access to Node.js APIs or shell execution.
 * All device detection is done via IPC to the main process.
 * All flashing is done via HTTPS calls to the backend API.
 */

const BACKEND_URL = 'https://freedomos.vulcantech.co';

// State
let detectedDevices = [];
let selectedDevice = null;
let currentJobId = null;
let eventSource = null;
let availableVersions = [];

// DOM Elements
const detectBtn = document.getElementById('detect-btn');
const refreshBtn = document.getElementById('refresh-btn');
const deviceStatus = document.getElementById('device-status');
const devicesList = document.getElementById('devices-list');
const flashSection = document.getElementById('flash-section');
const selectedDeviceInfo = document.getElementById('selected-device-info');
const versionSelect = document.getElementById('version-select');
const flashBtn = document.getElementById('flash-btn');
const unlockFlashBtn = document.getElementById('unlock-flash-btn');
const warningBox = document.getElementById('warning-box');
const warningText = document.getElementById('warning-text');
const jobSection = document.getElementById('job-section');
const jobIdSpan = document.getElementById('job-id');
const jobStatus = document.getElementById('job-status');
const logOutput = document.getElementById('log-output');
const closeJobBtn = document.getElementById('close-job-btn');
const bundleSection = document.getElementById('bundle-section');
const bundleVersionSelect = document.getElementById('bundle-version-select');
const downloadBundleBtn = document.getElementById('download-bundle-btn');
const downloadProgress = document.getElementById('download-progress');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const downloadBundleFirstCheckbox = document.getElementById('download-bundle-first');
const downloadStatus = document.getElementById('download-status');
const localBundlesInfo = document.getElementById('local-bundles-info');
const refreshApksBtn = document.getElementById('refresh-apks-btn');
const uploadApkBtn = document.getElementById('upload-apk-btn');
const apkStatus = document.getElementById('apk-status');
const apksList = document.getElementById('apks-list');

/**
 * Show status message
 */
function showStatus(message, type = 'info') {
  deviceStatus.textContent = message;
  deviceStatus.className = `status-message ${type}`;
}

/**
 * Hide status message
 */
function hideStatus() {
  deviceStatus.style.display = 'none';
}

/**
 * Render detected devices list
 */
function renderDevices() {
  if (detectedDevices.length === 0) {
    devicesList.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No devices detected. Make sure your device is connected and USB debugging is enabled.</p>';
    return;
  }

  devicesList.innerHTML = detectedDevices.map(device => {
    const isSelected = selectedDevice && selectedDevice.serial === device.serial;
    const hasError = device.error;

    return `
      <div class="device-card ${isSelected ? 'selected' : ''} ${hasError ? 'error' : ''}" 
           data-serial="${device.serial}">
        <div class="device-header">
          <div class="device-name">
            ${device.model || 'Unknown Device'}
            ${device.codename ? ` (${device.codename})` : ''}
          </div>
          <span class="device-state ${device.state}">${device.state}</span>
        </div>
        <div class="device-details">
          <div class="device-detail-item">
            <span class="device-detail-label">Serial:</span>
            <span class="device-detail-value">${device.serial}</span>
          </div>
          ${device.codename ? `
          <div class="device-detail-item">
            <span class="device-detail-label">Codename:</span>
            <span class="device-detail-value">${device.codename}</span>
          </div>
          ` : ''}
          ${device.manufacturer ? `
          <div class="device-detail-item">
            <span class="device-detail-label">Manufacturer:</span>
            <span class="device-detail-value">${device.manufacturer}</span>
          </div>
          ` : ''}
          <div class="device-detail-item">
            <span class="device-detail-label">Bootloader:</span>
            <span class="device-detail-value">${device.bootloader_unlocked ? '🔓 Unlocked' : '🔒 Locked'}</span>
          </div>
        </div>
        ${hasError ? `<div style="color: #fca5a5; margin-top: 10px;">⚠️ ${device.error}</div>` : ''}
      </div>
    `;
  }).join('');

  // Add click handlers
  document.querySelectorAll('.device-card').forEach(card => {
    card.addEventListener('click', () => {
      const serial = card.dataset.serial;
      selectDevice(serial);
    });
  });
}

/**
 * Select a device for flashing
 */
function selectDevice(serial) {
  selectedDevice = detectedDevices.find(d => d.serial === serial);

  if (!selectedDevice) {
    return;
  }

  // Update UI
  document.querySelectorAll('.device-card').forEach(card => {
    card.classList.remove('selected');
    if (card.dataset.serial === serial) {
      card.classList.add('selected');
    }
  });

  // Show selected device info
  selectedDeviceInfo.innerHTML = `
    <strong>Selected Device:</strong><br>
    ${selectedDevice.model || 'Unknown'} (${selectedDevice.codename || 'Unknown codename'})<br>
    Serial: ${selectedDevice.serial}<br>
    State: ${selectedDevice.state}<br>
    Bootloader: ${selectedDevice.bootloader_unlocked ? '🔓 Unlocked' : '🔒 Locked'}
  `;

  // Refresh APK list to update install button states
  renderApks();

  // Show flash section
  flashSection.style.display = 'block';
  bundleSection.style.display = 'block';

  // Enable/disable flash buttons based on bootloader status
  if (selectedDevice.bootloader_unlocked) {
    flashBtn.disabled = false;
    unlockFlashBtn.style.display = 'none';
    warningBox.style.display = 'none';
  } else {
    flashBtn.disabled = true;
    unlockFlashBtn.style.display = 'inline-flex';
    unlockFlashBtn.disabled = false;
    warningBox.style.display = 'block';
    warningText.textContent = 'This device has a locked bootloader. You must unlock it before flashing. Click "Unlock Bootloader & Flash" to proceed.';
  }

  // Load available versions automatically
  loadAvailableVersions();

  // Update download checkbox state
  updateDownloadCheckboxState();

  // Show local bundles info
  showLocalBundlesInfo();
}

/**
 * Show local bundles directory info
 */
async function showLocalBundlesInfo() {
  if (!window.electronAPI) {
    return;
  }

  try {
    const result = await window.electronAPI.getLocalBundlesPath();
    if (result.path) {
      localBundlesInfo.style.display = 'block';
      localBundlesInfo.innerHTML = `Local bundles: <code style="color: #60a5fa;">${result.path}</code>`;
    }
  } catch (error) {
    console.error('Failed to get local bundles path:', error);
  }
}

/**
 * Update download checkbox enabled state based on version selection
 */
function updateDownloadCheckboxState() {
  const version = versionSelect.value;
  downloadBundleFirstCheckbox.disabled = !version;
  if (!version) {
    downloadBundleFirstCheckbox.checked = false;
  }
}

// Auto-load versions when device is selected (removed manual button)

// Store bundle metadata for downloads
let bundleMetadata = {};

/**
 * Load available OS versions for the selected device
 */
async function loadAvailableVersions() {
  if (!selectedDevice || !selectedDevice.codename) {
    return;
  }

  try {
    // Use POST /bundles/index to get all bundles
    const response = await fetch(`${BACKEND_URL}/bundles/index`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to load versions: ${response.statusText}`);
    }

    const data = await response.json();

    // Extract bundles for the selected codename
    const codenameBundles = data[selectedDevice.codename] || [];
    availableVersions = codenameBundles.map(bundle => bundle.version);

    // Store metadata for download URLs
    bundleMetadata = {};
    codenameBundles.forEach(bundle => {
      bundleMetadata[bundle.version] = bundle;
    });

    // Populate version selects
    versionSelect.innerHTML = '<option value="">Use latest available</option>';
    bundleVersionSelect.innerHTML = '<option value="">Select version...</option>';

    availableVersions.forEach(version => {
      const bundle = bundleMetadata[version];
      const displayText = bundle ? `${version} (${bundle.deviceName || selectedDevice.codename})` : version;

      const option1 = document.createElement('option');
      option1.value = version;
      option1.textContent = displayText;
      versionSelect.appendChild(option1);

      const option2 = document.createElement('option');
      option2.value = version;
      option2.textContent = displayText;
      bundleVersionSelect.appendChild(option2);
    });

    if (availableVersions.length > 0) {
      downloadBundleBtn.disabled = false;
    }

    // Update download checkbox state
    updateDownloadCheckboxState();
  } catch (error) {
    console.error('Failed to load versions:', error);
    showStatus(`Failed to load versions: ${error.message}`, 'error');
  }
}

/**
 * Send detected devices to backend
 */
async function registerDevices() {
  if (detectedDevices.length === 0) {
    return;
  }

  try {
    const response = await fetch(`${BACKEND_URL}/devices`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        devices: detectedDevices.map(device => ({
          serial: device.serial,
          state: device.state,
          codename: device.codename,
          model: device.model,
          manufacturer: device.manufacturer || 'Google',
          bootloader_unlocked: device.bootloader_unlocked || false,
        })),
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to register devices: ${response.statusText}`);
    }

    console.log('Devices registered with backend');
  } catch (error) {
    console.error('Failed to register devices:', error);
    showStatus(`Warning: Failed to register devices with backend: ${error.message}`, 'warning');
  }
}

/**
 * Start flashing process
 */
async function startFlashing(unlockBootloader = false) {
  if (!selectedDevice) {
    showStatus('No device selected', 'error');
    return;
  }

  // Disable buttons during process
  flashBtn.disabled = true;
  unlockFlashBtn.disabled = true;

  try {
    const version = versionSelect.value || null;

    // Step 1: Download and extract bundle locally (REQUIRED for local flash)
    if (!version) {
      throw new Error('Please select a version to download');
    }

    showStatus('Downloading and extracting bundle locally...', 'info');
    appendLog(`Starting bundle download: ${selectedDevice.codename} ${version}`, 'info');

    // Show progress bar in flash section
    if (downloadProgress && progressFill && progressText) {
      downloadProgress.style.display = 'block';
      progressFill.style.width = '0%';
      progressText.textContent = 'Starting...';
    }

    let bundleExtracted = false;
    try {
      await downloadBundleFromServer(version);
      bundleExtracted = true;
      showStatus('Bundle downloaded and extracted successfully', 'success');
      appendLog(`Bundle downloaded and extracted successfully`, 'info');
      appendLog(`Bundle location: ${await getLocalBundlePath(selectedDevice.codename, version)}`, 'info');
      // Small delay after download
      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (error) {
      throw new Error(`Bundle download/extraction failed: ${error.message}. Cannot proceed with flash.`);
    }

    // Step 2: Reboot device into fastboot mode if not already there
    if (selectedDevice.state !== 'fastboot') {
      showStatus('Rebooting device into fastboot mode...', 'info');

      if (!window.electronAPI) {
        throw new Error('Electron API not available');
      }

      const rebootResult = await window.electronAPI.rebootToFastboot(selectedDevice.serial);

      if (!rebootResult.success) {
        throw new Error(`Failed to reboot to fastboot: ${rebootResult.error}`);
      }

      showStatus('Device entered fastboot mode. Starting flash job...', 'success');

      // Update device state
      selectedDevice.state = 'fastboot';

      // Refresh device list to show updated state
      const refreshResult = await window.electronAPI.detectDevices();
      if (refreshResult.success) {
        const updatedDevice = refreshResult.devices.find(d => d.serial === selectedDevice.serial);
        if (updatedDevice) {
          selectedDevice = updatedDevice;
          renderDevices();
          selectDevice(selectedDevice.serial); // Re-select to update UI
        }
      }

      // Small delay to ensure device is ready
      await new Promise(resolve => setTimeout(resolve, 1000));
    } else {
      showStatus('Device already in fastboot mode. Starting local flash...', 'info');
    }

    // Step 3: Execute flash locally from extracted bundle
    if (!bundleExtracted) {
      throw new Error('Bundle must be downloaded and extracted before flashing');
    }

    if (!window.electronAPI || !window.electronAPI.executeLocalFlash) {
      throw new Error('Local flash execution not available. Electron API missing.');
    }

    appendLog(`Starting local flash execution...`, 'info');
    appendLog(`Device: ${selectedDevice.serial} (${selectedDevice.codename})`, 'info');
    appendLog(`Bundle: ${selectedDevice.codename} ${version}`, 'info');
    appendLog(`Skip unlock: ${selectedDevice.bootloader_unlocked ? 'Yes' : 'No'}`, 'info');

    const bundlePath = await getLocalBundlePath(selectedDevice.codename, version);
    appendLog(`Bundle path: ${bundlePath}`, 'info');

    // Show job section
    jobSection.style.display = 'block';
    jobIdSpan.textContent = 'local-flash';
    jobStatus.textContent = 'Starting...';
    jobStatus.className = 'job-status running';
    if (logOutput.innerHTML === '') {
      // Keep existing logs from download
    }

    // Set up local flash progress listener
    let flashProgressUnsubscribe = null;
    if (window.electronAPI.onFlashProgress) {
      flashProgressUnsubscribe = window.electronAPI.onFlashProgress((progress) => {
        if (progress.deviceSerial === selectedDevice.serial && progress.codename === selectedDevice.codename) {
          if (progress.message) {
            appendLog(progress.message, progress.status || 'info');
          }
          if (progress.status === 'completed') {
            jobStatus.textContent = 'Completed Successfully';
            jobStatus.className = 'job-status success';
            closeJobBtn.style.display = 'inline-flex';
            showStatus('Flash completed successfully!', 'success');
          } else if (progress.status === 'error') {
            jobStatus.textContent = 'Failed';
            jobStatus.className = 'job-status error';
            closeJobBtn.style.display = 'inline-flex';
            showStatus(`Flash failed: ${progress.error || 'Unknown error'}`, 'error');
          } else if (progress.status === 'starting') {
            jobStatus.textContent = 'Running...';
            jobStatus.className = 'job-status running';
          }
        }
      });
    }

    try {
      const skipUnlock = selectedDevice.bootloader_unlocked || false;
      appendLog(`Executing flash-all.sh from local bundle...`, 'info');
      appendLog(`Skip unlock: ${skipUnlock}`, 'info');

      const result = await window.electronAPI.executeLocalFlash(
        selectedDevice.serial,
        selectedDevice.codename,
        version,
        skipUnlock
      );

      // Clean up progress listener
      if (flashProgressUnsubscribe) {
        flashProgressUnsubscribe();
      }

      if (!result.success) {
        throw new Error(result.error || 'Flash execution failed');
      }

      jobStatus.textContent = 'Completed Successfully';
      jobStatus.className = 'job-status success';
      closeJobBtn.style.display = 'inline-flex';
      showStatus('Flash completed successfully!', 'success');
      appendLog(`✓ Flash completed successfully!`, 'info');
    } catch (error) {
      // Clean up progress listener on error
      if (flashProgressUnsubscribe) {
        flashProgressUnsubscribe();
      }

      jobStatus.textContent = 'Failed';
      jobStatus.className = 'job-status error';
      closeJobBtn.style.display = 'inline-flex';
      appendLog(`✗ Flash failed: ${error.message}`, 'error');
      throw error;
    }
  } catch (error) {
    console.error('Failed to start flashing:', error);
    showStatus(`Failed to start flashing: ${error.message}`, 'error');

    // Re-enable buttons on error
    if (selectedDevice.bootloader_unlocked) {
      flashBtn.disabled = false;
    } else {
      unlockFlashBtn.disabled = false;
    }

    // Hide download status on error
    downloadStatus.style.display = 'none';
  }
}

// SSE reconnection state
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let reconnectTimeout = null;

/**
 * Start streaming logs from backend with reconnection support
 */
function startLogStream() {
  if (!currentJobId) {
    return;
  }

  // Close existing stream if any
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }

  // Clear any pending reconnection
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  reconnectAttempts = 0;
  connectToStream();
}

/**
 * Connect to SSE stream
 */
function connectToStream() {
  if (!currentJobId) {
    return;
  }

  const streamUrl = `${BACKEND_URL}/flash/jobs/${currentJobId}/stream`;
  console.log(`[SSE] Connecting to: ${streamUrl}`);
  appendLog(`Connecting to log stream: ${streamUrl}`, 'info');

  eventSource = new EventSource(streamUrl);

  eventSource.onopen = () => {
    console.log('[SSE] Stream connected successfully');
    reconnectAttempts = 0; // Reset on successful connection
    if (reconnectAttempts > 0) {
      appendLog('Reconnected to log stream', 'success');
    } else {
      appendLog('Log stream connected. Waiting for flash to start...', 'info');
    }
  };

  eventSource.onmessage = (event) => {
    try {
      // Handle both JSON and plain text
      let data;
      if (event.data.trim().startsWith('{')) {
        data = JSON.parse(event.data);
      } else {
        // Plain text message
        appendLog(event.data, 'info');
        return;
      }

      // Handle backend log format: {"line": "..."} or {"status": "..."}
      if (data.line) {
        appendLog(data.line, 'info');
        // Check if line indicates completion
        if (data.line.toLowerCase().includes('completed') || data.line.toLowerCase().includes('success')) {
          jobStatus.textContent = 'Completed Successfully';
          jobStatus.className = 'job-status success';
          closeJobBtn.style.display = 'inline-flex';
          eventSource.close();
          eventSource = null;
          reconnectAttempts = maxReconnectAttempts;
        } else if (data.line.toLowerCase().includes('failed') || data.line.toLowerCase().includes('error')) {
          jobStatus.textContent = 'Failed';
          jobStatus.className = 'job-status error';
          closeJobBtn.style.display = 'inline-flex';
        }
        return;
      }

      // Update job status
      if (data.status) {
        jobStatus.textContent = data.status;
        if (data.status.toLowerCase().includes('success') || data.status.toLowerCase().includes('complete')) {
          jobStatus.className = 'job-status success';
          closeJobBtn.style.display = 'inline-flex';
          if (data.status.toLowerCase().includes('complete')) {
            eventSource.close();
            eventSource = null;
            reconnectAttempts = maxReconnectAttempts;
          }
        } else if (data.status.toLowerCase().includes('error') || data.status.toLowerCase().includes('fail')) {
          jobStatus.className = 'job-status error';
          closeJobBtn.style.display = 'inline-flex';
        }
      }

      // Append log line
      if (data.message) {
        const level = data.level || data.status || 'info';
        appendLog(data.message, level);
      }

      // Handle completion - check for 'complete' or 'status: failed'
      if (data.complete || (data.status && (data.status === 'failed' || data.status === 'completed'))) {
        eventSource.close();
        eventSource = null;
        if (data.success || (data.status === 'completed')) {
          jobStatus.textContent = 'Completed Successfully';
          jobStatus.className = 'job-status success';
        } else {
          jobStatus.textContent = 'Failed';
          jobStatus.className = 'job-status error';
        }
        closeJobBtn.style.display = 'inline-flex';
        reconnectAttempts = maxReconnectAttempts; // Stop reconnecting
      }

      // Also check for 'status: failed' in the message
      if (data.status === 'failed' || (data.message && data.message.toLowerCase().includes('failed'))) {
        jobStatus.textContent = 'Failed';
        jobStatus.className = 'job-status error';
        closeJobBtn.style.display = 'inline-flex';
      }
    } catch (error) {
      console.error('Failed to parse SSE data:', error);
      // Try to display as plain text
      appendLog(event.data, 'info');
    }
  };

  eventSource.onerror = (error) => {
    // Don't log every error - EventSource fires errors frequently
    // Only handle if stream is actually closed
    if (eventSource.readyState === EventSource.CLOSED) {
      // Check if job is already complete
      const isComplete = jobStatus.className === 'job-status success' || jobStatus.className === 'job-status error';

      if (isComplete) {
        // Job is done, don't reconnect
        eventSource = null;
        return;
      }

      // Only reconnect if we haven't exceeded max attempts
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        appendLog(`Connection lost. Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`, 'warning');

        // Close current connection
        eventSource.close();
        eventSource = null;

        // Reconnect after delay (exponential backoff)
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 10000);
        reconnectTimeout = setTimeout(() => {
          connectToStream();
        }, delay);
      } else {
        appendLog('Max reconnection attempts reached. Stream closed.', 'error');
        eventSource.close();
        eventSource = null;
      }
    }
    // If readyState is CONNECTING or OPEN, ignore the error (EventSource fires errors during normal operation)
  };
}

/**
 * Append log line to output
 * Can be called before jobSection is shown
 */
function appendLog(message, level = 'info') {
  // Ensure log output element exists
  if (!logOutput) {
    console.log(`[Log] ${message}`);
    return;
  }

  const logLine = document.createElement('div');
  logLine.className = `log-line ${level}`;
  logLine.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  logOutput.appendChild(logLine);

  // Auto-scroll to bottom
  logOutput.scrollTop = logOutput.scrollHeight;

  // Also log to console for debugging
  if (level === 'error') {
    console.error(`[Log] ${message}`);
  } else {
    console.log(`[Log] ${message}`);
  }
}

/**
 * Download bundle ZIP (for manual download)
 */
async function downloadBundle() {
  if (!selectedDevice || !selectedDevice.codename) {
    showStatus('No device selected', 'error');
    return;
  }

  const version = bundleVersionSelect.value;
  if (!version) {
    showStatus('Please select a version', 'error');
    return;
  }

  const bundle = bundleMetadata[version];
  if (!bundle || !bundle.downloadUrl) {
    showStatus(`Download URL not available for version ${version}`, 'error');
    return;
  }

  // Use the downloadUrl from bundle metadata
  const downloadUrl = bundle.downloadUrl;

  // Create a temporary anchor element to trigger download
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = `${selectedDevice.codename}-${version}.zip`;
  link.target = '_blank';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showStatus(`Downloading ${version}...`, 'info');
}

/**
 * Download bundle from backend server and save locally
 * Returns true if download successful, false otherwise
 */
async function downloadBundleFromServer(version) {
  if (!selectedDevice || !selectedDevice.codename) {
    throw new Error('No device selected');
  }

  if (!version) {
    throw new Error('No version specified');
  }

  const bundle = bundleMetadata[version];
  if (!bundle || !bundle.downloadUrl) {
    throw new Error(`Download URL not available for version ${version}`);
  }

  if (!window.electronAPI) {
    throw new Error('Electron API not available');
  }

  downloadStatus.style.display = 'block';

  // First check if bundle exists locally and is extracted
  appendLog(`Checking if bundle is already present...`, 'info');
  const localCheck = await window.electronAPI.checkLocalBundle(selectedDevice.codename, version);

  if (localCheck.exists) {
    if (localCheck.extracted) {
      // Bundle is already extracted and ready
      downloadStatus.innerHTML = `<div style="color: #6ee7b7;">✓ Bundle ${version} already downloaded and extracted locally${localCheck.size > 0 ? ` (${formatBytes(localCheck.size)})` : ''}</div>`;
      appendLog(`Bundle already present and extracted at: ${localCheck.path}`, 'info');
      appendLog(`Skipping download - bundle ready to use`, 'info');
      return true;
    } else {
      // Bundle ZIP exists but not extracted - extract it
      downloadStatus.innerHTML = `<div style="color: #fbbf24;">Bundle ZIP found, extracting...</div>`;
      appendLog(`Bundle ZIP found at: ${localCheck.path}, extracting...`, 'info');

      // Extract the existing ZIP (pass empty URL to skip download)
      try {
        const result = await window.electronAPI.downloadBundleLocal(
          selectedDevice.codename,
          version,
          '' // Empty URL means just extract existing ZIP
        );

        if (result.success) {
          downloadStatus.innerHTML = `<div style="color: #6ee7b7;">✓ Bundle extracted successfully</div>`;
          appendLog(`Bundle extracted successfully`, 'info');
          return true;
        } else {
          throw new Error(result.error || 'Extraction failed');
        }
      } catch (error) {
        appendLog(`Extraction failed: ${error.message}, will re-download`, 'warning');
        // Continue to download if extraction fails
      }
    }
  }

  // Show progress bar (ensure elements exist)
  if (downloadProgress && progressFill && progressText) {
    downloadProgress.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = '0%';
  }
  downloadStatus.innerHTML = `<div style="color: #93c5fd;">Preparing download...</div>`;

  // Set up progress listener
  let progressUnsubscribe = null;
  if (window.electronAPI && window.electronAPI.onDownloadProgress) {
    progressUnsubscribe = window.electronAPI.onDownloadProgress((progress) => {
      if (progress.codename === selectedDevice.codename && progress.version === version) {
        updateDownloadProgress(progress);
      }
    });
  }

  try {
    // Prefer backend download endpoint if available
    let downloadUrl = bundle.downloadUrl;
    let downloadSource = 'GrapheneOS releases';

    // Try backend download endpoint first
    const backendDownloadUrl = `${BACKEND_URL}/bundles/releases/${selectedDevice.codename}/${version}/download`;
    let useBackendDownload = false;

    appendLog(`Checking bundle availability...`, 'info');
    try {
      const testResponse = await fetch(backendDownloadUrl, {
        method: 'HEAD',
        // Add timeout to prevent hanging (5 seconds)
        signal: AbortSignal.timeout(5000)
      });

      if (testResponse.ok) {
        useBackendDownload = true;
        downloadUrl = backendDownloadUrl;
        downloadSource = 'backend server';
        downloadStatus.innerHTML = `<div style="color: #93c5fd;">Downloading from backend server...</div>`;
        appendLog(`Using backend download: ${backendDownloadUrl}`, 'info');
        console.log(`[Download] Using backend download URL: ${backendDownloadUrl}`);
      } else {
        // 404 or other error - bundle not on backend, use direct URL
        appendLog(`Backend bundle not available (${testResponse.status}), using direct download`, 'warning');
        console.log(`[Download] Backend download returned ${testResponse.status}, using direct URL`);
        downloadStatus.innerHTML = `<div style="color: #93c5fd;">Downloading from GrapheneOS releases...</div>`;
      }
    } catch (error) {
      // Network error, timeout, or CORS issue - fall back to direct URL
      appendLog(`Backend check failed, using direct download: ${error.message}`, 'warning');
      console.log(`[Download] Backend download check failed (${error.name}: ${error.message}), using direct URL`);
      downloadStatus.innerHTML = `<div style="color: #93c5fd;">Downloading from GrapheneOS releases...</div>`;
    }

    // If backend download failed, ensure we use direct URL
    if (!useBackendDownload) {
      downloadUrl = bundle.downloadUrl;
    }

    // Use Electron main process to download (bypasses CSP)
    const filename = `${selectedDevice.codename}-factory-${version}.zip`;
    appendLog(`Starting download: ${filename}`, 'info');
    appendLog(`Source: ${downloadSource}`, 'info');
    appendLog(`URL: ${downloadUrl}`, 'info');
    console.log(`[Download] Starting download: ${downloadUrl}`);

    const result = await window.electronAPI.downloadBundleLocal(
      selectedDevice.codename,
      version,
      downloadUrl
    );

    // Clean up progress listener
    if (progressUnsubscribe) {
      progressUnsubscribe();
    }

    if (!result.success) {
      throw new Error(result.error || 'Download failed');
    }

    if (result.cached) {
      downloadStatus.innerHTML = `<div style="color: #6ee7b7;">✓ Bundle ${version} found in cache (${formatBytes(result.size)})</div>`;
      appendLog(`Bundle found in cache: ${formatBytes(result.size)}`, 'info');
      if (progressFill && progressText) {
        progressFill.style.width = '100%';
        progressText.textContent = '100% (cached)';
      }
    } else {
      const sizeText = result.size ? formatBytes(result.size) : '';
      downloadStatus.innerHTML = `<div style="color: #6ee7b7;">✓ Bundle ${version} downloaded successfully ${sizeText}</div>`;
      appendLog(`Download completed: ${sizeText}`, 'info');
      if (progressFill && progressText) {
        progressFill.style.width = '100%';
        progressText.textContent = '100%';
      }
    }

    // Hide progress bar after a delay
    if (downloadProgress) {
      setTimeout(() => {
        downloadProgress.style.display = 'none';
      }, 2000);
    }

    return true;
  } catch (error) {
    // Clean up progress listener on error
    if (progressUnsubscribe) {
      progressUnsubscribe();
    }

    downloadStatus.innerHTML = `<div style="color: #fca5a5;">✗ Download failed: ${error.message}</div>`;
    appendLog(`Download failed: ${error.message}`, 'error');
    if (progressFill && progressText) {
      progressFill.style.width = '0%';
      progressText.textContent = 'Failed';
    }
    throw error;
  }
}

/**
 * Update download progress bar and logs
 */
function updateDownloadProgress(progress) {
  if (!progress) return;

  const percentage = progress.percentage || 0;
  const downloaded = progress.downloaded || 0;
  const total = progress.total || 0;
  const status = progress.status || 'downloading';
  const filename = progress.filename || 'bundle.zip';

  // Update progress bar
  if (progressFill && progressText) {
    progressFill.style.width = `${percentage}%`;

    if (status === 'completed') {
      progressText.textContent = `100% - ${formatBytes(total)}`;
    } else if (status === 'cached') {
      progressText.textContent = `100% (cached) - ${formatBytes(total)}`;
    } else if (status === 'error') {
      progressText.textContent = `Error: ${progress.error || 'Unknown error'}`;
    } else {
      const downloadedStr = formatBytes(downloaded);
      const totalStr = total > 0 ? formatBytes(total) : '?';
      progressText.textContent = `${percentage}% - ${downloadedStr}${total > 0 ? ' / ' + totalStr : ''}`;
    }
  }

  // Update logs - show what's being downloaded
  if (status === 'downloading') {
    // Log every 10% progress or on significant milestones
    if (percentage % 10 === 0 && percentage > 0) {
      const downloadedStr = formatBytes(downloaded);
      const totalStr = total > 0 ? formatBytes(total) : 'unknown size';
      appendLog(`Downloading ${filename}: ${percentage}% (${downloadedStr} / ${totalStr})`, 'info');
    } else if (percentage === 0 && downloaded === 0) {
      // Initial download start
      appendLog(`Starting download: ${filename}`, 'info');
      if (total > 0) {
        appendLog(`Total size: ${formatBytes(total)}`, 'info');
      }
    }
  } else if (status === 'completed') {
    appendLog(`✓ Download completed: ${filename} (${formatBytes(total)})`, 'info');
  } else if (status === 'cached') {
    appendLog(`✓ Using cached bundle: ${filename} (${formatBytes(total)})`, 'info');
  } else if (status === 'error') {
    appendLog(`✗ Download error: ${progress.error || 'Unknown error'}`, 'error');
  }
}

/**
 * Get local bundle path
 */
async function getLocalBundlePath(codename, version) {
  if (!window.electronAPI) {
    return 'N/A';
  }
  try {
    const result = await window.electronAPI.getLocalBundlesPath();
    return `${result.path}/${codename}/${version}`;
  } catch (error) {
    return 'N/A';
  }
}

/**
 * Format bytes to human readable format
 */
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Detect devices using Electron IPC
 */
async function detectDevices() {
  detectBtn.disabled = true;
  detectBtn.innerHTML = '<span class="spinner"></span> Detecting...';
  hideStatus();

  try {
    if (!window.electronAPI) {
      throw new Error('Electron API not available. Make sure you are running in Electron.');
    }

    const result = await window.electronAPI.detectDevices();

    if (!result.success) {
      throw new Error(result.error || 'Device detection failed');
    }

    detectedDevices = result.devices || [];

    if (detectedDevices.length === 0) {
      showStatus('No devices detected. Make sure your device is connected and USB debugging is enabled.', 'warning');
    } else {
      showStatus(`Detected ${detectedDevices.length} device(s)`, 'success');
      refreshBtn.style.display = 'inline-flex';

      // Register devices with backend
      await registerDevices();
    }

    renderDevices();

    // Refresh APK list to update install button states (always call to update button states)
    renderApks();
  } catch (error) {
    console.error('Device detection failed:', error);
    showStatus(`Device detection failed: ${error.message}`, 'error');
    detectedDevices = [];
    renderDevices();

    // Refresh APK list even on error (to disable buttons)
    if (availableApks.length > 0) {
      renderApks();
    }
  } finally {
    detectBtn.disabled = false;
    detectBtn.innerHTML = '<span class="btn-icon">🔍</span> Detect Devices';
  }
}

/**
 * Close job section
 */
function closeJob() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }
  reconnectAttempts = 0;
  jobSection.style.display = 'none';
  currentJobId = null;
  logOutput.innerHTML = '';
}

/**
 * APK Management Functions
 */

let availableApks = [];

/**
 * Show APK status message
 */
function showApkStatus(message, type = 'info') {
  apkStatus.textContent = message;
  apkStatus.className = `status-message ${type}`;
  apkStatus.style.display = 'block';
}

/**
 * Hide APK status message
 */
function hideApkStatus() {
  apkStatus.style.display = 'none';
}

/**
 * Format file size
 */
function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format date/time
 */
function formatDateTime(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString();
}

/**
 * Load available APKs from server
 */
async function loadApks() {
  try {
    showApkStatus('Loading APKs...', 'info');

    const response = await fetch(`${BACKEND_URL}/apks/list`);

    if (!response.ok) {
      throw new Error(`Failed to load APKs: ${response.statusText}`);
    }

    availableApks = await response.json();

    renderApks();
    hideApkStatus();
  } catch (error) {
    console.error('Error loading APKs:', error);
    showApkStatus(`Failed to load APKs: ${error.message}`, 'error');
    apksList.innerHTML = `<p style="color: #f44336; text-align: center; padding: 20px;">Error: ${error.message}</p>`;
  }
}

/**
 * Render APKs list
 */
function renderApks() {
  if (availableApks.length === 0) {
    apksList.innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No APKs available on the server.</p>';
    return;
  }

  // Check if a device is selected
  const hasDevice = selectedDevice && selectedDevice.serial;

  // Debug logging
  console.log('[APK] Rendering APKs:', {
    hasDevice: !!hasDevice,
    selectedDeviceExists: !!selectedDevice,
    deviceSerial: selectedDevice?.serial,
    deviceState: selectedDevice?.state,
    availableApksCount: availableApks.length,
    message: hasDevice ? `Device selected: ${selectedDevice.serial} (${selectedDevice.state})` : 'No device selected - install buttons will be disabled'
  });

  // Build APK list HTML
  const apksHTML = availableApks.map((apk, index) => {
    // Enable install if device is selected and NOT in fastboot mode
    // ADB states that allow installation: 'device', 'online', etc. (anything except 'fastboot')
    const canInstall = hasDevice && selectedDevice && selectedDevice.state && selectedDevice.state !== 'fastboot';

    // Determine tooltip message
    let tooltipMessage = '';
    if (!hasDevice) {
      tooltipMessage = 'Please select a device first';
    } else if (selectedDevice.state === 'fastboot') {
      tooltipMessage = 'Device must be in device mode (not fastboot) to install APKs';
    } else if (!selectedDevice.state || selectedDevice.state === 'offline' || selectedDevice.state === 'unauthorized') {
      tooltipMessage = `Device is in ${selectedDevice.state || 'unknown'} state. Please ensure USB debugging is enabled.`;
    }

    return `
      <div class="apk-card">
        <div class="apk-header">
          <div class="apk-name">
            <span class="apk-icon">📱</span>
            <span>${apk.filename}</span>
          </div>
          <div class="apk-size">${formatBytes(apk.size || 0)}</div>
        </div>
        <div class="apk-details">
          <div class="apk-detail-item">
            <span class="apk-detail-label">Uploaded:</span>
            <span class="apk-detail-value">${formatDateTime(apk.upload_time)}</span>
          </div>
        </div>
        <div class="apk-actions">
          <button 
            class="btn btn-primary btn-sm install-apk-btn" 
            data-filename="${apk.filename}"
            ${!canInstall ? `disabled title="${tooltipMessage}"` : ''}
          >
            <span class="btn-icon">📲</span>
            Install APK
          </button>
        </div>
      </div>
    `;
  }).join('');

  // Add helpful message if no device selected, otherwise just show APKs
  if (!hasDevice) {
    const noDeviceMsg = '<div style="background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 12px; margin-bottom: 15px; color: #fbbf24;"><strong>ℹ️ No device selected</strong><br><span style="font-size: 0.9em;">Please detect and select a device first to enable install buttons.</span></div>';
    apksList.innerHTML = noDeviceMsg + apksHTML;
  } else {
    apksList.innerHTML = apksHTML;
  }

  // Add event listeners to install buttons
  document.querySelectorAll('.install-apk-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const filename = e.target.closest('.install-apk-btn').dataset.filename;
      await installApk(filename);
    });
  });
}

/**
 * Install APK on selected device
 */
async function installApk(filename) {
  if (!selectedDevice || !selectedDevice.serial) {
    showApkStatus('Please select a device first', 'error');
    return;
  }

  // Check if device is in fastboot mode (can't install APKs in fastboot)
  if (selectedDevice.state === 'fastboot') {
    showApkStatus('Device must be in device mode (not fastboot) to install APKs. Please reboot the device to normal mode.', 'error');
    return;
  }

  // Check if device is in a valid state for ADB commands
  if (!selectedDevice.state || selectedDevice.state === 'offline' || selectedDevice.state === 'unauthorized') {
    showApkStatus(`Device is in ${selectedDevice.state || 'unknown'} state. Please ensure USB debugging is enabled and device is authorized.`, 'error');
    return;
  }

  try {
    showApkStatus(`Installing ${filename}...`, 'info');

    // Call IPC handler to install APK
    const result = await window.electronAPI.installApk(selectedDevice.serial, filename);

    if (result.success) {
      showApkStatus(`✓ ${filename} installed successfully`, 'success');
      appendLog(`[APK] Installed ${filename} on device ${selectedDevice.serial}`, 'success');

      // Refresh APK list after a short delay
      setTimeout(() => {
        loadApks();
      }, 1000);
    } else {
      throw new Error(result.error || 'Installation failed');
    }
  } catch (error) {
    console.error('Error installing APK:', error);
    showApkStatus(`Failed to install ${filename}: ${error.message}`, 'error');
    appendLog(`[APK] Failed to install ${filename}: ${error.message}`, 'error');
  }
}

// Event Listeners
detectBtn.addEventListener('click', detectDevices);
refreshBtn.addEventListener('click', detectDevices);
flashBtn.addEventListener('click', () => startFlashing(false));
unlockFlashBtn.addEventListener('click', () => startFlashing(true));
downloadBundleBtn.addEventListener('click', downloadBundle);
closeJobBtn.addEventListener('click', closeJob);
versionSelect.addEventListener('change', updateDownloadCheckboxState);
refreshApksBtn.addEventListener('click', loadApks);

/**
 * Handle APK file upload
 */
uploadApkBtn.addEventListener('click', async () => {
  try {
    uploadApkBtn.disabled = true;
    showApkStatus('Selecting APK file...', 'info');

    // Call IPC handler to open file dialog and upload APK
    const result = await window.electronAPI.uploadApk();

    if (result.success) {
      showApkStatus(`✓ ${result.message || 'APK uploaded successfully'}`, 'success');
      appendLog(`[APK] ${result.message || 'APK uploaded successfully'}`, 'success');

      // Refresh APK list after a short delay
      setTimeout(() => {
        loadApks();
      }, 1000);
    } else {
      if (result.error !== 'No file selected') {
        showApkStatus(`Failed to upload: ${result.error}`, 'error');
        appendLog(`[APK] Failed to upload: ${result.error}`, 'error');
      } else {
        hideApkStatus(); // User cancelled, don't show error
      }
    }
  } catch (error) {
    console.error('Error uploading APK:', error);
    showApkStatus(`Failed to upload: ${error.message}`, 'error');
    appendLog(`[APK] Failed to upload: ${error.message}`, 'error');
  } finally {
    uploadApkBtn.disabled = false;
  }
});

// Initialize
console.log('FlashDash Client initialized');
showStatus('Ready. Click "Detect Devices" to begin.', 'info');

// Auto-load APKs on startup
loadApks();
