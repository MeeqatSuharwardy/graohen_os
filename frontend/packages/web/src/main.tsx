import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import '@flashdash/ui/styles/globals.css';

// Suppress known Chrome extension errors and warnings
if (typeof window !== 'undefined') {
  const originalError = console.error;
  const originalWarn = console.warn;

  const suppressedPatterns = [
    /No checkout popup config found/i,
    /message port closed before a response was received/i,
    /csspeeper-inspector-tools/i,
    /chrome\.tabs\.getSelected is not a function/i,
    /Ad unit initialization failed/i,
    /runtime\.lastError/i,
    /Error handling response/i,
    /chrome-extension:\/\//i,
    /installHook\.js/i,
    /React Router Future Flag Warning/i,
    /v7_startTransition/i,
    /v7_relativeSplatPath/i,
  ];

  const shouldSuppress = (message: string, errorObj?: any): boolean => {
    if (suppressedPatterns.some(pattern => pattern.test(message))) {
      return true;
    }
    if (errorObj && errorObj.stack && suppressedPatterns.some(pattern => pattern.test(errorObj.stack))) {
      return true;
    }
    if (errorObj && errorObj.filename && suppressedPatterns.some(pattern => pattern.test(errorObj.filename))) {
      return true;
    }
    return false;
  };

  console.error = (...args: any[]) => {
    const message = args.map(arg => typeof arg === 'string' ? arg : String(arg)).join(' ');
    if (!shouldSuppress(message, args.find(arg => arg instanceof Error))) {
      originalError.apply(console, args);
    }
  };

  console.warn = (...args: any[]) => {
    const message = args.map(arg => typeof arg === 'string' ? arg : String(arg)).join(' ');
    if (!shouldSuppress(message, args.find(arg => arg instanceof Error))) {
      originalWarn.apply(console, args);
    }
  };

  // Suppress unhandled promise rejections from extensions
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const message = typeof reason === 'string' ? reason : (reason instanceof Error ? reason.message : String(reason));
    if (shouldSuppress(message, reason)) {
      event.preventDefault();
    }
  });

  // Suppress global error events from extensions
  window.addEventListener('error', (event) => {
    const message = event.message;
    if (shouldSuppress(message, event.error)) {
      event.preventDefault();
    }
  }, true);
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

