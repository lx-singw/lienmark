'use client';

/**
 * Lienmark Decisions & Checkpoint Gate Page
 * Accountable dual-review decision packages, conflict attestations, and immutable ledger explorer.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import Link from 'next/link';
import { Gavel, ShieldCheck, ArrowUpRight, FileText, CheckCircle2, Lock } from 'lucide-react';

export default function DecisionsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-white">Decisions &amp; Checkpoint Gate</h1>
            <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-emerald-300">
              Two-Person Accountable Gate
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic human checkpointing: Lead Counsel signs off on creative drift and E&amp;O exceptions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1.5 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 px-3.5 py-2 text-xs font-semibold text-sky-300 transition-colors"
          >
            <Gavel className="h-3.5 w-3.5" />
            <span>Open Interactive Gate</span>
            <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
          <span className="text-xs font-mono text-slate-400">Total Cleared Claims</span>
          <p className="text-2xl font-bold font-mono text-emerald-400">11 of 12</p>
          <p className="text-xs text-slate-400">10 Carried Forward · 1 Re-Attested</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
          <span className="text-xs font-mono text-slate-400">Exceptions Scheduled</span>
          <p className="text-2xl font-bold font-mono text-rose-400">1 Item</p>
          <p className="text-xs text-slate-400">Scene 18 Jazz Cue (Vanguard dispute)</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
          <span className="text-xs font-mono text-slate-400">Ledger Integrity</span>
          <p className="text-2xl font-bold font-mono text-white flex items-center gap-2">
            <Lock className="h-5 w-5 text-emerald-400" />
            <span>SHA-256 Valid</span>
          </p>
          <p className="text-xs text-slate-400">Zero cryptographic tamper flags</p>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-6 space-y-4">
        <h3 className="text-base font-bold text-white">Underwriting Schedule Direct Links</h3>
        <p className="text-xs text-slate-300">
          Completed decision packages are committed into the tamper-evident cryptographic ledger and synthesized into the statutory schedule.
        </p>
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Link
            href="/report/proj_blockbuster_cinema"
            className="flex items-center gap-2 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 px-4 py-2 text-xs font-semibold text-amber-300 transition-colors"
          >
            <FileText className="h-4 w-4" />
            <span>Generate Form E&amp;O-2026 Exceptions Schedule</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
