'use client';

/**
 * InboxEmptyState Component
 * Displays celebratory zero-state when all triage action items are cleared.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import Link from 'next/link';
import { ShieldCheck, Film, FileText } from 'lucide-react';

export const InboxEmptyState: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-800/80 bg-[#0e1424]/60 backdrop-blur-md p-12 text-center space-y-4 max-w-lg mx-auto mt-8">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-lg shadow-emerald-950/50">
        <ShieldCheck className="h-8 w-8" />
      </div>

      <div className="space-y-1.5">
        <h3 className="text-lg font-bold text-white tracking-tight">
          Inbox Zero — Zero Unresolved Clearance Drift
        </h3>
        <p className="text-xs text-slate-400 max-w-sm">
          All rights-bearing claims, clarifications, and budget authorizations are up to date for this production cut.
        </p>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <Link
          href="/productions"
          className="flex items-center gap-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-200 transition-colors"
        >
          <Film className="h-3.5 w-3.5 text-sky-400" />
          <span>View Productions</span>
        </Link>
        <Link
          href="/report/proj_blockbuster_cinema"
          className="flex items-center gap-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 px-3.5 py-2 text-xs font-semibold text-amber-300 transition-colors"
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Form E&amp;O-2026</span>
        </Link>
      </div>
    </div>
  );
};

export default InboxEmptyState;
