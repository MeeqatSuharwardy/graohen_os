import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@flashdash/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@flashdash/ui';
import { Download, Apple, Laptop, HardDrive, CheckCircle2 } from 'lucide-react';

interface BuildInfo {
  platform: 'windows' | 'mac' | 'linux';
  name: string;
  icon: typeof Laptop;
  url: string;
  size: string;
  version: string;
  description: string;
}

// Get download base URL from environment or use default
const getDownloadBaseUrl = () => {
  return import.meta.env.VITE_DOWNLOAD_BASE_URL || 'https://os.fxmail.ai/download';
};

const builds: BuildInfo[] = [
  {
    platform: 'windows',
    name: 'Windows',
    icon: Laptop,
    url: import.meta.env.VITE_DESKTOP_DOWNLOAD_WIN || `${getDownloadBaseUrl()}/@flashdashdesktop%20Setup%201.0.0.exe`,
    version: '1.0.0',
    description: 'Windows 10/11 installer (.exe)',
    size: '~120 MB',
  },
  {
    platform: 'mac',
    name: 'macOS',
    icon: Apple,
    url: import.meta.env.VITE_DESKTOP_DOWNLOAD_MAC || `${getDownloadBaseUrl()}/FlashDash-1.0.0.dmg`,
    version: '1.0.0',
    description: 'macOS 10.15+ installer (.dmg)',
    size: '~120 MB',
  },
  {
    platform: 'linux',
    name: 'Linux',
    icon: HardDrive,
    url: import.meta.env.VITE_DESKTOP_DOWNLOAD_LINUX || `${getDownloadBaseUrl()}/flashdash-1.0.0.AppImage`,
    version: '1.0.0',
    description: 'Linux AppImage and .deb packages',
    size: '~120 MB',
  },
];

export function Downloads() {
  const [os, setOs] = useState<'windows' | 'mac' | 'linux' | 'unknown'>('unknown');

  useEffect(() => {
    const userAgent = navigator.userAgent.toLowerCase();
    if (userAgent.includes('win')) setOs('windows');
    else if (userAgent.includes('mac')) setOs('mac');
    else if (userAgent.includes('linux')) setOs('linux');
    else setOs('unknown');
  }, []);

  const recommendedBuild = builds.find(b => b.platform === os) || builds[0];

  return (
    <div className="min-h-screen container mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-6xl mx-auto space-y-6 sm:space-y-8"
      >
        {/* Header */}
        <div className="text-center space-y-3 sm:space-y-4">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent px-4">
            Download FlashDash Desktop
          </h1>
          <p className="text-base sm:text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto px-4">
            Professional GrapheneOS flashing dashboard for Pixel devices. 
            Available for Windows, macOS, and Linux.
          </p>
        </div>

        {/* Recommended Build */}
        {os !== 'unknown' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-primary/10 border-2 border-primary rounded-lg p-4 sm:p-6"
          >
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 mb-3 sm:mb-4">
              <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6 text-primary flex-shrink-0" />
              <h2 className="text-xl sm:text-2xl font-semibold">Recommended for Your System</h2>
            </div>
            <Card className="bg-card">
              <CardContent className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3 sm:gap-4">
                    <recommendedBuild.icon className="w-10 h-10 sm:w-12 sm:h-12 text-primary flex-shrink-0" />
                    <div>
                      <h3 className="text-lg sm:text-xl font-semibold">{recommendedBuild.name}</h3>
                      <p className="text-sm sm:text-base text-muted-foreground">{recommendedBuild.description}</p>
                      <p className="text-xs sm:text-sm text-muted-foreground mt-1">Version {recommendedBuild.version}</p>
                    </div>
                  </div>
                  <Button
                    size="lg"
                    className="w-full sm:w-auto"
                    onClick={() => window.open(recommendedBuild.url, '_blank')}
                    disabled={recommendedBuild.url === '#'}
                  >
                    <Download className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
                    <span className="text-sm sm:text-base">Download for {recommendedBuild.name}</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* All Builds */}
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold mb-4 sm:mb-6 px-4 sm:px-0">All Downloads</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {builds.map((build, index) => {
              const Icon = build.icon;
              const isRecommended = build.platform === os;
              
              return (
                <motion.div
                  key={build.platform}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + index * 0.1 }}
                >
                  <Card className={`h-full ${isRecommended ? 'ring-2 ring-primary' : ''}`}>
                    <CardHeader className="p-4 sm:p-6">
                      <div className="flex items-center gap-2 sm:gap-3">
                        <Icon className="w-7 h-7 sm:w-8 sm:h-8 text-primary flex-shrink-0" />
                        <CardTitle className="text-lg sm:text-xl">{build.name}</CardTitle>
                        {isRecommended && (
                          <span className="ml-auto text-xs bg-primary text-primary-foreground px-2 py-1 rounded whitespace-nowrap">
                            Recommended
                          </span>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3 sm:space-y-4 p-4 sm:p-6 pt-0">
                      <p className="text-sm sm:text-base text-muted-foreground">{build.description}</p>
                      <div className="text-xs sm:text-sm text-muted-foreground space-y-1">
                        <p>Version: {build.version}</p>
                        {build.size && <p>Size: {build.size}</p>}
                      </div>
                      <Button
                        className="w-full"
                        onClick={() => window.open(build.url, '_blank')}
                        disabled={build.url === '#'}
                        variant={isRecommended ? 'default' : 'outline'}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        <span className="text-sm sm:text-base">{build.url === '#' ? 'Coming Soon' : 'Download'}</span>
                      </Button>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* System Requirements */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader className="p-4 sm:p-6">
              <CardTitle className="text-lg sm:text-xl">System Requirements</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-4 sm:p-6 pt-0">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                <div>
                  <h3 className="text-base sm:text-lg font-semibold mb-2">Windows</h3>
                  <ul className="text-xs sm:text-sm text-muted-foreground space-y-1">
                    <li>• Windows 10 or later</li>
                    <li>• 64-bit processor</li>
                    <li>• 100 MB free disk space</li>
                    <li>• ADB/Fastboot tools</li>
                  </ul>
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-semibold mb-2">macOS</h3>
                  <ul className="text-xs sm:text-sm text-muted-foreground space-y-1">
                    <li>• macOS 10.15 or later</li>
                    <li>• Intel or Apple Silicon</li>
                    <li>• 100 MB free disk space</li>
                    <li>• ADB/Fastboot tools</li>
                  </ul>
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-semibold mb-2">Linux</h3>
                  <ul className="text-xs sm:text-sm text-muted-foreground space-y-1">
                    <li>• Ubuntu 20.04+ or similar</li>
                    <li>• 64-bit processor</li>
                    <li>• 100 MB free disk space</li>
                    <li>• ADB/Fastboot tools</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Additional Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="text-center text-xs sm:text-sm text-muted-foreground px-4"
        >
          <p>
            Need help? Check out our{' '}
            <a href="/docs" className="text-primary hover:underline">
              documentation
            </a>{' '}
            or{' '}
            <a href="https://github.com/flashdash/flashdash" className="text-primary hover:underline">
              GitHub repository
            </a>
            .
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
}
