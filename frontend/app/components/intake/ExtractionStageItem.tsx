'use client';

/**
 * Lienmark Extraction Stage Item Component
 * Renders an individual pipeline stage row with status icons, elapsed time, and micro-progress.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  FileCode2,
  Sparkles,
  ScanEye,
  ShieldCheck,
  Check,
  Loader2,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { ExtractionStageItemProps, StageStatus } from './types';
import { getStageTheme, formatElapsedTime, formatTokenCount } from './intake_utils';

function renderStageIcon(iconName: string, isCompleted: boolean) {
  if (isCompleted) {
    return <Check className="h-4 w-4 text-emerald-400" aria-hidden="true" />;
  }
  switch (iconName) {
    case 'FileCode2':
      return <FileCode2 className="h-4 w-4" aria-hidden="true" />;
    case 'Sparkles':
      return <Sparkles className="h-4 w-4" aria-hidden="true" />;
    case 'ScanEye':
      return <ScanEye className="h-4 w-4" aria-hidden="true" />;
    case 'ShieldCheck':
      return <ShieldCheck className="h-4 w-4" aria-hidden="true" />;
    default:
      return <FileCode2 className="h-4 w-4" aria-hidden="true" />;
  }
}

export const ExtractionStageItem: React.FC<ExtractionStageItemProps> = ({
  stage,
  telemetry,
  isActive,
  isLast,
}) => {
  const isCompleted = telemetry.status === StageStatus.COMPLETED;
  const isFailed = telemetry.status === StageStatus.FAILED;
  const theme = getStageTheme(telemetry.status);

  return (
    <div
      className={`relative rounded-lg border p-3 transition-all ${
        isActive
          ? 'bg-[#111c33] border-sky-500/70 shadow-lg shadow-sky-950/40 ring-1 ring-sky-500/30'
          : isCompleted
          ? 'bg-[#0d1627] border-slate-800'
          : 'bg-[#090f1d] border-slate-800/60 opacity-80'
      }`}
      role="listitem"
      aria-label={`Stage ${stage.stageNumber}: ${stage.title} - ${telemetry.status}`}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left: Icon & Stage Metadata */}
        <div className="flex items-start gap-3 min-w-0">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-lg border flex-shrink-0 mt-0.5 ${
              isCompleted
                ? 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40'
                : isActive
                ? 'bg-sky-500/20 text-sky-300 border-sky-500/50 ring-2 ring-sky-500/20 animate-pulse'
                : 'bg-slate-900 text-slate-500 border-slate-800'
            }`}
          >
            {renderStageIcon(stage.iconName, isCompleted)}
          </div>

          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold text-white tracking-tight font-mono">
                Stage {stage.stageNumber}: {stage.title}
              </span>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-800/80 px-1.5 py-0.2 rounded border border-slate-700/60">
                {stage.modelSubtitle}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 line-clamp-1 font-sans">
              {isActive && telemetry.currentAction ? telemetry.currentAction : stage.description}
            </p>
          </div>
        </div>

        {/* Right: Stage Status & Latency Badge */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isActive && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold text-sky-300 bg-sky-950/80 border border-sky-500/40 px-2 py-0.5 rounded">
              <Loader2 className="h-3 w-3 animate-spin text-sky-400" />
              <span>ACTIVE</span>
            </span>
          )}
          {isCompleted && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-emerald-300 bg-emerald-950/80 border border-emerald-500/40 px-2 py-0.5 rounded">
              <Check className="h-3 w-3 text-emerald-400" />
              <span>DONE ({formatElapsedTime(telemetry.elapsedMs / 1000)})</span>
            </span>
          )}
          {isFailed && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold text-rose-300 bg-rose-950/80 border border-rose-500/50 px-2 py-0.5 rounded">
              <AlertCircle className="h-3 w-3 text-rose-400" />
              <span>FAILED</span>
            </span>
          )}
        </div>
      </div>

      {/* Sub-Progress Bar for Active Stage */}
      {isActive && (
        <div className="mt-2.5 space-y-1">
          <div className="flex justify-between text-[10px] font-mono text-slate-400">
            <span className="text-sky-300 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{formatElapsedTime(telemetry.elapsedMs / 1000)}</span>
            </span>
            {telemetry.tokensProcessed > 0 && (
              <span>{formatTokenCount(telemetry.tokensProcessed)}</span>
            )}
            <span className="text-sky-400 font-bold">{telemetry.progressPercent}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-slate-800/90 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-sky-500 to-cyan-300 transition-all duration-200"
              style={{ width: `${telemetry.progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Message for Failed Stage */}
      {isFailed && telemetry.errorMessage && (
        <div className="mt-2 p-2 rounded bg-rose-950/60 border border-rose-500/40 text-[11px] font-mono text-rose-200">
          Error: {telemetry.errorMessage}
        </div>
      )}
    </div>
  );
};

export default ExtractionStageItem;
