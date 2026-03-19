/**
 * useFlasher Hook - React hook for flash operations
 */

import { useState, useCallback } from 'react';
import { FlashExecutor } from '@flashdash/flasher';
import type { FlashOptions, FlashProgress } from '@flashdash/flasher';

export function useFlasher() {
  const [flashExecutor] = useState(() => new FlashExecutor());
  const [isFlashing, setIsFlashing] = useState(false);
  const [progress, setProgress] = useState<FlashProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startFlash = useCallback(
    async (options: FlashOptions) => {
      try {
        setError(null);
        setIsFlashing(true);
        setProgress(null);

        const progressCallback = (prog: FlashProgress) => {
          setProgress(prog);
          options.onProgress?.(prog);
        };

        await flashExecutor.startFlash({
          ...options,
          onProgress: progressCallback,
        });
      } catch (err: any) {
        setError(err.message || 'Flash operation failed');
        setIsFlashing(false);
      } finally {
        setIsFlashing(false);
      }
    },
    [flashExecutor]
  );

  const cancelFlash = useCallback(() => {
    flashExecutor.cancel();
    setIsFlashing(false);
    setError('Flash operation cancelled');
  }, [flashExecutor]);

  return {
    isFlashing,
    progress,
    error,
    startFlash,
    cancelFlash,
    stateMachine: flashExecutor.getStateMachine(),
  };
}

