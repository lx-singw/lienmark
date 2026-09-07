'use client';

/**
 * ExceptionsSchedulePreview Component
 * Certified Form E&O-2026 Underwriting Exceptions & Carried Claims Preview with Hash Stamps.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Hash,
  Award,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
} from 'lucide-react';
import { ExceptionsScheduleData, RiskLevel } from '../types';

interface ExceptionsSchedulePreviewProps {
  readonly data: ExceptionsScheduleData;
}

function getRiskBadgeClass(level: RiskLevel): string {
  switch (level) {
    case 'CRITICAL':
      return 'bg-rose-500/20 border-rose-500/40 text-rose-300';
    case 'HIGH':
      return 'bg-amber-500/20 border-amber-500/40 text-amber-300';
    case 'MEDIUM':
      return 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300';
    case 'LOW':
    default:
      return 'bg-sky-500/20 border-sky-500/40 text-sky-300';
  }
}

function renderHashBadge(label: string, hash: string): React.JSX.Element {
  return (
    <div className="flex flex-col gap-1 rounded-xl bg-slate-950/80 border border-slate-800/80 p-3 font-mono">
      <div className="flex items-center gap-1.5 text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
        <Hash className="h-3 w-3 text-emerald-400" />
        <span>{label}</span>
      </div>
      <p className="text-xs text-slate-200 break-all font-mono select-all bg-black/40 px-2 py-1 rounded border border-slate-800/50">
        {hash}
      </p>
    </div>
  );
}

function renderExceptionsSection(data: ExceptionsScheduleData): React.JSX.Element {
  if (data.exception_claims.length === 0) {
    return (
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-center">
        <p className="text-xs text-emerald-300 font-medium">
          Zero Clearance Exceptions Recorded — Clean Underwriting Exhibit
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wider">
        <AlertTriangle className="h-4 w-4" />
        <span>Disclosed Exceptions ({data.exception_claims.length})</span>
      </div>
      <div className="space-y-2">
        {data.exception_claims.map((exc) => (
          <div
            key={exc.id}
            className="rounded-xl border border-amber-500/30 bg-[#0B0F17]/90 p-3.5 space-y-2"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white">{exc.title}</span>
                <span className="text-[10px] font-mono text-slate-400">({exc.category})</span>
              </div>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${getRiskBadgeClass(
                  exc.risk_level
                )}`}
              >
                {exc.risk_level} RISK
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">{exc.reason}</p>
            {exc.policy_rule && (
              <div className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                <span className="text-slate-500">Policy Carve-out:</span>
                <span className="text-amber-300">{exc.policy_rule}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function renderClearedSection(data: ExceptionsScheduleData): React.JSX.Element {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
        <CheckCircle2 className="h-4 w-4" />
        <span>Certified Cleared &amp; Carried Claims ({data.cleared_claims.length})</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {data.cleared_claims.map((cl) => (
          <div
            key={cl.id}
            className="rounded-lg border border-slate-800 bg-[#0B0F17]/70 p-3 space-y-1"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-200 truncate">{cl.title}</span>
              <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                {cl.status}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
              <span>{cl.category}</span>
              <span>{cl.timecode ?? 'Timeline Locked'}</span>
            </div>
            {cl.counsel_note && (
              <p className="text-[11px] text-slate-400 italic pt-1 border-t border-slate-800/60">
                {cl.counsel_note}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function renderScheduleHeader(data: ExceptionsScheduleData): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800/80 pb-4">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <FileCheck className="h-5 w-5 text-sky-400" />
          <h3 className="text-base font-bold text-white tracking-tight">
            FORM E&amp;O-2026: CLEARANCE EXCEPTIONS SCHEDULE
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Certified Legal Exhibit for Production Errors &amp; Omissions Underwriting
        </p>
      </div>
      <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 text-xs text-emerald-300 font-mono">
        <Award className="h-4 w-4 text-emerald-400 shrink-0" />
        <span>{data.underwriter_seal}</span>
      </div>
    </div>
  );
}

function renderMetricsGrid(data: ExceptionsScheduleData): React.JSX.Element {
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-center">
        <span className="text-[10px] text-slate-400 font-mono block uppercase">Cleared Claims</span>
        <span className="text-xl font-bold font-mono text-emerald-400">{data.cleared_claims.length}</span>
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-center">
        <span className="text-[10px] text-slate-400 font-mono block uppercase">Exceptions</span>
        <span className="text-xl font-bold font-mono text-amber-400">{data.exception_claims.length}</span>
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-center">
        <span className="text-[10px] text-slate-400 font-mono block uppercase">Underwriting Date</span>
        <span className="text-xs font-bold font-mono text-sky-300 truncate block mt-1">{data.certified_at}</span>
      </div>
    </div>
  );
}

export function ExceptionsSchedulePreview({
  data,
}: ExceptionsSchedulePreviewProps): React.JSX.Element {
  return (
    <div className="space-y-5 text-slate-200">
      <div className="rounded-2xl border border-slate-800 bg-[#0B0F17] p-5 shadow-2xl space-y-4">
        {renderScheduleHeader(data)}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {renderHashBadge('SHA-256 CUT HASH', data.cut_hash)}
          {renderHashBadge('SHA-256 LEDGER HEAD HASH', data.ledger_head_hash)}
        </div>
        {renderMetricsGrid(data)}
        {renderExceptionsSection(data)}
        {renderClearedSection(data)}
      </div>
    </div>
  );
}
