'use client';

/**
 * Evidence Comparison Modal Component
 * Side-by-side legal reconciliation of public claims vs private contracts.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useEffect, useState } from 'react';
import { X, ShieldCheck, AlertTriangle, Layers, FileText, CheckCircle2 } from 'lucide-react';
import { EvidenceCompareResponse } from '../types';

interface EvidenceComparisonModalProps {
  readonly claimId: string;
  readonly onClose: () => void;
}

export function EvidenceComparisonModal({
  claimId,
  onClose,
}: EvidenceComparisonModalProps): React.JSX.Element {
  const [data, setData] = useState<EvidenceCompareResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchComparison() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/v1/evidence/compare?claim_id=${encodeURIComponent(claimId)}`);
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const payload = (await res.json()) as EvidenceCompareResponse;
        if (isMounted) setData(payload);
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : 'Failed to load comparison');
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    fetchComparison();
    return () => {
      isMounted = false;
    };
  }, [claimId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl border border-slate-800 bg-[#0e1424] shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <Layers className="h-5 w-5 text-sky-400" />
            <div>
              <h2 className="text-base font-bold text-white">Side-by-Side Rights Reconciliation</h2>
              <p className="text-xs font-mono text-slate-400">Claim ID: {claimId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="py-12 text-center text-xs font-mono text-slate-400">
              Reconciling statutory registrations against private contracts...
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300">
              {error}
            </div>
          )}

          {data && (
            <>
              <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                <div>
                  <span className="text-[10px] font-mono uppercase text-slate-400">Target Asset Claim</span>
                  <h3 className="text-sm font-bold text-white">{data.claim_title}</h3>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-mono font-bold border ${
                      data.legal_shield_active
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    }`}
                  >
                    {data.legal_shield_active ? (
                      <ShieldCheck className="h-3.5 w-3.5" />
                    ) : (
                      <AlertTriangle className="h-3.5 w-3.5" />
                    )}
                    <span>{data.concordance_status}</span>
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h4 className="text-xs font-mono uppercase text-sky-400 flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5" />
                    <span>Public Catalog &amp; Registry Evidence</span>
                  </h4>
                  {data.public_findings.length === 0 ? (
                    <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-950/50 text-xs text-slate-500">
                      No external registry records recorded.
                    </div>
                  ) : (
                    data.public_findings.map((item) => (
                      <div
                        key={item.evidence_id}
                        className="rounded-xl border border-slate-800/80 bg-slate-950/70 p-3.5 space-y-2"
                      >
                        <span className="text-[11px] font-bold text-white">{item.title}</span>
                        <p className="text-xs font-mono text-slate-300 leading-relaxed">
                          {item.snippet}
                        </p>
                      </div>
                    ))
                  )}
                </div>

                <div className="space-y-3">
                  <h4 className="text-xs font-mono uppercase text-emerald-400 flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span>Executed Private Contracts (§ 205e)</span>
                  </h4>
                  {data.private_contract_clauses.length === 0 ? (
                    <div className="p-4 rounded-xl border border-slate-800/80 bg-slate-950/50 text-xs text-slate-500">
                      No private contract or release instrument bound.
                    </div>
                  ) : (
                    data.private_contract_clauses.map((clause, idx) => (
                      <div
                        key={idx}
                        className="rounded-xl border border-slate-800/80 bg-slate-950/70 p-3.5 space-y-2"
                      >
                        <span className="text-[11px] font-bold text-white">
                          {String(clause.clause_title || 'Contract Release Instrument')}
                        </span>
                        <p className="text-xs font-mono text-slate-300 leading-relaxed">
                          {String(clause.clause_text || clause.summary || 'Executed license shield.')}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-sky-950/20 p-4 space-y-1">
                <span className="text-[10px] font-mono uppercase text-sky-400 font-bold">
                  Counsel Reconciliation Analysis
                </span>
                <p className="text-xs text-slate-200 leading-relaxed">{data.analysis}</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
