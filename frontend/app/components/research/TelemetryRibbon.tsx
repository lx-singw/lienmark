'use client';

/**
 * TelemetryRibbon.tsx
 * Telemetry ribbon and inverse steering indicator for clearance research modal.
 * Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Gauge, Layers, Database, Compass } from 'lucide-react';
import type { SearchExecutionTelemetry } from './types';
import {
  formatLatency,
  getLatencyBadgeColor,
  getHttpStatusBadgeStyle,
} from './research_utils';

export interface TelemetryRibbonProps {
  readonly telemetry: SearchExecutionTelemetry;
}

interface LatencyPillProps {
  readonly latencyMs: number;
}

const LatencyPill: React.FC<LatencyPillProps> = ({ latencyMs }) => {
  const style = getLatencyBadgeColor(latencyMs);
  const percent = Math.min(100, Math.round((latencyMs / 2000) * 100));
  return (
    <div className="flex flex-col space-y-1">
      <div className="flex items-center justify-between text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
        <span className="flex items-center space-x-1">
          <Gauge className="w-3 h-3 text-cyan-400" />
          <span>Latency</span>
        </span>
        <span className={style.text}>{style.label}</span>
      </div>
      <div className="flex items-center space-x-2">
        <span className={`font-mono font-bold ${style.text}`}>
          {formatLatency(latencyMs)}
        </span>
        <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              latencyMs < 300
                ? 'bg-emerald-400'
                : latencyMs < 1000
                ? 'bg-amber-400'
                : 'bg-rose-400'
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>
    </div>
  );
};

interface StatsGridProps {
  readonly telemetry: SearchExecutionTelemetry;
}

const TelemetryStatsGrid: React.FC<StatsGridProps> = ({ telemetry }) => {
  const httpStyle = getHttpStatusBadgeStyle(telemetry.http_status);
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-cinema-black/60 border border-slate-800 text-xs">
      <div className="flex flex-col space-y-1">
        <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
          HTTP Status
        </span>
        <span
          className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded font-mono font-bold w-fit border ${httpStyle.bg} ${httpStyle.border} ${httpStyle.text}`}
        >
          <span>{httpStyle.label}</span>
        </span>
      </div>

      <LatencyPill latencyMs={telemetry.latency_ms} />

      <div className="flex flex-col space-y-1">
        <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
          Results Yield
        </span>
        <span className="inline-flex items-center space-x-1 text-slate-100 font-semibold">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>{telemetry.result_count} Findings</span>
        </span>
      </div>

      <div className="flex flex-col space-y-1">
        <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">
          Execution Mode
        </span>
        <span className="inline-flex items-center space-x-1 text-slate-300">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span>{telemetry.cache_hit ? 'Cached Replay' : 'Parallel API Live'}</span>
        </span>
      </div>
    </div>
  );
};

interface SteeringBannerProps {
  readonly reason?: string;
}

const SteeringAlertBanner: React.FC<SteeringBannerProps> = ({ reason }) => (
  <div className="flex items-start space-x-3 p-3.5 rounded-xl bg-gradient-to-r from-amber-950/50 via-purple-950/30 to-amber-950/50 border border-amber-500/40 shadow-lg">
    <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-300 shrink-0 mt-0.5">
      <Compass
        className="w-4 h-4 animate-spin"
        style={{ animationDuration: '8s' }}
      />
    </div>
    <div className="flex-1 text-xs">
      <div className="flex items-center space-x-2">
        <span className="font-bold text-amber-300 uppercase tracking-wider text-[11px]">
          Inverse Domain Steering Triggered
        </span>
        <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-500/20 text-amber-200 font-mono">
          Fallback Mode Active
        </span>
      </div>
      <p className="mt-1 text-slate-300 leading-relaxed text-[11px]">
        {reason ||
          'Strict registry queries returned 0 results. Domain constraints stripped and negative keyword filters (-lyrics -chords -youtube -spotify) applied to isolate rights ownership catalogs.'}
      </p>
    </div>
  </div>
);

export const TelemetryRibbon: React.FC<TelemetryRibbonProps> = ({
  telemetry,
}) => (
  <div className="space-y-3">
    <TelemetryStatsGrid telemetry={telemetry} />
    {telemetry.is_inverse_steering && (
      <SteeringAlertBanner reason={telemetry.inverse_reason} />
    )}
  </div>
);

export default TelemetryRibbon;
