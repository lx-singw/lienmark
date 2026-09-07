'use client';

/**
 * WrapChecklistPreview Component
 * Post-Production Wrap Delivery Gate & Distributor Funds Release Status Preview.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lock,
  Unlock,
  ShieldCheck,
  FileCheck2,
} from 'lucide-react';
import { WrapChecklistResponse, WrapChecklistItem } from '../types';

interface WrapChecklistPreviewProps {
  readonly checklist: WrapChecklistResponse;
}

function renderGateBanner(checklist: WrapChecklistResponse): React.JSX.Element {
  const isReady = checklist.is_ready_for_funds_release;
  return (
    <div
      className={`rounded-xl border p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 ${
        isReady
          ? 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300'
          : 'border-rose-500/40 bg-rose-950/20 text-rose-300'
      }`}
    >
      <div className="flex items-center gap-3">
        {isReady ? (
          <Unlock className="h-6 w-6 text-emerald-400 shrink-0" />
        ) : (
          <Lock className="h-6 w-6 text-rose-400 shrink-0" />
        )}
        <div>
          <h4 className="text-sm font-bold uppercase tracking-wider">
            {isReady ? 'Distributor Funds Release: Authorized' : 'Distributor Funds Release: Blocked'}
          </h4>
          <p className="text-xs text-slate-300 mt-0.5">
            {isReady
              ? 'All 100% legal delivery gates and clearance exhibits verified.'
              : `${checklist.blocking_reasons.length} blocking condition(s) prevent escrow release.`}
          </p>
        </div>
      </div>
      <div className="text-right sm:border-l sm:border-slate-800/80 sm:pl-4">
        <span className="text-[10px] uppercase font-mono text-slate-400 block">Completeness</span>
        <span className="text-lg font-bold font-mono text-white">
          {checklist.cleared_percentage.toFixed(1)}%
        </span>
      </div>
    </div>
  );
}

function renderSignOffStamp(checklist: WrapChecklistResponse): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-xl bg-slate-950/70 border border-slate-800 p-3 text-xs font-mono">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-emerald-400" />
        <span className="text-slate-400">Counsel Sign-off:</span>
        <span className="text-white font-bold">
          {checklist.signed_off ? checklist.signed_off_by ?? 'Production Counsel' : 'PENDING'}
        </span>
      </div>
      <div className="text-slate-400 text-[11px]">
        {checklist.signed_off_at ? `Signed at ${checklist.signed_off_at}` : 'Awaiting Final Signature'}
      </div>
    </div>
  );
}

function renderBlockers(checklist: WrapChecklistResponse): React.JSX.Element | null {
  if (checklist.blocking_reasons.length === 0) return null;
  return (
    <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-3.5 space-y-2">
      <div className="flex items-center gap-2 text-xs font-bold text-rose-400 uppercase tracking-wider">
        <AlertTriangle className="h-4 w-4" />
        <span>Active Blocker Invariants</span>
      </div>
      <ul className="space-y-1 text-xs text-rose-200 list-disc list-inside">
        {checklist.blocking_reasons.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
    </div>
  );
}

function renderChecklistItem(item: WrapChecklistItem): React.JSX.Element {
  const isCleared = item.status === 'CLEARED';
  return (
    <div
      key={item.item_id}
      className="flex items-start justify-between gap-3 rounded-xl border border-slate-800 bg-[#0B0F17]/80 p-3.5"
    >
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] font-mono text-sky-300">
            {item.category}
          </span>
          <span className="text-xs font-bold text-white">{item.title}</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">{item.description}</p>
        {item.blocking_reason && (
          <p className="text-[11px] font-mono text-rose-400 pt-1">
            Blocker: {item.blocking_reason}
          </p>
        )}
      </div>

      <div className="shrink-0 pt-0.5">
        {isCleared ? (
          <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-1 rounded-lg">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>CLEARED</span>
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] font-mono text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-1 rounded-lg">
            <XCircle className="h-3.5 w-3.5" />
            <span>{item.status}</span>
          </span>
        )}
      </div>
    </div>
  );
}

export function WrapChecklistPreview({
  checklist,
}: WrapChecklistPreviewProps): React.JSX.Element {
  return (
    <div className="space-y-4 text-slate-200">
      <div className="rounded-2xl border border-slate-800 bg-[#0B0F17] p-5 shadow-2xl space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-800/80 pb-4">
          <FileCheck2 className="h-5 w-5 text-sky-400" />
          <div>
            <h3 className="text-base font-bold text-white tracking-tight">
              POST-PRODUCTION WRAP DELIVERY GATE
            </h3>
            <p className="text-xs text-slate-400">
              Escrow Release Checklist • {checklist.cleared_items}/{checklist.total_items} Conditions Satisfied
            </p>
          </div>
        </div>

        {renderGateBanner(checklist)}
        {renderSignOffStamp(checklist)}
        {renderBlockers(checklist)}

        <div className="space-y-2 pt-2">
          {checklist.items.map((item) => renderChecklistItem(item))}
        </div>
      </div>
    </div>
  );
}
