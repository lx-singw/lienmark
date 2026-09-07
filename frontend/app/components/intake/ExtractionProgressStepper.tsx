'use client';

/**
 * Lienmark Extraction Progress Stepper Component
 * Real-time 4-stage stepper tracking screenplay AST parsing, Gemini 2.5 Flash multimodal extraction,
 * self-reflection verification pass, and confidentiality trimming with immutable baseline snapshot.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Layers, CheckCircle2, RotateCw, ShieldCheck } from 'lucide-react';
import {
  ExtractionProgressStepperProps,
  StageStatus,
  StageTelemetry,
} from './types';
import { EXTRACTION_STAGES } from './intake_utils';
import { ExtractionTelemetryCard } from './ExtractionTelemetryCard';
import { ExtractionStageItem } from './ExtractionStageItem';

export const ExtractionProgressStepper: React.FC<ExtractionProgressStepperProps> = ({
  progressData,
  onRetry,
  onViewBaseline,
  className = '',
}) => {
  const isCompleted = progressData.overallStatus === StageStatus.COMPLETED;
  const isFailed = progressData.overallStatus === StageStatus.FAILED;

  return (
    <section
      aria-label="Screenplay Multimodal Intake Extraction Stepper"
      className={`rounded-xl border border-slate-800 bg-[#0b1220] p-4 md:p-5 shadow-2xl space-y-4 ${className}`}
    >
      {/* Stepper Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30">
            <Layers className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <span>Multimodal Intake Pipeline</span>
              <span className="font-mono text-[10px] bg-slate-800 text-sky-300 px-1.5 py-0.5 rounded border border-slate-700 font-semibold">
                {progressData.documentName || 'Screenplay Cut'}
              </span>
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Milestone Baseline Extraction &middot; Gemini 2.5 Flash GenAI ADK
            </p>
          </div>
        </div>

        {/* Global Action Status */}
        <div className="flex items-center gap-2">
          {isFailed && onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-semibold text-rose-200 bg-rose-950/80 border border-rose-500/50 rounded-lg hover:bg-rose-900/80 transition-colors"
            >
              <RotateCw className="h-3.5 w-3.5" />
              <span>Retry Extraction</span>
            </button>
          )}
          {isCompleted && progressData.baselineSnapshotKey && onViewBaseline && (
            <button
              type="button"
              onClick={() => onViewBaseline(progressData.baselineSnapshotKey!)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-bold text-emerald-200 bg-emerald-950/90 border border-emerald-500/60 rounded-lg hover:bg-emerald-900 transition-colors shadow-sm"
            >
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>Inspect Baseline Claims</span>
            </button>
          )}
        </div>
      </div>

      {/* 4-Tile Telemetry HUD Ribbon */}
      <ExtractionTelemetryCard
        elapsedSeconds={progressData.elapsedSeconds}
        totalTokens={progressData.totalTokensProcessed}
        claimsCount={progressData.totalClaimsExtracted}
        backgroundClaimsCount={progressData.backgroundClaimsCount}
        overallProgress={progressData.overallProgress}
      />

      {/* 4-Stage Vertical Stepper Stack */}
      <div className="space-y-2.5" role="list" aria-label="Extraction Pipeline Stages">
        {EXTRACTION_STAGES.map((stage, idx) => {
          const telemetry: StageTelemetry = progressData.stageDetails[stage.id] ?? {
            stageId: stage.id,
            status: StageStatus.PENDING,
            progressPercent: 0,
            elapsedMs: 0,
            tokensProcessed: 0,
            claimsDiscovered: 0,
            currentAction: 'Queued',
          };
          const isActive = progressData.activeStageId === stage.id;
          const isLast = idx === EXTRACTION_STAGES.length - 1;

          return (
            <ExtractionStageItem
              key={stage.id}
              stage={stage}
              telemetry={telemetry}
              isActive={isActive}
              isLast={isLast}
            />
          );
        })}
      </div>

      {/* Baseline Immutable Snapshot Verification Banner */}
      {isCompleted && progressData.baselineSnapshotKey && (
        <div
          className="rounded-lg border border-emerald-500/40 bg-emerald-950/30 p-3 flex items-start gap-2.5 text-xs text-emerald-200 shadow-md animate-in fade-in"
          role="status"
          aria-live="polite"
        >
          <ShieldCheck className="h-4 w-4 text-emerald-400 mt-0.5 flex-shrink-0" />
          <div className="space-y-0.5">
            <div className="font-bold text-emerald-300">
              Immutable Baseline Snapshot Locked
            </div>
            <p className="text-[11px] text-emerald-200/90 font-mono">
              Snapshot Hash:{' '}
              <span className="text-white font-bold">{progressData.baselineSnapshotKey}</span>{' '}
              &middot; All extracted claims stripped of narrative spoilers and ready for matrix review.
            </p>
          </div>
        </div>
      )}
    </section>
  );
};

export default ExtractionProgressStepper;
