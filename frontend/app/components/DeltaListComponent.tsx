'use client';

/**
 * Lienmark Script Cut v7 -> v8 Delta Breakdown List
 * Visual breakdown of detected differences between v7 and v8.
 * Highlights Item 11 (Scene 42 poster) and Item 12 (Scene 18 jazz cue),
 * displaying scene timecodes, prominence shifts, and direct 'Inspect' actions.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  GitCompare,
  AlertTriangle,
  Clock,
  ArrowRight,
  Eye,
  CheckCircle2,
  AlertOctagon,
  Sparkles,
} from 'lucide-react';
import { DecisionState, ReviewQueueItem } from '@/lib/types';

export interface DeltaListComponentProps {
  items: ReadonlyArray<ReviewQueueItem>;
  selectedQueueKey: string;
  onSelectQueueItem: (key: string) => void;
  onInspectItem?: (key: string) => void;
}

export const DeltaListComponent: React.FC<DeltaListComponentProps> = ({
  items,
  selectedQueueKey,
  onSelectQueueItem,
  onInspectItem,
}) => {
  return (
    <section aria-label="Script Revision Delta Differences" className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCompare className="h-4 w-4 text-amber-400" aria-hidden="true" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Script Revision Delta Breakdown (v7 Locked &rarr; v8 Revised)
          </h3>
        </div>
        <span className="text-xs font-mono text-slate-400">
          2 Material Invalidation Deltas Detected
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map((item) => {
          const isSelected = item.stable_lineage_key === selectedQueueKey;
          const isItem11 = item.stable_lineage_key === 'poster_noir_detective_magazine';
          const isItem12 = item.stable_lineage_key === 'music_cue_midnight_serenade';

          const itemNumber = isItem11 ? '#11' : isItem12 ? '#12' : '#--';
          const timecode = isItem11 ? '00:44:12' : isItem12 ? '00:19:40' : item.scene;
          const shiftSummary = isItem11
            ? '2s background blur → 14s close-up focal dialogue'
            : isItem12
            ? 'Incidental performance → Vanguard Media ownership dispute'
            : item.four_dimensions?.creative_change?.after_prominence || 'Prominence modified';

          return (
            <div
              key={item.stable_lineage_key}
              onClick={() => onSelectQueueItem(item.stable_lineage_key)}
              className={`rounded-xl border p-4 cursor-pointer transition-all ${
                isSelected
                  ? 'border-sky-400 bg-[#1a2542] shadow-lg shadow-sky-950/50 ring-2 ring-sky-500/20'
                  : 'border-slate-800 bg-[#131b2e] hover:border-slate-700 hover:bg-[#162038]'
              }`}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectQueueItem(item.stable_lineage_key);
                }
              }}
            >
              {/* Header row */}
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-sky-400">
                      Item {itemNumber}
                    </span>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300 uppercase">
                      {item.asset_type}
                    </span>
                    <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
                      <Clock className="h-3 w-3 text-slate-500" aria-hidden="true" />
                      {item.scene} ({timecode})
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white mt-1 leading-snug">
                    {item.asset_name}
                  </h4>
                </div>

                {/* State Badge with Explicit Text and Icon */}
                <div>
                  {item.current_state === DecisionState.STALE && (
                    <span
                      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold badge-stale animate-pulse"
                      aria-label="Status: Stale, Awaiting Counsel Disposition"
                    >
                      <AlertTriangle className="h-3 w-3 text-amber-400" aria-hidden="true" />
                      <span>[STALE - ACTION REQUIRED]</span>
                    </span>
                  )}
                  {item.current_state === DecisionState.RE_ATTESTED && (
                    <span
                      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold badge-reattested"
                      aria-label="Status: Re-Attested by Counsel"
                    >
                      <CheckCircle2 className="h-3 w-3 text-sky-400" aria-hidden="true" />
                      <span>[RE-ATTESTED]</span>
                    </span>
                  )}
                  {item.current_state === DecisionState.EXCEPTION && (
                    <span
                      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold badge-exception"
                      aria-label="Status: Exception Scheduled"
                    >
                      <AlertOctagon className="h-3 w-3 text-rose-400" aria-hidden="true" />
                      <span>[EXCEPTION]</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Prominence Change Indicator */}
              <div className="mt-2.5 rounded-lg bg-slate-900/90 p-2.5 border border-slate-800 text-xs space-y-1">
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-semibold uppercase tracking-wider text-slate-400">
                    Detected Prominence / Rights Shift:
                  </span>
                  <span className="rounded px-1.5 py-0.2 text-[10px] font-bold bg-amber-950/60 text-amber-300 border border-amber-500/30">
                    MATERIAL SHIFT
                  </span>
                </div>
                <p className="font-mono text-amber-200 font-semibold text-xs">
                  {shiftSummary}
                </p>
                {isItem11 && item.four_dimensions?.creative_change?.dialogue_shift && (
                  <p className="text-[11px] text-sky-300 font-serif italic pt-1 border-t border-slate-800">
                    &ldquo;{item.four_dimensions.creative_change.dialogue_shift}&rdquo;
                  </p>
                )}
                {isItem12 && (
                  <p className="text-[11px] text-rose-300 pt-1 border-t border-slate-800 font-mono">
                    Conflict: ASCAP ACE / Vanguard Media ownership claim (Aug 2026)
                  </p>
                )}
              </div>

              {/* Footer row with direct inspect action */}
              <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                <span className="text-slate-400 font-mono truncate max-w-[200px]">
                  Reason: <strong className="text-slate-200">{item.four_dimensions?.statutory_policy_reason?.reason_code || 'CREATIVE_DRIFT'}</strong>
                </span>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onInspectItem) {
                      onInspectItem(item.stable_lineage_key);
                    } else {
                      onSelectQueueItem(item.stable_lineage_key);
                    }
                  }}
                  className="flex items-center gap-1 text-sky-400 hover:text-sky-300 font-semibold transition-colors focus:outline-none focus:underline"
                  aria-label={`Inspect four dimensions for ${item.asset_name}`}
                >
                  <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Inspect 4 Dimensions</span>
                  <ArrowRight className="h-3 w-3" aria-hidden="true" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default DeltaListComponent;
