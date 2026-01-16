import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Suppress known Chrome extension errors (these don't affect the app functionality)
if (typeof window !== 'undefined') {
  const originalError = console.error;
  const originalWarn = console.warn;
  
  const shouldSuppressError = (message: string, error?: any): boolean => {
    const suppressedPatterns = [
      /No checkout popup config found/i,
      /message port closed before a response was received/i,
      /message channel closed before a response was received/i,
      /csspeeper-inspector-tools/i,
      /chrome\.tabs\.getSelected is not a function/i,
      /Ad unit initialization failed/i,
      /runtime\.lastError/i,
      /Error handling response/i,
      /chrome-extension:\/\/.*app\.bundle\.js/i,
      /installHook\.js/i,
      /React Router Future Flag Warning/i, // Suppress React Router warnings (if using Router elsewhere)
      /v7_startTransition/i,
      /v7_relativeSplatPath/i,
    ];
    
    // Check message string
    if (suppressedPatterns.some(pattern => pattern.test(message))) {
      return true;
    }
    
    // Check error stack traces
    if (error && typeof error === 'object') {
      const errorString = String(error) + (error.stack || '') + (error.message || '');
      if (suppressedPatterns.some(pattern => pattern.test(errorString))) {
        return true;
      }
    }
    
    return false;
  };
  
  console.error = (...args: any[]) => {
    const message = args.join(' ');
    const error = args.find(arg => arg instanceof Error || (typeof arg === 'object' && arg?.stack));
    if (!shouldSuppressError(message, error)) {
      originalError.apply(console, args);
    }
  };
  
  console.warn = (...args: any[]) => {
    const message = args.join(' ');
    const error = args.find(arg => arg instanceof Error || (typeof arg === 'object' && arg?.stack));
    if (!shouldSuppressError(message, error)) {
      originalWarn.apply(console, args);
    }
  };
  
  // Suppress unhandled promise rejections from extensions
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const reasonString = String(reason) + (reason?.stack || '') + (reason?.message || '');
    const message = reasonString + ' ' + (event.reason?.toString() || '');
    
    if (shouldSuppressError(message, reason)) {
      event.preventDefault(); // Suppress the error
      return;
    }
  });
  
  // Suppress global errors from extensions
  window.addEventListener('error', (event) => {
    const errorString = (event.message || '') + ' ' + (event.filename || '') + ' ' + (event.error?.stack || '');
    
    if (shouldSuppressError(errorString, event.error)) {
      event.preventDefault(); // Suppress the error
      return;
    }
  }, true); // Use capture phase to catch errors early
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

