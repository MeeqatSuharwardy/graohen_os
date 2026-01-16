/**
 * Flash Steps - Step-by-step wizard UI
 * Google Pixel Web Flasher style
 */

import React from 'react';
import type { FlashState } from '@flashdash/flasher';

export interface FlashStep {
  state: FlashState;
  label: string;
  description?: string;
}

export interface FlashStepsProps {
  currentState: FlashState;
  steps: FlashStep[];
}

export function FlashSteps({ currentState, steps }: FlashStepsProps) {
  const getStepStatus = (stepState: FlashState, currentState: FlashState) => {
    const stateOrder = [
      'idle',
      'device_connected',
      'build_selected',
      'downloading',
      'download_complete',
      'rebooting_to_bootloader',
      'fastboot_mode',
      'unlocking_bootloader',
      'flashing',
      'flash_complete',
      'rebooting',
      'complete',
    ];

    const currentIndex = stateOrder.indexOf(currentState);
    const stepIndex = stateOrder.indexOf(stepState);

    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">Flashing Progress</h3>
      <div className="space-y-4">
        {steps.map((step, index) => {
          const status = getStepStatus(step.state, currentState);
          const isActive = status === 'active';
          const isCompleted = status === 'completed';

          return (
            <div key={step.state} className="flex items-start">
              <div className="flex-shrink-0">
                {isCompleted ? (
                  <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                ) : isActive ? (
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
                    <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <span className="text-gray-500 text-sm font-medium">{index + 1}</span>
                  </div>
                )}
              </div>
              <div className={`ml-4 flex-1 ${isActive ? '' : 'opacity-60'}`}>
                <div className={`font-medium ${isActive ? 'text-blue-600' : 'text-gray-900'}`}>
                  {step.label}
                </div>
                {step.description && (
                  <div className="text-sm text-gray-500 mt-1">{step.description}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

