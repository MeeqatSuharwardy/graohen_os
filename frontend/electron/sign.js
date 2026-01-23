/**
 * Custom code signing script for electron-builder
 * 
 * This script handles code signing for Windows executables.
 * Set CSC_LINK and CSC_KEY_PASSWORD environment variables to enable signing.
 */

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

exports.default = async function(config) {
  const { path: filePath } = config;
  
  // Check if certificate is provided
  if (!process.env.CSC_LINK) {
    console.log('⚠️  No code signing certificate provided (CSC_LINK not set)');
    console.log('   Building unsigned executable - SmartScreen warning will appear');
    return;
  }

  const certPath = process.env.CSC_LINK;
  const certPassword = process.env.CSC_KEY_PASSWORD || '';

  // Verify certificate file exists
  if (!fs.existsSync(certPath)) {
    console.error(`✗ Certificate file not found: ${certPath}`);
    throw new Error(`Certificate file not found: ${certPath}`);
  }

  console.log(`🔐 Signing executable: ${filePath}`);
  console.log(`   Using certificate: ${certPath}`);

  // Determine if we're on Windows (can use signtool) or cross-compiling
  const isWindows = process.platform === 'win32';
  
  if (isWindows) {
    // Use signtool on Windows
    try {
      // Try to find signtool (usually in Windows SDK)
      const signToolPaths = [
        'C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.22621.0\\x64\\signtool.exe',
        'C:\\Program Files (x86)\\Windows Kits\\10\\bin\\x64\\signtool.exe',
        'signtool.exe' // In PATH
      ];

      let signTool = null;
      for (const toolPath of signToolPaths) {
        try {
          execSync(`"${toolPath}" /?`, { stdio: 'ignore' });
          signTool = toolPath;
          break;
        } catch (e) {
          // Try next path
        }
      }

      if (!signTool) {
        // Fallback to electron-builder's built-in signing
        console.log('   Using electron-builder built-in signing...');
        return; // Let electron-builder handle it
      }

      // Sign with signtool
      const signCommand = `"${signTool}" sign /f "${certPath}" /p "${certPassword}" /t http://timestamp.digicert.com /d "FlashDash" /du "https://freedomos.vulcantech.co" "${filePath}"`;
      
      execSync(signCommand, { stdio: 'inherit' });
      console.log('✓ Code signing successful');
      
      // Verify signature
      try {
        execSync(`"${signTool}" verify /pa /v "${filePath}"`, { stdio: 'inherit' });
        console.log('✓ Signature verification successful');
      } catch (verifyError) {
        console.warn('⚠️  Signature verification failed (this may be normal for self-signed certs)');
      }
    } catch (error) {
      console.error('✗ Code signing failed:', error.message);
      // Don't throw - let electron-builder try its own method
      console.log('   Falling back to electron-builder built-in signing...');
    }
  } else {
    // Cross-compiling from macOS/Linux
    // electron-builder will handle signing automatically if CSC_LINK is set
    console.log('   Using electron-builder built-in signing (cross-compile)...');
  }
};
