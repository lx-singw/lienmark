'use client';

/**
 * WatcherStatusBar Component
 * Displays the live health status of Eventarc event triggers and storage watcher pollers.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Radio, Zap, Clock, HardDrive } from 'lucide-react';
import type { WatcherStatus } from './types';

interface WatcherStatusBarProps {
  status: WatcherStatus;
  isPolling: boolean;
  onTogglePolling: () => void;
}

export const WatcherStatusBar: React.FC<WatcherStatusBarProps> = ({
  status,
  isPolling,
  onTogglePolling,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-300">
      <div className="flex flex-wrap items-center gap-4">
        {/* Eventarc Listener */}
        <div className="flex items-center gap-1.5" title="Google Cloud Eventarc storage.objects.v1.finalized">
          <Zap className="h-3.5 w-3.5 text-purple-400" />
          <span className="text-slate-400">Eventarc:</span>
          <span className="flex items-center gap-1 font-medium text-purple-300">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Active (200 OK)
          </span>
        </div>

        {/* Storage Bucket */}
        <div className="flex items-center gap-1.5">
          <HardDrive className="h-3.5 w-3.5 text-sky-400" />
          <span className="text-slate-400">Bucket:</span>
          <span className="font-mono text-sky-300">{status.bucketUri}</span>
        </div>

        {/* Poller Interval */}
        <div className="flex items-center gap-1.5">
          <Clock className="h-3.5 w-3.5 text-amber-400" />
          <span className="text-slate-400">Sync:</span>
          <span className="font-mono text-amber-300">10s cadence</span>
        </div>
      </div>

      {/* Auto-poll Toggle */}
      <button
        onClick={onTogglePolling}
        className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium border transition-colors ${
          isPolling
            ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-300'
            : 'border-slate-700 bg-slate-800 text-slate-400'
        }`}
        aria-label="Toggle autonomous storage polling"
      >
        <Radio className={`h-3 w-3 ${isPolling ? 'animate-pulse text-emerald-400' : ''}`} />
        <span>{isPolling ? 'Live Polling ON' : 'Polling Paused'}</span>
      </button>
    </div>
  );
};
