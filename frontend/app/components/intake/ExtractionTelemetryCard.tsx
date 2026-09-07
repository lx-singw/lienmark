'use client';

/**
 * Lienmark Extraction Telemetry HUD Ribbon
 * Displays elapsed processing time, live Gemini token volume, discovered claims, and progress bar.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Clock, Cpu, FileText, CheckCircle2 } from 'lucide-react';
import { ExtractionTelemetryCardProps } from './types';
import { formatElapsedTime, formatTokenCount } from './intake_utils';

export const ExtractionTelemetryCard: React.FC<ExtractionTelemetryCardProps> = ({
  elapsedSeconds,
  totalTokens,
  claimsCount,
  backgroundClaimsCount,
  overallProgress,
  className = '',
}) => {
  const boundedProgress = Math.min(100, Math.max(0, Math.round(overallProgress)));

  return (
    <div
      className={`rounded-lg border border-slate-800 bg-[#080e1a] p-3.5 space-y-3 ${className}`}
      role="region"
      aria-label="Intake Pipeline Telemetry HUD"
    >
      {/* 3-Metric Tiles Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {/* Metric 1: Elapsed Duration */}
        <div className="rounded-md border border-slate-800/80 bg-slate-900/60 p-2.5 flex items-center gap-2.5">
          <div className="p-2 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 flex-shrink-0">
            <Clock className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              Elapsed Time
            </div>
            <div className="text-sm font-mono font-bold text-white tracking-tight">
              {formatElapsedTime(elapsedSeconds)}
            </div>
          </div>
        </div>

        {/* Metric 2: Live Token Processing Count */}
        <div className="rounded-md border border-slate-800/80 bg-slate-900/60 p-2.5 flex items-center gap-2.5">
          <div className="p-2 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 flex-shrink-0">
            <Cpu className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              Gemini 2.5 Tokens
            </div>
            <div className="text-sm font-mono font-bold text-purple-200 tracking-tight">
              {formatTokenCount(totalTokens)}
            </div>
          </div>
        </div>

        {/* Metric 3: Discovered Claims (Primary & Reflection) */}
        <div className="rounded-md border border-slate-800/80 bg-slate-900/60 p-2.5 flex items-center gap-2.5">
          <div className="p-2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex-shrink-0">
            <FileText className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              Extracted Claims
            </div>
            <div className="text-sm font-mono font-bold text-emerald-200 tracking-tight flex items-center gap-1.5">
              <span>{claimsCount} claims</span>
              {backgroundClaimsCount > 0 && (
                <span className="text-[10px] text-emerald-400 font-normal">
                  ({backgroundClaimsCount} bg)
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Metric 4: High-Contrast Progress Bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-slate-400 flex items-center gap-1.5">
            {boundedProgress === 100 ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                <span className="text-emerald-300 font-semibold">Baseline Locked</span>
              </>
            ) : (
              <span>Extraction Progress</span>
            )}
          </span>
          <span className="font-bold text-sky-400">{boundedProgress}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-sky-500 via-cyan-400 to-emerald-400 transition-all duration-300 shadow-sm"
            style={{ width: `${boundedProgress}%` }}
            role="progressbar"
            aria-valuenow={boundedProgress}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>
    </div>
  );
};

export default ExtractionTelemetryCard;
