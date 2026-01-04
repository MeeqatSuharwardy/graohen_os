module.exports = {
  appId: 'com.flashdash.app',
  productName: 'FlashDash',
  directories: {
    output: 'out',
  },
  files: [
    'dist/**/*',
    'dist-electron/**/*',
    'package.json',
  ],
  mac: {
    category: 'public.app-category.utilities',
    target: ['dmg'],
    icon: 'assets/icon.icns',
  },
  win: {
    target: ['nsis'],
    icon: 'assets/icon.ico',
  },
  linux: {
    target: ['AppImage'],
    icon: 'assets/icon.png',
    category: 'Utility',
  },
  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true,
  },
  protocols: [
    {
      name: 'FlashDash Protocol',
      schemes: ['flashdash'],
    },
  ],
};

