'use client';

/**
 * Lienmark Clearance Reviewer Dashboard Header
 * Displays project metadata, script revision comparison with content hashes,
 * policy binder information, and primary operational controls.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import Link from 'next/link';
import {
  History,
  RefreshCw,
  FileSpreadsheet,
  Film,
  ShieldAlert,
  GitCompare,
  Hash,
  RotateCcw,
  UserCheck,
  Scale,
  Search,
  Lock,
} from 'lucide-react';
import { UserRole, hasClearanceAuthority } from '@/lib/types';

export interface DashboardHeaderProps {
  projectName?: string;
  projectId?: string;
  policyNumber?: string;
  underwriterStatus?: string;
  baseVersionLabel?: string;
  targetVersionLabel?: string;
  baseContentHash?: string;
  targetContentHash?: string;
  totalClaimsCount?: number;
  auditEventCount: number;
  isRunningEvaluation: boolean;
  isPending?: boolean;
  targetVersionId?: 'v8' | 'v7';
  onToggleTargetVersion?: (version: 'v8' | 'v7') => void;
  onRunEvaluation: () => void;
  onOpenAuditTrail: () => void;
  exceptionsScheduleUrl?: string;
  onResetDemo?: () => void;
  isResettingDemo?: boolean;
  onSeedDemoMode?: (mode: 'baseline' | 'drifted' | 'resolved') => void;
  currentDemoMode?: string;
  userRole?: UserRole;
  onRoleChange?: (role: UserRole) => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  projectName = 'Shadows Over Broadway',
  projectId = 'proj_blockbuster_cinema',
  policyNumber = 'E&O-2026.1-DEVPOST',
  underwriterStatus = 'PENDING_REVIEW',
  baseVersionLabel = 'Script Cut v7 Locked',
  targetVersionLabel = 'v8 Revised',
  baseContentHash = 'a1b2c3d4e5f60718293a4b5c6d7e8f90',
  targetContentHash = 'f9e8d7c6b5a43210fedcba9876543210',
  totalClaimsCount = 12,
  auditEventCount,
  isRunningEvaluation,
  isPending = false,
  targetVersionId = 'v8',
  onToggleTargetVersion,
  onRunEvaluation,
  onOpenAuditTrail,
  exceptionsScheduleUrl = '/report/proj_blockbuster_cinema',
  onResetDemo,
  isResettingDemo = false,
  onSeedDemoMode,
  currentDemoMode = 'drifted',
  userRole = UserRole.REVIEWER,
  onRoleChange,
}) => {
  const shortBaseHash = baseContentHash.slice(0, 8);
  const shortTargetHash = targetContentHash.slice(0, 8);

  return (
    <header
      className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-6"
      role="banner"
      aria-label="Clearance Reviewer Dashboard Header"
    >
      <div className="space-y-1.5">
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          <div className="flex items-center gap-2">
            <Film className="h-6 w-6 text-sky-400" aria-hidden="true" />
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Clearance Reviewer Dashboard
            </h1>
          </div>

          {/* Script Cut Comparison Version Toggle */}
          <div
            className="inline-flex items-center rounded-lg border border-slate-700 bg-slate-900/90 p-1 text-xs font-mono shadow-sm"
            role="group"
            aria-label="Script Cut Version Comparison Selection"
          >
            <span className="text-slate-400 px-2 py-0.5 flex items-center gap-1">
              <GitCompare className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
              <span>v7 &rarr;</span>
            </span>
            <button
              type="button"
              onClick={() => onToggleTargetVersion?.('v8')}
              className={`px-2.5 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-sky-400 ${
                targetVersionId === 'v8'
                  ? 'bg-sky-500/25 text-sky-200 font-bold border border-sky-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Compare v7 against v8 Revised Cut (2 Stale Claims Detected)"
            >
              v8 Revised
            </button>
            <button
              type="button"
              onClick={() => onToggleTargetVersion?.('v7')}
              className={`px-2.5 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-emerald-400 ${
                targetVersionId === 'v7'
                  ? 'bg-emerald-500/25 text-emerald-200 font-bold border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
              title="Evaluate (v7, v7) Baseline Parity (Zero Clearance Drift)"
            >
              v7 Parity (Zero Drift)
            </button>
            <span className="text-[10px] text-slate-500 border-l border-slate-800 pl-2 pr-1 hidden sm:flex items-center gap-0.5">
              <Hash className="h-2.5 w-2.5 text-slate-500" aria-hidden="true" />
              {shortBaseHash} &rarr; {shortTargetHash}
            </span>
          </div>

          {/* Policy Binder Badge */}
          <div
            className="inline-flex items-center gap-1.5 rounded-md border border-amber-500/30 bg-amber-950/40 px-2.5 py-1 text-xs font-mono text-amber-300"
            title={`Policy Binder ${policyNumber} Underwriter Status: ${underwriterStatus}`}
          >
            <ShieldAlert className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
            <span>{policyNumber}</span>
            <span className="rounded bg-amber-900/60 px-1.5 py-0.2 text-[9px] font-bold text-amber-200 border border-amber-500/40 uppercase">
              {underwriterStatus}
            </span>
          </div>

          {/* Active Visual Role Badge (Sprint 1.2 RBAC UI Authority) */}
          {userRole === UserRole.REVIEWER && (
            <div
              className="inline-flex items-center gap-1.5 rounded-md border border-sky-500/40 bg-sky-950/50 px-2.5 py-1 text-xs font-mono text-sky-300 shadow-sm"
              title="Active Role: Reviewer (Sarah Jenkins, Esq. - Lead Clearance Counsel) — Adjudication Authority Active"
            >
              <Scale className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
              <span>Sarah Jenkins, Esq.</span>
              <span className="rounded bg-sky-900/80 px-1.5 py-0.2 text-[9px] font-bold text-sky-200 border border-sky-500/50 uppercase">
                Reviewer (Counsel)
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" title="Affirmative Adjudication Active" />
            </div>
          )}

          {userRole === UserRole.PRODUCER && (
            <div
              className="inline-flex items-center gap-1.5 rounded-md border border-purple-500/40 bg-purple-950/50 px-2.5 py-1 text-xs font-mono text-purple-300 shadow-sm"
              title="Active Role: Producer (Marcus Vance - Executive Producer) — Read-Only Mode (Clearance Gated)"
            >
              <Film className="h-3.5 w-3.5 text-purple-400" aria-hidden="true" />
              <span>Marcus Vance</span>
              <span className="rounded bg-purple-900/80 px-1.5 py-0.2 text-[9px] font-bold text-purple-200 border border-purple-500/50 uppercase">
                Producer
              </span>
              <span className="rounded bg-amber-950 px-1 py-0.2 text-[8px] text-amber-300 border border-amber-500/40 uppercase font-bold">
                Read-Only
              </span>
            </div>
          )}

          {userRole === UserRole.ANALYST && (
            <div
              className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-950/50 px-2.5 py-1 text-xs font-mono text-cyan-300 shadow-sm"
              title="Active Role: Analyst (Alex Chen - Rights Research Analyst) — Read-Only Mode (Clearance Gated)"
            >
              <Search className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
              <span>Alex Chen</span>
              <span className="rounded bg-cyan-900/80 px-1.5 py-0.2 text-[9px] font-bold text-cyan-200 border border-cyan-500/50 uppercase">
                Analyst
              </span>
              <span className="rounded bg-amber-950 px-1 py-0.2 text-[8px] text-amber-300 border border-amber-500/40 uppercase font-bold">
                Read-Only
              </span>
            </div>
          )}

          {userRole === UserRole.ADMIN && (
            <div
              className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/40 bg-emerald-950/50 px-2.5 py-1 text-xs font-mono text-emerald-300 shadow-sm"
              title="Active Role: Admin (Elena Rostova - Studio Legal Ops Admin) — Full Supervisory Access"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
              <span>Elena Rostova</span>
              <span className="rounded bg-emerald-900/80 px-1.5 py-0.2 text-[9px] font-bold text-emerald-200 border border-emerald-500/50 uppercase">
                Admin
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            </div>
          )}

          {/* Interactive Role Switcher (Sprint 1.2 Role-Gating Testing) */}
          {onRoleChange && (
            <div
              className="inline-flex items-center rounded-lg border border-slate-700 bg-slate-900/90 p-1 text-xs font-mono shadow-sm"
              role="group"
              aria-label="Active Principal Role Selector"
            >
              <span className="text-slate-400 px-2 py-0.5 text-[11px] font-sans">Role:</span>
              <button
                type="button"
                onClick={() => onRoleChange(UserRole.REVIEWER)}
                className={`px-2 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-sky-400 ${
                  userRole === UserRole.REVIEWER
                    ? 'bg-sky-500/25 text-sky-200 font-bold border border-sky-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Switch to Reviewer role (Sarah Jenkins, Esq. - Clearance Counsel)"
              >
                Reviewer
              </button>
              <button
                type="button"
                onClick={() => onRoleChange(UserRole.PRODUCER)}
                className={`px-2 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-purple-400 ${
                  userRole === UserRole.PRODUCER
                    ? 'bg-purple-500/25 text-purple-200 font-bold border border-purple-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Switch to Producer role (Marcus Vance - Read-Only Clearance Mode)"
              >
                Producer
              </button>
              <button
                type="button"
                onClick={() => onRoleChange(UserRole.ANALYST)}
                className={`px-2 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-cyan-400 ${
                  userRole === UserRole.ANALYST
                    ? 'bg-cyan-500/25 text-cyan-200 font-bold border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Switch to Analyst role (Alex Chen - Read-Only Clearance Mode)"
              >
                Analyst
              </button>
              <button
                type="button"
                onClick={() => onRoleChange(UserRole.ADMIN)}
                className={`px-2 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-emerald-400 ${
                  userRole === UserRole.ADMIN
                    ? 'bg-emerald-500/25 text-emerald-200 font-bold border border-emerald-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Switch to Admin role (Elena Rostova - Full Access)"
              >
                Admin
              </button>
            </div>
          )}

          {/* Take Quick Selector */}
          {onSeedDemoMode && (
            <div
              className="inline-flex items-center rounded-lg border border-slate-700 bg-slate-900/90 p-1 text-xs font-mono shadow-sm"
              role="group"
              aria-label="Demo Recording Take Selection"
            >
              <span className="text-slate-400 px-2 py-0.5 text-[11px] font-sans">Take:</span>
              <button
                type="button"
                onClick={() => onSeedDemoMode('baseline')}
                className={`px-2 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-emerald-400 ${
                  currentDemoMode === 'baseline'
                    ? 'bg-emerald-500/25 text-emerald-200 font-bold border border-emerald-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Seed Baseline Take: 12 Approved claims under V7"
              >
                V7 Base
              </button>
              <button
                type="button"
                onClick={() => onSeedDemoMode('drifted')}
                className={`px-2 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-amber-400 ${
                  currentDemoMode === 'drifted'
                    ? 'bg-amber-500/25 text-amber-200 font-bold border border-amber-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Seed Drifted Take: 10 Carried, 2 Stale claims"
              >
                V8 Drift
              </button>
              <button
                type="button"
                onClick={() => onSeedDemoMode('resolved')}
                className={`px-2 py-1 rounded text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-sky-400 ${
                  currentDemoMode === 'resolved'
                    ? 'bg-sky-500/25 text-sky-200 font-bold border border-sky-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Seed Resolved Take: 10 Carried, 1 Re-attested, 1 Exception"
              >
                Resolved
              </button>
            </div>
          )}
        </div>

        <p className="text-xs text-slate-400">
          Detect clearance drift, selectively revalidate affected evidence, and keep sign-offs aligned with every production version.
        </p>
        <p className="text-sm text-slate-400 flex flex-wrap items-center gap-x-2 gap-y-1">
          <span>
            Production: <strong className="text-slate-200">{projectName}</strong>{' '}
            <span className="font-mono text-xs text-slate-500">({projectId})</span>
          </span>
          <span className="text-slate-600">&middot;</span>
          <span>
            Carrier Policy: <span className="font-mono text-slate-300">{policyNumber}</span>
          </span>
          <span className="text-slate-600">&middot;</span>
          <span className="text-sky-300 font-semibold">{totalClaimsCount} Canonical Rights Claims</span>
        </p>
      </div>

      {/* Interactive Controls */}
      <div className="flex flex-wrap items-center gap-2.5 sm:gap-3" role="toolbar" aria-label="Dashboard Actions">
        {onResetDemo && (
          <button
            type="button"
            onClick={onResetDemo}
            disabled={isResettingDemo}
            className="flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-950/40 hover:bg-rose-900/60 hover:border-rose-500/70 px-3 py-2 text-sm font-medium text-rose-200 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-rose-400 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Reset Demo State to Baseline (Ctrl+Shift+R)"
            title="Reset entire clearance demo state to clean V7 baseline (Shortcut: Ctrl+Shift+R)"
          >
            <RotateCcw
              className={`h-4 w-4 text-rose-400 ${isResettingDemo ? 'animate-spin' : ''}`}
              aria-hidden="true"
            />
            <span>{isResettingDemo ? 'Resetting...' : 'Reset Demo'}</span>
            <kbd className="hidden lg:inline-block rounded bg-rose-900/80 px-1.5 py-0.5 text-[10px] font-mono text-rose-300 border border-rose-500/40">
              Ctrl+⇧+R
            </kbd>
          </button>
        )}

        <button
          type="button"
          onClick={onOpenAuditTrail}
          className="flex items-center gap-2 rounded-lg border border-purple-500/40 bg-purple-950/40 hover:bg-purple-900/60 px-3.5 py-2 text-sm font-medium text-purple-200 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-400"
          aria-label={`Open Audit Trail Drawer (${auditEventCount} recorded events)`}
        >
          <History className="h-4 w-4 text-purple-400" aria-hidden="true" />
          <span>Audit Trail ({auditEventCount})</span>
        </button>

        <button
          type="button"
          onClick={onRunEvaluation}
          disabled={isRunningEvaluation || isPending}
          className="flex items-center gap-2 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-400 px-4 py-2 text-sm font-semibold text-slate-950 transition-all shadow-md shadow-sky-500/20 active:scale-95 focus:outline-none focus:ring-2 focus:ring-sky-300"
          aria-label={isRunningEvaluation ? 'Clearance Evaluation running' : 'Run Clearance Evaluation'}
          aria-busy={isRunningEvaluation}
        >
          <RefreshCw
            className={`h-4 w-4 ${isRunningEvaluation ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
          <span>{isRunningEvaluation ? 'Evaluating Delta...' : 'Run Clearance Evaluation'}</span>
        </button>

        <Link
          href={exceptionsScheduleUrl}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/90 hover:bg-slate-800 hover:border-slate-600 px-3.5 py-2 text-sm font-medium text-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          aria-label="View Form E&O Exceptions Schedule"
        >
          <FileSpreadsheet className="h-4 w-4 text-amber-400" aria-hidden="true" />
          <span>Exceptions Schedule</span>
        </Link>
      </div>
    </header>
  );
};

export default DashboardHeader;
