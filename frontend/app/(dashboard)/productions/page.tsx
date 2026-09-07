'use client';

/**
 * Lienmark Productions Portfolio Page
 * Studio portfolio view showcasing clearance health progress bars and live velocity stats.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Search, FileBadge } from 'lucide-react';
import { ProductionItem } from './types';
import { ProductionCard } from './components/ProductionCard';
import { ReportExportModal } from '@/components/reports/ReportExportModal';

interface VelocityData {
  readonly overall_resolution_time?: { readonly median_hours?: number };
  readonly stale_aging?: { readonly avg_stale_hours?: number };
  readonly resolution_burn_rate?: { readonly clearance_percentage?: number };
}

const PORTFOLIO_PRODUCTIONS: ReadonlyArray<ProductionItem> = [
  {
    id: 'proj_blockbuster_cinema',
    title: 'Project Noir',
    imprint: 'Blockbuster Cinema LLC',
    genre: 'Neo-Noir Crime Thriller (Feature)',
    activeRevision: 'Cut v8.2 Revised',
    lastEvaluatedAt: '',
    totalClaims: 12,
    carriedCount: 10,
    reattestedCount: 1,
    staleCount: 1,
    exceptionCount: 0,
    reportSlug: 'proj_blockbuster_cinema',
    claimBreakdown: { props: 6, music: 3, brands: 2, persons: 1 },
  },
  {
    id: 'proj_neon_horizon',
    title: 'Neon Horizon',
    imprint: 'Starlight Interactive Media',
    genre: 'Sci-Fi Action (Feature)',
    activeRevision: 'Cut v4.0 Locked',
    lastEvaluatedAt: '',
    totalClaims: 24,
    carriedCount: 24,
    reattestedCount: 0,
    staleCount: 0,
    exceptionCount: 0,
    reportSlug: 'proj_blockbuster_cinema',
    claimBreakdown: { props: 12, music: 6, brands: 4, persons: 2 },
  },
  {
    id: 'proj_shadows_manhattan',
    title: 'Shadows of Manhattan',
    imprint: 'Vanguard Pictures',
    genre: 'Period Drama (Pilot)',
    activeRevision: 'Cut v2.1 Drifted',
    lastEvaluatedAt: '',
    totalClaims: 18,
    carriedCount: 15,
    reattestedCount: 1,
    staleCount: 2,
    exceptionCount: 0,
    reportSlug: 'proj_blockbuster_cinema',
    claimBreakdown: { props: 9, music: 4, brands: 3, persons: 2 },
  },
  {
    id: 'proj_last_heist',
    title: 'The Last Heist',
    imprint: 'Criterion Documentary Group',
    genre: 'True Crime Docuseries (Ep 1-6)',
    activeRevision: 'Cut v1.4 Review',
    lastEvaluatedAt: '',
    totalClaims: 32,
    carriedCount: 28,
    reattestedCount: 0,
    staleCount: 3,
    exceptionCount: 1,
    reportSlug: 'proj_blockbuster_cinema',
    claimBreakdown: { props: 10, music: 12, brands: 5, persons: 5 },
  },
];

function renderPortfolioStats(
  assuranceRate: number,
  medianHours: number,
  staleAgingHours: number,
  activeCuts: number
): React.JSX.Element {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div className="rounded-xl border border-slate-800 bg-[#0e1424]/70 p-3.5 space-y-1">
        <span className="text-[11px] text-slate-400 font-medium">Clearance Assurance</span>
        <p className="text-xl font-bold font-mono text-emerald-400">{assuranceRate}%</p>
      </div>
      <div className="rounded-xl border border-slate-800 bg-[#0e1424]/70 p-3.5 space-y-1">
        <span className="text-[11px] text-slate-400 font-medium">Resolution Median</span>
        <p className="text-xl font-bold font-mono text-white">{medianHours}h</p>
      </div>
      <div className="rounded-xl border border-slate-800 bg-[#0e1424]/70 p-3.5 space-y-1">
        <span className="text-[11px] text-slate-400 font-medium">Stale Claim Aging</span>
        <p className="text-xl font-bold font-mono text-amber-400">{staleAgingHours}h avg</p>
      </div>
      <div className="rounded-xl border border-slate-800 bg-[#0e1424]/70 p-3.5 space-y-1">
        <span className="text-[11px] text-slate-400 font-medium">Active Revisions</span>
        <p className="text-xl font-bold font-mono text-sky-400">{activeCuts} Cuts</p>
      </div>
    </div>
  );
}

function renderHeader(
  searchQuery: string,
  onSearchChange: (q: string) => void,
  onOpenExport: () => void,
  count: number
): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-5">
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-white">Studio Productions Portfolio</h1>
          <span className="rounded-full bg-sky-500/20 border border-sky-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-sky-300">
            {count} Active Productions
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Global portfolio view of motion picture and television productions under E&amp;O clearance change control.
        </p>
      </div>
      <div className="flex items-center gap-3 w-full sm:w-auto">
        <button
          onClick={onOpenExport}
          className="flex items-center gap-1.5 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 px-3 py-1.5 text-xs font-semibold text-sky-300 transition-colors shrink-0"
        >
          <FileBadge className="h-3.5 w-3.5" />
          <span>Export Deliverables</span>
        </button>
        <div className="relative w-full sm:w-56">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search productions..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full rounded-xl bg-slate-900 border border-slate-800 pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500/50"
          />
        </div>
      </div>
    </div>
  );
}

export default function ProductionsPage() {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [velocity, setVelocity] = useState<VelocityData | null>(null);
  const [isExportOpen, setIsExportOpen] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    fetch('/api/v1/dashboard/velocity', { headers: { Accept: 'application/json' } })
      .then((r) => (r.ok ? r.json() : null))
      .then((data: VelocityData | null) => {
        if (isMounted && data) setVelocity(data);
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  const filteredProductions = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return PORTFOLIO_PRODUCTIONS.filter((p) => p.title.toLowerCase().includes(q) || p.imprint.toLowerCase().includes(q));
  }, [searchQuery]);

  const assuranceRate = velocity?.resolution_burn_rate?.clearance_percentage ?? 93.8;
  const medianHours = velocity?.overall_resolution_time?.median_hours ?? 4.2;
  const staleAgingHours = velocity?.stale_aging?.avg_stale_hours ?? 12.5;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {renderHeader(searchQuery, setSearchQuery, () => setIsExportOpen(true), PORTFOLIO_PRODUCTIONS.length)}
      {renderPortfolioStats(assuranceRate, medianHours, staleAgingHours, PORTFOLIO_PRODUCTIONS.length)}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredProductions.map((prod) => (
          <ProductionCard key={prod.id} production={prod} />
        ))}
      </div>
      <ReportExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        productionId="proj_blockbuster_cinema"
        productionTitle="Project Noir"
      />
    </div>
  );
}
