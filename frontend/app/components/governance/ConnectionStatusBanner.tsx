'use client';

/**
 * ConnectionStatusBanner.tsx
 * Fail-closed glassmorphism status banner alerting when backend is unavailable or stale.
 * Invariant: Files <= 250 lines, functions <= 40 lines, strict TypeScript, Tailwind CSS, Lucide icons.
 */

import React from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  RefreshCw,
  WifiOff,
  Database,
  Lock,
} from 'lucide-react';
import { ConnectionState } from '@/lib/types';

export interface ConnectionStatusBannerProps {
  readonly connectionState: ConnectionState;
  readonly onRetry: () => void | Promise<void>;
  readonly isRetrying?: boolean;
  readonly errorMessage?: string | null;
}

export const ConnectionStatusBanner: React.FC<ConnectionStatusBannerProps> = ({
  connectionState,
  onRetry,
  isRetrying = false,
  errorMessage,
}) => {
  if (connectionState !== 'unavailable' && connectionState !== 'stale') {
    return null;
  }

  const isUnavailable = connectionState === 'unavailable';

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`relative overflow-hidden rounded-2xl border p-4 sm:p-5 backdrop-blur-md shadow-2xl transition-all duration-300 animate-in fade-in slide-in-from-top-2 ${
        isUnavailable
          ? 'border-rose-500/50 bg-gradient-to-r from-rose-950/85 via-[#1a0f18]/90 to-slate-950/85 shadow-rose-950/30 text-rose-200'
          : 'border-amber-500/50 bg-gradient-to-r from-amber-950/85 via-[#1c160c]/90 to-slate-950/85 shadow-amber-950/30 text-amber-200'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div
            className={`p-2.5 rounded-xl border flex-shrink-0 mt-0.5 ${
              isUnavailable
                ? 'bg-rose-500/20 border-rose-500/40 text-rose-400'
                : 'bg-amber-500/20 border-amber-500/40 text-amber-400'
            }`}
          >
            {isUnavailable ? (
              <WifiOff className="h-6 w-6 animate-pulse" aria-hidden="true" />
            ) : (
              <Database className="h-6 w-6" aria-hidden="true" />
            )}
          </div>

          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`text-[10px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded border ${
                  isUnavailable
                    ? 'bg-rose-900/60 border-rose-500/40 text-rose-300'
                    : 'bg-amber-900/60 border-amber-500/40 text-amber-300'
                }`}
              >
                {isUnavailable ? 'FAIL-CLOSED: API OFFLINE' : 'DEGRADED: STALE SNAPSHOT'}
              </span>
              <span className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
                <Lock className="h-3 w-3" aria-hidden="true" />
                <span>Mutations Locked</span>
              </span>
            </div>

            <h3 className="text-base font-bold text-white tracking-wide">
              {isUnavailable
                ? 'Clearance Verification Backend Offline'
                : 'Displaying Stale Cached Snapshot'}
            </h3>

            <p className="text-xs sm:text-sm text-slate-300 max-w-3xl leading-relaxed">
              {isUnavailable
                ? 'The FastAPI clearance verification backend is currently unreachable. In accordance with fail-closed governance, all clearance decisions, re-attestations, and evaluations are strictly locked.'
                : 'The system is disconnected from the live backend and rendering a historical cached snapshot. Attestation mutations and E&O exception determinations are disabled until live connection is restored.'}
            </p>

            {errorMessage && (
              <div className="pt-1">
                <p className="text-[11px] font-mono text-slate-400 bg-slate-950/60 rounded px-2.5 py-1 border border-slate-800/80 inline-block truncate max-w-xl">
                  Details: {errorMessage}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 sm:self-center flex-shrink-0 pt-2 sm:pt-0">
          <button
            type="button"
            onClick={() => void onRetry()}
            disabled={isRetrying}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-950 transition-all shadow-lg active:scale-95 focus:outline-none focus:ring-2 disabled:opacity-60 disabled:cursor-not-allowed ${
              isUnavailable
                ? 'bg-rose-400 hover:bg-rose-300 focus:ring-rose-300 shadow-rose-950/40'
                : 'bg-amber-400 hover:bg-amber-300 focus:ring-amber-300 shadow-amber-950/40'
            }`}
            aria-label="Retry backend connection"
          >
            <RefreshCw
              className={`h-4 w-4 ${isRetrying ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
            <span>{isRetrying ? 'Retrying Connection...' : 'Retry Connection'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConnectionStatusBanner;
