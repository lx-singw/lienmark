'use client';

/**
 * Lienmark Active Clearance Blockers Summary Component
 * Sprint 4C Usability Fix 2: Unfamiliar Tester Comprehension
 * Prominently surfaces the 2 blockers preventing clearance sign-off in Script Cut v8:
 *  1. Item 11 (Scene 42 Noir Poster): Creative drift (2s background blur -> 14s close-up focal dialogue).
 *     Resolution: Corroborated public domain via LOC. Action: Click Re-Attest.
 *  2. Item 12 (Scene 18 Jazz Cue): Adverse rights assignment (Vanguard Media dispute).
 *     Resolution: Cannot be cleared under current license. Action: Click Leave as Exception or replace cue.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  AlertTriangle,
  AlertOctagon,
  ShieldAlert,
  Gavel,
  CheckCircle2,
} from 'lucide-react';
import { DecisionState, EvaluatedClaim } from '@/lib/types';

export interface ActiveClearanceBlockersProps {
  staleCount: number;
  claims?: ReadonlyArray<EvaluatedClaim>;
  onOpenInGate: (lineageKey: string) => void;
  className?: string;
}

export const ActiveClearanceBlockers: React.FC<ActiveClearanceBlockersProps> = ({
  claims = [],
  onOpenInGate,
  className = '',
}) => {
  // Check resolution states of Item 11 and Item 12 from claims list
  const claim11 = claims.find((c) => c.stable_lineage_key === 'poster_noir_detective_magazine');
  const claim12 = claims.find((c) => c.stable_lineage_key === 'music_cue_midnight_serenade');

  const isItem11Resolved = claim11?.state === DecisionState.RE_ATTESTED;
  const isItem12Resolved = claim12?.state === DecisionState.EXCEPTION;

  // Active blockers pending count
  const pendingBlockersCount = (isItem11Resolved ? 0 : 1) + (isItem12Resolved ? 0 : 1);

  return (
    <section
      aria-label="Active Clearance Blockers Summary"
      role="region"
      className={`rounded-2xl border-2 border-amber-500/60 bg-gradient-to-br from-amber-950/40 via-[#131b2e] to-[#0d1424] p-5 sm:p-6 shadow-2xl shadow-amber-950/30 space-y-4 animate-in fade-in duration-300 ${className}`}
    >
      {/* Component Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-amber-500/30 pb-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/40 flex-shrink-0">
            <AlertTriangle className="h-5 w-5 animate-pulse" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                Active Clearance Blockers Summary
              </h3>
              <span className="rounded-full bg-amber-500/20 border border-amber-500/50 px-2.5 py-0.5 text-xs font-mono font-bold text-amber-300">
                {pendingBlockersCount} Blocking Underwriting Review
              </span>
            </div>
            <p className="text-xs text-amber-200/90 font-medium mt-0.5">
              Script revision v8 introduced 2 material rights deltas that invalidate locked v7 clearance.
              Both must be adjudicated by counsel before Form E&amp;O-2026 can be issued.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <span className="rounded bg-slate-900/90 border border-slate-700 px-2.5 py-1 text-[11px] font-mono text-slate-300">
            Policy Rule: <strong>Fail-Closed Gate</strong>
          </span>
        </div>
      </div>

      {/* 2 Blocker Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Blocker 1: Item 11 (Scene 42 Noir Poster) */}
        <div
          className={`rounded-xl border p-4 transition-all space-y-3 ${
            isItem11Resolved
              ? 'border-emerald-500/40 bg-emerald-950/20'
              : 'border-amber-500/40 bg-[#162038] ring-1 ring-amber-500/20'
          }`}
          role="article"
          aria-label="Clearance Blocker 1: Item 11 Scene 42 Noir Poster"
        >
          {/* Card Header */}
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-sky-500/20 text-sky-300 border border-sky-500/40 px-2 py-0.5 text-xs font-mono font-bold">
                  Blocker 1 of 2
                </span>
                <span className="text-xs font-mono font-bold text-slate-400">
                  Key: poster_noir_detective_magazine
                </span>
              </div>
              <h4 className="text-sm font-bold text-white mt-1.5 flex items-center gap-2">
                <span>Item 11 (Scene 42 Noir Poster)</span>
                {isItem11Resolved && (
                  <span className="inline-flex items-center gap-1 rounded bg-emerald-900/80 px-2 py-0.2 text-[11px] font-semibold text-emerald-300 border border-emerald-500/40">
                    <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                    Resolved: Re-Attested
                  </span>
                )}
              </h4>
            </div>

            <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300">
              Visual Asset
            </span>
          </div>

          {/* Detailed 3-Point Breakdown */}
          <div className="space-y-2 text-xs">
            {/* 1. What Changed */}
            <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-400">
                1. What Changed (Creative Drift):
              </span>
              <p className="text-slate-200 font-semibold">
                Creative drift (2s background blur &rarr; 14s close-up focal dialogue).
              </p>
              <p className="text-[11px] text-slate-400">
                Scene 42: Detective holding vintage 1946 pulp magazine in continuous foreground focus while reciting key monologue.
              </p>
            </div>

            {/* 2. Resolution */}
            <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-sky-400">
                2. Legal Resolution:
              </span>
              <p className="text-slate-200 font-semibold">
                Corroborated public domain via LOC.
              </p>
              <p className="text-[11px] text-slate-400">
                Library of Congress Copyright Office catalog confirms 1946 registration lapsed without required 28-year renewal in 1974.
              </p>
            </div>

            {/* 3. Action Required */}
            <div className="rounded-lg bg-amber-950/40 p-2.5 border border-amber-500/30 space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-300">
                3. Counsel Action Required:
              </span>
              <p className="text-amber-100 font-bold">
                Action: Click Re-Attest.
              </p>
              <p className="text-[11px] text-amber-200/80">
                Submit formal attestation under statutory public domain doctrine to approve for production broadcast.
              </p>
            </div>
          </div>

          {/* Action Button */}
          <div className="pt-1">
            {isItem11Resolved ? (
              <div className="flex items-center justify-between text-xs text-emerald-300 bg-emerald-950/60 rounded-lg p-2 border border-emerald-500/30">
                <span className="flex items-center gap-1.5 font-medium">
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                  <span>Attested by Lead Counsel under Public Domain</span>
                </span>
                <button
                  type="button"
                  onClick={() => onOpenInGate('poster_noir_detective_magazine')}
                  className="text-[11px] text-sky-400 hover:text-sky-300 underline font-semibold"
                >
                  Review Decision
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onOpenInGate('poster_noir_detective_magazine')}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-amber-500 hover:bg-amber-400 py-2.5 px-4 text-xs font-bold text-slate-950 transition-all shadow-md shadow-amber-500/20 active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-amber-300"
                aria-label="Click Re-Attest for Item 11 Scene 42 Noir Poster"
              >
                <Gavel className="h-4 w-4" aria-hidden="true" />
                <span>Open in Checkpoint Gate &rarr; Click Re-Attest</span>
              </button>
            )}
          </div>
        </div>

        {/* Blocker 2: Item 12 (Scene 18 Jazz Cue) */}
        <div
          className={`rounded-xl border p-4 transition-all space-y-3 ${
            isItem12Resolved
              ? 'border-rose-500/40 bg-rose-950/20'
              : 'border-rose-500/50 bg-[#162038] ring-1 ring-rose-500/20'
          }`}
          role="article"
          aria-label="Clearance Blocker 2: Item 12 Scene 18 Jazz Cue"
        >
          {/* Card Header */}
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 px-2 py-0.5 text-xs font-mono font-bold">
                  Blocker 2 of 2
                </span>
                <span className="text-xs font-mono font-bold text-slate-400">
                  Key: music_cue_midnight_serenade
                </span>
              </div>
              <h4 className="text-sm font-bold text-white mt-1.5 flex items-center gap-2">
                <span>Item 12 (Scene 18 Jazz Cue)</span>
                {isItem12Resolved && (
                  <span className="inline-flex items-center gap-1 rounded bg-rose-900/80 px-2 py-0.2 text-[11px] font-semibold text-rose-300 border border-rose-500/40">
                    <AlertOctagon className="h-3 w-3" aria-hidden="true" />
                    Resolved: Scheduled Exception
                  </span>
                )}
              </h4>
            </div>

            <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300">
              Music Cue
            </span>
          </div>

          {/* Detailed 3-Point Breakdown */}
          <div className="space-y-2 text-xs">
            {/* 1. What Changed */}
            <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-rose-400">
                1. What Changed (Adverse Rights):
              </span>
              <p className="text-slate-200 font-semibold">
                Adverse rights assignment (Vanguard Media dispute).
              </p>
              <p className="text-[11px] text-slate-400">
                ASCAP ACE catalog and PRO index reflect Vanguard Media acquisition of worldwide sync rights (August 2026), voiding prior master synch warranty.
              </p>
            </div>

            {/* 2. Resolution */}
            <div className="rounded-lg bg-slate-900/80 p-2.5 border border-slate-800 space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-400">
                2. Legal Resolution:
              </span>
              <p className="text-slate-200 font-semibold">
                Cannot be cleared under current license.
              </p>
              <p className="text-[11px] text-slate-400">
                External synchronization contract conflict creates direct copyright infringement liability under 17 U.S.C. &sect; 504.
              </p>
            </div>

            {/* 3. Action Required */}
            <div className="rounded-lg bg-rose-950/40 p-2.5 border border-rose-500/30 space-y-1">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-rose-300">
                3. Counsel Action Required:
              </span>
              <p className="text-rose-100 font-bold">
                Action: Click Leave as Exception or replace cue.
              </p>
              <p className="text-[11px] text-rose-200/80">
                Exclude cue onto Form E&amp;O-2026 Underwriting Exceptions Schedule or instruct music supervisor to replace track.
              </p>
            </div>
          </div>

          {/* Action Button */}
          <div className="pt-1">
            {isItem12Resolved ? (
              <div className="flex items-center justify-between text-xs text-rose-300 bg-rose-950/60 rounded-lg p-2 border border-rose-500/30">
                <span className="flex items-center gap-1.5 font-medium">
                  <AlertOctagon className="h-4 w-4" aria-hidden="true" />
                  <span>Flagged as Unresolved Exception on Form E&amp;O Schedule</span>
                </span>
                <button
                  type="button"
                  onClick={() => onOpenInGate('music_cue_midnight_serenade')}
                  className="text-[11px] text-sky-400 hover:text-sky-300 underline font-semibold"
                >
                  Review Decision
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => onOpenInGate('music_cue_midnight_serenade')}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-rose-500 hover:bg-rose-400 py-2.5 px-4 text-xs font-bold text-slate-950 transition-all shadow-md shadow-rose-500/20 active:scale-[0.99] focus:outline-none focus:ring-2 focus:ring-rose-300"
                aria-label="Click Leave as Exception or replace cue for Item 12 Scene 18 Jazz Cue"
              >
                <ShieldAlert className="h-4 w-4" aria-hidden="true" />
                <span>Open in Checkpoint Gate &rarr; Click Leave as Exception</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default ActiveClearanceBlockers;
