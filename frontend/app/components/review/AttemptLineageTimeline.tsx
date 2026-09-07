'use client';

/**
 * Lienmark Attempt Lineage Timeline Component (Sprint 4.3)
 * Renders visual comparison drawer tracking Attempt 1 (Rejected with counsel directive quote)
 * to Attempt 2 (Active Re-investigation / Revised Finding).
 * Authored strictly under Google AntiGravity: zero-any TypeScript, files <= 250 lines, functions <= 40 lines.
 */

import React from 'react';
import {
  GitCommit,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Quote,
  Search,
  UserCheck,
  ArrowDown,
  Layers,
} from 'lucide-react';
import { AttemptLineageItem, AttemptLineageTimelineProps } from './review_types';
import { formatAttemptBadge, formatReviewTimestamp } from './review_utils';

export const AttemptLineageTimeline: React.FC<AttemptLineageTimelineProps> = ({
  attempts,
  claimKey,
  className = '',
  activeAttemptNumber,
}) => {
  if (!attempts || attempts.length === 0) {
    return (
      <div className={`rounded-lg border border-slate-800 bg-slate-950/40 p-4 text-center text-xs text-slate-400 ${className}`}>
        No prior counsel review attempts recorded for this claim.
      </div>
    );
  }

  return (
    <div className={`space-y-4 rounded-xl border border-slate-800 bg-[#0c1322] p-4 shadow-lg ${className}`}>
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-amber-400" aria-hidden="true" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Clearance Investigation Lineage & Directive Timeline
          </h4>
        </div>
        {claimKey && (
          <span className="font-mono text-[10px] text-slate-400">
            Asset: <span className="text-sky-300">{claimKey}</span>
          </span>
        )}
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
        {attempts.map((item, index) => {
          const badge = formatAttemptBadge(item.attemptNumber, item.action);
          const isLatest = index === attempts.length - 1;
          const isActive = activeAttemptNumber === item.attemptNumber;

          return (
            <div key={`${item.attemptNumber}-${item.timestamp}`} className="relative group">
              {/* Timeline Connector Dot */}
              <div
                className={`absolute -left-6 top-1.5 flex h-5 w-5 items-center justify-center rounded-full border text-[10px] font-bold ${
                  item.action === 'reject'
                    ? 'border-rose-500 bg-rose-950 text-rose-300'
                    : item.action === 'sign_off'
                    ? 'border-emerald-500 bg-emerald-950 text-emerald-300'
                    : 'border-amber-500 bg-amber-950 text-amber-300 animate-pulse'
                }`}
              >
                {item.action === 'reject' ? (
                  <AlertTriangle className="h-2.5 w-2.5" />
                ) : item.action === 'sign_off' ? (
                  <CheckCircle2 className="h-2.5 w-2.5" />
                ) : (
                  <Clock className="h-2.5 w-2.5" />
                )}
              </div>

              {/* Attempt Card */}
              <div
                className={`rounded-lg border p-3.5 transition-all ${
                  isActive || isLatest
                    ? 'border-slate-700 bg-slate-900/90 shadow-md ring-1 ring-sky-500/30'
                    : 'border-slate-800/80 bg-slate-950/60'
                }`}
              >
                {/* Header info */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className={`rounded border px-2 py-0.5 font-mono text-[10px] font-bold ${badge.badgeClass}`}>
                      {badge.label}
                    </span>
                    <span className="flex items-center gap-1 font-mono text-[11px] text-slate-300">
                      <UserCheck className="h-3 w-3 text-sky-400" />
                      {item.counselName}
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-slate-500">
                    {formatReviewTimestamp(item.timestamp)}
                  </span>
                </div>

                {/* Directive Quote (Especially prominent on Rejections) */}
                {item.directiveText && (
                  <div className="mt-2.5 rounded border border-amber-500/20 bg-amber-950/30 p-2 text-xs">
                    <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold uppercase text-amber-300">
                      <Quote className="h-3 w-3 text-amber-400 flex-shrink-0" />
                      <span>Counsel Re-investigation Directive:</span>
                    </div>
                    <p className="mt-1 font-serif italic text-amber-100/90 text-xs pl-4 border-l border-amber-500/40">
                      "{item.directiveText}"
                    </p>
                  </div>
                )}

                {/* Evidence / Finding Summary */}
                {(item.finding || item.evidenceSummary) && (
                  <div className="mt-2 space-y-1 text-xs">
                    {item.finding && (
                      <div className="font-mono text-[11px] text-slate-200">
                        <span className="text-slate-400">Finding:</span> {item.finding}
                      </div>
                    )}
                    {item.evidenceSummary && (
                      <div className="flex items-start gap-1 text-[11px] text-slate-400">
                        <Search className="h-3 w-3 text-sky-400 mt-0.5 flex-shrink-0" />
                        <span>{item.evidenceSummary}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Intermediate Arrow indicator between attempts */}
              {!isLatest && (
                <div className="flex justify-center my-1 text-slate-600">
                  <ArrowDown className="h-3 w-3 animate-bounce" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AttemptLineageTimeline;
