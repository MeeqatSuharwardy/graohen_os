import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@flashdash/ui';
import { Card, CardContent } from '@flashdash/ui';
import { Badge } from '@flashdash/ui';
import { Download, Smartphone, Shield, Zap, ArrowRight, Monitor, Globe } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

function detectOS(): 'windows' | 'mac' | 'linux' | 'unknown' {
  const userAgent = navigator.userAgent.toLowerCase();
  if (userAgent.includes('win')) return 'windows';
  if (userAgent.includes('mac')) return 'mac';
  if (userAgent.includes('linux')) return 'linux';
  return 'unknown';
}

const getDownloadBaseUrl = () => {
  return import.meta.env.VITE_DOWNLOAD_BASE_URL || 'https://os.fxmail.ai/download';
};

function getDownloadUrl(os: string): string {
  const baseUrl = getDownloadBaseUrl();
  const winUrl = import.meta.env.VITE_DESKTOP_DOWNLOAD_WIN || `${baseUrl}/@flashdashdesktop%20Setup%201.0.0.exe`;
  const macUrl = import.meta.env.VITE_DESKTOP_DOWNLOAD_MAC || `${baseUrl}/FlashDash-1.0.0.dmg`;
  const linuxUrl = import.meta.env.VITE_DESKTOP_DOWNLOAD_LINUX || `${baseUrl}/flashdash-1.0.0.AppImage`;

  switch (os) {
    case 'windows':
      return winUrl;
    case 'mac':
      return macUrl;
    case 'linux':
      return linuxUrl;
    default:
      return '#';
  }
}

function getDownloadLabel(os: string): string {
  switch (os) {
    case 'windows':
      return 'Download for Windows';
    case 'mac':
      return 'Download for macOS';
    case 'linux':
      return 'Download for Linux';
    default:
      return 'Download Desktop App';
  }
}

export function Landing() {
  const [os, setOs] = useState<'windows' | 'mac' | 'linux' | 'unknown'>('unknown');
  const navigate = useNavigate();

  useEffect(() => {
    setOs(detectOS());
  }, []);

  const handleOpenDesktop = () => {
    const protocol = import.meta.env.VITE_DESKTOP_PROTOCOL || 'flashdash://open';
    window.location.href = protocol;
    
    // Fallback: show modal after timeout
    setTimeout(() => {
      const confirmed = window.confirm(
        'Could not open desktop app. Would you like to download it instead?'
      );
      if (confirmed) {
        window.open(getDownloadUrl(os), '_blank');
      }
    }, 1000);
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 md:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl mx-auto text-center space-y-6 sm:space-y-8"
        >
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2 }}
          >
            <Badge className="mb-3 sm:mb-4 text-xs sm:text-sm" variant="outline">
              <Shield className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
              Production Ready
            </Badge>
          </motion.div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent px-4">
            FlashDash
          </h1>
          <p className="text-lg sm:text-xl md:text-2xl text-muted-foreground max-w-2xl mx-auto px-4">
            Professional GrapheneOS flashing dashboard for Pixel devices
          </p>

          <motion.div
            className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-stretch sm:items-center px-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Button
              size="lg"
              className="group relative overflow-hidden w-full sm:w-auto"
              onClick={() => window.open(getDownloadUrl(os), '_blank')}
            >
              <Download className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
              <span className="text-sm sm:text-base">{getDownloadLabel(os)}</span>
              <motion.div
                className="absolute inset-0 bg-primary/20"
                initial={{ x: '-100%' }}
                whileHover={{ x: '100%' }}
                transition={{ duration: 0.5 }}
              />
            </Button>

            <Button
              size="lg"
              variant="outline"
              className="w-full sm:w-auto"
              onClick={() => navigate('/downloads')}
            >
              <Download className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
              <span className="text-sm sm:text-base">All Downloads</span>
            </Button>

            <Button
              size="lg"
              variant="outline"
              className="w-full sm:w-auto hidden md:flex"
              onClick={handleOpenDesktop}
            >
              <Monitor className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
              <span className="text-sm sm:text-base">Open Desktop App</span>
              <ArrowRight className="w-3 h-3 sm:w-4 sm:h-4 ml-2" />
            </Button>

            <Button
              size="lg"
              variant="default"
              className="w-full sm:w-auto bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
              onClick={() => {
                const webFlasherUrl = import.meta.env.VITE_WEB_FLASHER_URL || `${window.location.origin}/flash`;
                
                if (import.meta.env.DEV && !import.meta.env.VITE_WEB_FLASHER_URL) {
                  fetch('http://localhost:5175', { method: 'HEAD', mode: 'no-cors' })
                    .then(() => {
                      window.open('http://localhost:5175', '_blank');
                    })
                    .catch(() => {
                      alert('Web Flasher dev server is not running.\n\nTo run it:\ncd frontend && pnpm dev:web-flasher\n\nOr use the production build at /flash');
                      window.open(webFlasherUrl, '_blank');
                    });
                } else {
                  window.open(webFlasherUrl, '_blank');
                }
              }}
            >
              <Globe className="w-4 h-4 sm:w-5 sm:h-5 mr-2" />
              <span className="text-sm sm:text-base">Flash Online</span>
              <ArrowRight className="w-3 h-3 sm:w-4 sm:h-4 ml-2" />
            </Button>
          </motion.div>
        </motion.div>
      </section>

      {/* Features Grid */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 md:py-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-6xl mx-auto">
          {[
            {
              icon: Smartphone,
              title: 'Device Detection',
              description: 'Automatically detect and identify Pixel devices via ADB/Fastboot',
            },
            {
              icon: Shield,
              title: 'Safe Flashing',
              description: 'Built-in safety gates with typed confirmations and dry-run mode',
            },
            {
              icon: Zap,
              title: 'Live Logging',
              description: 'Real-time streaming logs with SSE for complete transparency',
            },
          ].map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + index * 0.1 }}
              whileHover={{ scale: 1.05, y: -5 }}
            >
              <Card className="h-full backdrop-blur-sm bg-card/80 border-border/50">
                <CardContent className="p-4 sm:p-6">
                  <feature.icon className="w-8 h-8 sm:w-10 sm:h-10 mb-3 sm:mb-4 text-primary" />
                  <h3 className="text-lg sm:text-xl font-semibold mb-2">{feature.title}</h3>
                  <p className="text-sm sm:text-base text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Demo CTA */}
      <section className="container mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 md:py-20">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="max-w-2xl mx-auto text-center"
        >
          <Card className="backdrop-blur-sm bg-card/80 border-border/50">
            <CardContent className="p-6 sm:p-8">
              <h2 className="text-2xl sm:text-3xl font-bold mb-3 sm:mb-4">Try the Demo</h2>
              <p className="text-sm sm:text-base text-muted-foreground mb-4 sm:mb-6">
                Explore the dashboard interface with mocked data. No device required.
              </p>
              <Button
                size="lg"
                variant="outline"
                className="w-full sm:w-auto"
                onClick={() => navigate('/demo')}
              >
                <span className="text-sm sm:text-base">View Demo Dashboard</span>
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </section>
    </div>
  );
}

