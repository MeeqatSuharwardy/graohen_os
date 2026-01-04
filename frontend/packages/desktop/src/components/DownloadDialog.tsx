import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@flashdash/ui';
import { Button } from '@flashdash/ui';
import { Progress } from '@flashdash/ui';
import { Badge } from '@flashdash/ui';
import { Alert, AlertDescription } from '@flashdash/ui';
import { Download, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { apiClient } from '../lib/api';

interface Release {
  version: string;
  url?: string;
  sha256?: string;
  size?: number;
  date?: string;
}

interface DownloadDialogProps {
  codename: string;
  deviceName?: string;
  trigger?: React.ReactNode;
}

export function DownloadDialog({ codename, deviceName, trigger }: DownloadDialogProps) {
  const [open, setOpen] = useState(false);
  const [releases, setReleases] = useState<Release[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadId, setDownloadId] = useState<string | null>(null);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [manualVersion, setManualVersion] = useState('');

  useEffect(() => {
    if (open && releases.length === 0) {
      fetchReleases();
    }
  }, [open, codename]);

  useEffect(() => {
    if (downloadId) {
      const interval = setInterval(async () => {
        try {
          const response = await apiClient.get(`/bundles/download/${downloadId}/status`);
          const status = response.data;
          
          if (status.status === 'downloading') {
            setDownloadProgress(status.progress || 0);
          } else if (status.status === 'completed') {
            setDownloadProgress(100);
            setDownloading(false);
            setDownloadId(null);
            clearInterval(interval);
          } else if (status.status === 'error') {
            setError(status.error || 'Download failed');
            setDownloading(false);
            setDownloadId(null);
            clearInterval(interval);
          }
        } catch (err: any) {
          setError(err.message || 'Failed to check download status');
          clearInterval(interval);
        }
      }, 500);

      return () => clearInterval(interval);
    }
  }, [downloadId]);

  const fetchReleases = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`/bundles/releases/${codename}`);
      setReleases(response.data.releases || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch releases');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (version: string) => {
    setDownloading(true);
    setError(null);
    setSelectedVersion(version);
    setDownloadProgress(0);

    try {
      const response = await apiClient.post('/bundles/download', {
        codename,
        version,
      });
      
      const downloadId = response.data.download_id;
      setDownloadId(downloadId);
    } catch (err: any) {
      setError(err.message || 'Failed to start download');
      setDownloading(false);
    }
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return 'Unknown size';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Download Build
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Download GrapheneOS Build</DialogTitle>
          <DialogDescription>
            {deviceName || codename} - Select a version to download
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {downloading && downloadId && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Downloading {selectedVersion}...</span>
                <span>{downloadProgress.toFixed(1)}%</span>
              </div>
              <Progress value={downloadProgress} />
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Enter Version</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={manualVersion}
                    onChange={(e) => setManualVersion(e.target.value)}
                    placeholder="e.g., 2024.01.15.12"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  />
                  <Button
                    onClick={() => {
                      if (manualVersion.trim()) {
                        handleDownload(manualVersion.trim());
                      }
                    }}
                    disabled={downloading || !manualVersion.trim()}
                  >
                    {downloading && selectedVersion === manualVersion ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Downloading...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4 mr-2" />
                        Download
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Enter the GrapheneOS version (e.g., 2024.01.15.12)
                </p>
              </div>

              {releases.length > 0 && (
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  <label className="text-sm font-medium">Available Releases</label>
                  {releases.map((release) => (
                    <div
                      key={release.version}
                      className="flex items-center justify-between p-3 rounded-lg border bg-card/50"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold">v{release.version}</span>
                          {release.size && (
                            <Badge variant="outline">{formatSize(release.size)}</Badge>
                          )}
                          {release.date && (
                            <span className="text-xs text-muted-foreground">{release.date}</span>
                          )}
                        </div>
                        {release.sha256 && (
                          <p className="text-xs font-mono text-muted-foreground truncate">
                            {release.sha256.substring(0, 16)}...
                          </p>
                        )}
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleDownload(release.version)}
                        disabled={downloading || (selectedVersion === release.version && downloading)}
                      >
                        {downloading && selectedVersion === release.version ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Downloading...
                          </>
                        ) : (
                          <>
                            <Download className="w-4 h-4 mr-2" />
                            Download
                          </>
                        )}
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {releases.map((release) => (
                <div
                  key={release.version}
                  className="flex items-center justify-between p-3 rounded-lg border bg-card/50"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold">v{release.version}</span>
                      {release.size && (
                        <Badge variant="outline">{formatSize(release.size)}</Badge>
                      )}
                      {release.date && (
                        <span className="text-xs text-muted-foreground">{release.date}</span>
                      )}
                    </div>
                    {release.sha256 && (
                      <p className="text-xs font-mono text-muted-foreground truncate">
                        {release.sha256.substring(0, 16)}...
                      </p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    onClick={() => handleDownload(release.version)}
                    disabled={downloading || (selectedVersion === release.version && downloading)}
                  >
                    {downloading && selectedVersion === release.version ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Downloading...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4 mr-2" />
                        Download
                      </>
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

