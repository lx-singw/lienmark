'use client';

/**
 * OfflineConnectivityBanner Component
 * Floating glassmorphism banner warning users during network partitions
 * and celebrating seamless SSE state recovery.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState } from 'react';
import {
  WifiOff,
  Wifi,
  RefreshCw,
  CheckCircle2,
  Radio,
  Clock,
} from 'lucide-react';
import { OfflineConnectivityBannerProps } from './types';
import { useNetworkStatus } from './useNetworkStatus';

function renderDisconnectedContent(
  seconds: number,
  isRetrying: boolean,
  onRetry: () => void
): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-rose-500/20 border border-rose-500/40 text-rose-400 shrink-0 animate-pulse">
          <WifiOff className="h-4 w-4" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-xs font-bold font-mono uppercase tracking-wider text-white">
              OFFLINE MODE: LOCAL QUEUE ACTIVE
            </h4>
            <span className="flex items-center gap-1 rounded-full bg-rose-500/20 border border-rose-500/40 px-2 py-0.5 text-[10px] font-mono text-rose-300">
              <Clock className="h-2.5 w-2.5" /> {seconds}s
            </span>
          </div>
          <p className="text-[11px] text-slate-300 mt-0.5">
            Network partitioned. Local triage actions are preserved safely in memory.
          </p>
        </div>
      </div>

      <button
        type="button"
        disabled={isRetrying}
        onClick={onRetry}
        className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-700/80 hover:border-slate-500 px-3 py-1.5 text-xs font-mono font-semibold text-rose-300 hover:text-white transition-all shrink-0 disabled:opacity-50"
      >
        <RefreshCw className={`h-3 w-3 ${isRetrying ? 'animate-spin text-rose-400' : ''}`} />
        <span>{isRetrying ? 'Checking...' : 'Retry Link'}</span>
      </button>
    </div>
  );
}

function renderRestoredContent(): React.JSX.Element {
  return (
    <div className="flex items-center gap-3">
      <div className="p-2 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 shrink-0">
        <Wifi className="h-4 w-4" />
      </div>
      <div>
        <div className="flex items-center gap-2">
          <h4 className="text-xs font-bold font-mono uppercase tracking-wider text-white">
            CONNECTION RESTORED
          </h4>
          <span className="flex items-center gap-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-mono text-emerald-300">
            <CheckCircle2 className="h-2.5 w-2.5" /> Re-anchored
          </span>
        </div>
        <p className="text-[11px] text-slate-300 mt-0.5">
          Real-time clearance engine synchronized. Local actions dispatched to ledger.
        </p>
      </div>
    </div>
  );
}

export function OfflineConnectivityBanner({
  onRetry,
  className = '',
}: OfflineConnectivityBannerProps): React.JSX.Element | null {
  const { transition, offlineDurationSeconds, checkConnectivity } = useNetworkStatus();
  const [retrying, setRetrying] = useState<boolean>(false);

  if (transition === 'connected') return null;

  const handleManualRetry = async () => {
    setRetrying(true);
    try {
      if (onRetry) onRetry();
      await checkConnectivity();
    } finally {
      setTimeout(() => setRetrying(false), 500);
    }
  };

  const isRestored = transition === 'restored';
  const bannerStyles = isRestored
    ? 'border-emerald-500/60 bg-[#071710]/95 shadow-emerald-950/60 text-emerald-200'
    : 'border-rose-500/60 bg-[#17080e]/95 shadow-rose-950/60 text-rose-200';

  return (
    <aside
      role="status"
      aria-live="polite"
      className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 w-11/12 max-w-2xl rounded-2xl border p-3.5 backdrop-blur-xl shadow-2xl transition-all duration-300 animate-in fade-in slide-in-from-top-3 ${bannerStyles} ${className}`}
    >
      {isRestored
        ? renderRestoredContent()
        : renderDisconnectedContent(offlineDurationSeconds, retrying, handleManualRetry)}
    </aside>
  );
}

export default OfflineConnectivityBanner;
