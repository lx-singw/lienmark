'use client';

/**
 * Lienmark Dashboard Top Navigation Bar
 * Features production selector, SSE status, system health badges, and schedule link.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import Link from 'next/link';
import {
  FileText,
  Radio,
  ChevronDown,
  Sparkles,
} from 'lucide-react';
import SystemStatusBadges from '@/app/components/SystemStatusBadges';

interface TopNavProps {
  readonly selectedProduction?: string;
}

export const TopNav: React.FC<TopNavProps> = ({
  selectedProduction = 'Blockbuster Cinema — Project Noir (Cut v8)',
}) => {
  return (
    <header className="h-16 flex-shrink-0 border-b border-slate-800/80 bg-[#0B0F17]/90 backdrop-blur-md px-6 flex items-center justify-between no-print z-20">
      {/* Left: Production Selector */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-700 transition-colors cursor-pointer">
          <div className="h-2 w-2 rounded-full bg-sky-400" />
          <span className="font-semibold">{selectedProduction}</span>
          <ChevronDown className="h-3.5 w-3.5 text-slate-400 ml-1" />
        </div>

        {/* Live SSE Stream Pulse */}
        <div className="hidden lg:flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/30 px-2.5 py-1 text-[11px] font-mono text-emerald-300">
          <Radio className="h-3 w-3 animate-pulse text-emerald-400" />
          <span>SSE Stream Connected</span>
        </div>
      </div>

      {/* Right: Telemetry & Actions */}
      <div className="flex items-center gap-3">
        <SystemStatusBadges />

        <Link
          href="/report/proj_blockbuster_cinema"
          className="flex items-center gap-1.5 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors"
        >
          <FileText className="h-3.5 w-3.5" />
          <span>Form E&amp;O-2026</span>
        </Link>
      </div>
    </header>
  );
};

export default TopNav;
