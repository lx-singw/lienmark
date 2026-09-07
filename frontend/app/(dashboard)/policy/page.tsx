'use client';

/**
 * Lienmark Studio Policy & Configuration Page
 * Fail-closed policy rules, spend guard thresholds, and storage webhook configuration.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState } from 'react';
import { SlidersHorizontal, ShieldAlert, DollarSign, HardDrive, Lock } from 'lucide-react';
import { StudioPolicyEditor } from '@/app/components/governance';

export default function PolicyPage() {
  const [showEditor, setShowEditor] = useState<boolean>(false);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-white">Policy &amp; Studio Governance</h1>
            <span className="rounded-full bg-purple-500/20 border border-purple-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-purple-300">
              E&amp;O-2026.1-DEVPOST
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic invalidation rules, Eventarc storage webhook targets, and API spend guard boundaries.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowEditor((prev) => !prev)}
          className="flex items-center gap-1.5 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/40 px-3.5 py-2 text-xs font-semibold text-purple-300 transition-colors"
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          <span>{showEditor ? 'Hide Policy Editor' : 'Open Policy Editor'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <Lock className="h-4 w-4 text-emerald-400" />
            <span>Underwriting Doctrine</span>
          </div>
          <p className="text-lg font-bold text-white">Fail-Closed Gate</p>
          <p className="text-xs text-slate-400">All unverified creative deltas require explicit counsel re-affirmation.</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <DollarSign className="h-4 w-4 text-emerald-400" />
            <span>API Spend Guard</span>
          </div>
          <p className="text-lg font-bold text-emerald-400">$25.00 / Run Limit</p>
          <p className="text-xs text-slate-400">Parallel Search and Gemini calls capped to prevent runaway spend.</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
          <div className="flex items-center gap-2 text-slate-400 text-xs">
            <HardDrive className="h-4 w-4 text-sky-400" />
            <span>Intake Bucket Watcher</span>
          </div>
          <p className="text-lg font-bold text-sky-400">gs://lienmark-intake</p>
          <p className="text-xs text-slate-400">Eventarc storage.objects.v1.finalized triggers automatic intake.</p>
        </div>
      </div>

      {showEditor && (
        <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/90 p-5">
          <StudioPolicyEditor />
        </div>
      )}
    </div>
  );
}
