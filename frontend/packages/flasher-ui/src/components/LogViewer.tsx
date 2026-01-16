/**
 * Log Viewer - Shows flash logs/output
 * Google Pixel Web Flasher style
 */

import React, { useEffect, useRef } from 'react';

export interface LogEntry {
  message: string;
  level?: 'info' | 'warning' | 'error';
  timestamp?: Date;
}

export interface LogViewerProps {
  logs: LogEntry[];
  maxLines?: number;
  autoScroll?: boolean;
}

export function LogViewer({
  logs,
  maxLines = 100,
  autoScroll = true,
}: LogViewerProps) {
  const logEndRef = useRef<HTMLDivElement>(null);
  const displayLogs = logs.slice(-maxLines);

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const getLogColor = (level?: string) => {
    switch (level) {
      case 'error':
        return 'text-red-600';
      case 'warning':
        return 'text-yellow-600';
      default:
        return 'text-gray-700';
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-700 p-4 max-h-96 overflow-y-auto font-mono text-sm">
      <div className="space-y-1">
        {displayLogs.map((log, index) => (
          <div key={index} className={getLogColor(log.level)}>
            {log.timestamp && (
              <span className="text-gray-500 mr-2">
                {log.timestamp.toLocaleTimeString()}
              </span>
            )}
            <span>{log.message}</span>
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}

