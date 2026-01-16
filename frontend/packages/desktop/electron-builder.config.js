module.exports = {
  appId: 'com.flashdash.app',
  productName: 'FlashDash',
  directories: {
    output: 'dist',
    buildResources: 'assets',
  },
  files: [
    'dist/**/*',
    'dist-electron/**/*',
    'package.json',
    '!**/*.map',
    '!node_modules',
  ],
  mac: {
    category: 'public.app-category.utilities',
    target: [
      {
        target: 'dmg',
        arch: ['x64', 'arm64'],
      },
    ],
    icon: 'assets/icon.icns',
    hardenedRuntime: true,
    gatekeeperAssess: false,
    entitlements: 'assets/entitlements.mac.plist',
    entitlementsInherit: 'assets/entitlements.mac.plist',
  },
  win: {
    target: [
      {
        target: 'nsis',
        arch: ['x64', 'ia32'],
      },
    ],
    icon: 'assets/icon.ico',
    sign: null,
    signAndEditExecutable: false,
    signDlls: false,
  },
  linux: {
    target: [
      {
        target: 'AppImage',
        arch: ['x64'],
      },
      {
        target: 'deb',
        arch: ['x64'],
      },
    ],
    executableName: 'flashdash',
    category: 'Utility',
    maintainer: 'FlashDash Team <support@flashdash.dev>',
    synopsis: 'GrapheneOS Flashing Dashboard',
    description: 'Professional GrapheneOS flashing dashboard for Pixel devices',
  },
  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true,
    createDesktopShortcut: true,
    createStartMenuShortcut: true,
    shortcutName: 'FlashDash',
  },
  protocols: [
    {
      name: 'FlashDash Protocol',
      schemes: ['flashdash'],
    },
  ],
  publish: null, // Set this if you want to auto-publish to GitHub releases, etc.
};

