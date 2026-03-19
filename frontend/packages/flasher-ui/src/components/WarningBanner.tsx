/**
 * Warning Banner - "Do not disconnect device" warning
 * Google Pixel Web Flasher style
 */

import React from 'react';

export interface WarningBannerProps {
  message?: string;
  show: boolean;
  variant?: 'warning' | 'error' | 'info';
}

export function WarningBanner({
  message = '⚠️ Do not disconnect your device',
  show,
  variant = 'warning',
}: WarningBannerProps) {
  if (!show) return null;

  const variantStyles = {
    warning: 'bg-orange-50 border-orange-200 text-orange-800',
    error: 'bg-red-50 border-red-200 text-red-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  };

  return (
    <div className={`border-2 rounded-lg p-4 mb-4 ${variantStyles[variant]}`}>
      <div className="flex items-center">
        <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
        <span className="font-medium">{message}</span>
      </div>
    </div>
  );
}

