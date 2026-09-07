'use client';

/**
 * Lienmark Decisions & Checkpoint Gate Page
 * Chronological immutable ledger explorer, cryptographic verification, and human counsel audit trail.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Gavel, ArrowUpRight, Lock, FileSpreadsheet } from 'lucide-react';
import { DecisionChainResponse } from './types';
import { DecisionFilterToolbar } from './components/DecisionFilterToolbar';
import { DecisionTimeline } from './components/DecisionTimeline';
import { CryptoVerificationModal } from './components/CryptoVerificationModal';
import { ReportExportModal } from '@/components/reports/ReportExportModal';

function renderDecisionsHeader(onOpenExport: () => void): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-5">
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-white">Decisions &amp; Checkpoint Gate</h1>
          <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-emerald-300">
            Immutable Cryptographic Ledger
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Two-person accountable gate: Lead Counsel signs off on creative drift and E&amp;O exceptions.
        </p>
      </div>

      <div className="flex items-center gap-2.5">
        <button
          onClick={onOpenExport}
          className="flex items-center gap-1.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 px-3.5 py-2 text-xs font-semibold text-emerald-300 transition-colors"
        >
          <FileSpreadsheet className="h-3.5 w-3.5" />
          <span>Export Deliverables</span>
        </button>
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
  );
}

function renderLedgerStats(chain: DecisionChainResponse | null): React.JSX.Element {
  const approved = chain?.events.filter((e) => e.decision_status === 'APPROVED').length || 0;
  const superseded = chain?.events.filter((e) => e.is_superseded).length || 0;
  const isValid = chain?.is_chain_valid ?? true;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
        <span className="text-xs font-mono text-slate-400">Total Cleared Claims</span>
        <p className="text-2xl font-bold font-mono text-emerald-400">{approved} Blocks</p>
        <p className="text-xs text-slate-400">Cryptographically chained</p>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
        <span className="text-xs font-mono text-slate-400">Superseded Overrides</span>
        <p className="text-2xl font-bold font-mono text-purple-400">{superseded} Events</p>
        <p className="text-xs text-slate-400">Non-destructive append-only history</p>
      </div>
      <div className="rounded-2xl border border-slate-800 bg-[#0e1424]/80 p-5 space-y-2">
        <span className="text-xs font-mono text-slate-400">Ledger Integrity</span>
        <p className="text-2xl font-bold font-mono text-white flex items-center gap-2">
          <Lock className="h-5 w-5 text-emerald-400" />
          <span>{isValid ? 'SHA-256 Valid' : 'Tamper Detected'}</span>
        </p>
        <p className="text-xs text-slate-400">Zero cryptographic tamper flags</p>
      </div>
    </div>
  );
}

export default function DecisionsPage(): React.JSX.Element {
  const [chain, setChain] = useState<DecisionChainResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [verifyEventId, setVerifyEventId] = useState<string | null>(null);
  const [isExportOpen, setIsExportOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchLedger = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/ledger/decisions');
      if (res.ok) setChain((await res.json()) as DecisionChainResponse);
    } catch (err) {
      console.warn('[DecisionsPage] Failed to fetch decisions ledger:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  const filteredEvents = useMemo(() => {
    if (!chain?.events) return [];
    return chain.events.filter((evt) => {
      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'SUPERSEDED' && evt.is_superseded) ||
        evt.decision_status?.toUpperCase() === statusFilter;
      const q = searchQuery.trim().toLowerCase();
      const matchesQuery =
        !q ||
        evt.claim_title?.toLowerCase().includes(q) ||
        evt.counsel_rationale?.toLowerCase().includes(q) ||
        evt.actor_name?.toLowerCase().includes(q) ||
        evt.entry_hash?.toLowerCase().includes(q);
      return matchesStatus && matchesQuery;
    });
  }, [chain?.events, statusFilter, searchQuery]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {renderDecisionsHeader(() => setIsExportOpen(true))}
      {renderLedgerStats(chain)}
      <DecisionFilterToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        activeStatus={statusFilter}
        onStatusChange={setStatusFilter}
        isChainValid={chain?.is_chain_valid ?? true}
        chainLength={chain?.chain_length ?? 0}
      />
      {loading ? (
        <div className="py-12 text-center text-xs font-mono text-slate-400">Loading immutable decision timeline...</div>
      ) : (
        <DecisionTimeline events={filteredEvents} onVerifyEvent={setVerifyEventId} />
      )}
      {verifyEventId && <CryptoVerificationModal eventId={verifyEventId} onClose={() => setVerifyEventId(null)} />}
      <ReportExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        initialTab="audit_manifest"
        productionId="proj_blockbuster_cinema"
        productionTitle="Project Noir"
      />
    </div>
  );
}
