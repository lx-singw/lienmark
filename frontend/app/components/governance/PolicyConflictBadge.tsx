'use client';

/**
 * PolicyConflictBadge.tsx
 * High-visibility badge indicating studio policy non-compliance or waiver requirements on claims.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Files <= 250 lines, functions <= 40 lines, zero-any TypeScript.
 */

import React, { useState } from 'react';
import { ShieldAlert, ShieldX, ChevronRight, X, AlertTriangle, FileText } from 'lucide-react';
import { PolicyViolationUI } from './policy_types';

export interface PolicyConflictBadgeProps {
  hasConflict?: boolean;
  requiresSpecialWaiver?: boolean;
  violations?: PolicyViolationUI[];
  compact?: boolean;
  onOpenWaiverModal?: () => void;
}

function renderViolationsList(
  violations: PolicyViolationUI[],
  onOpenWaiverModal?: () => void
): React.ReactNode {
  return (
    <div className="mt-2 space-y-2">
      {violations.map((v, i) => (
        <div
          key={`${v.ruleCode}-${i}`}
          className="p-2 rounded bg-slate-900/90 border border-rose-500/30 text-left text-xs"
        >
          <div className="flex items-center justify-between gap-1 mb-1">
            <span className="font-mono text-[10px] uppercase font-bold text-rose-400">
              {v.ruleCode}
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded uppercase font-semibold bg-rose-950 text-rose-300 border border-rose-600/40">
              {v.severity}
            </span>
          </div>
          <p className="text-slate-300 text-[11px] leading-relaxed">{v.message}</p>
          <div className="mt-1.5 pt-1.5 border-t border-slate-800 text-[10px] text-amber-300 flex items-start gap-1">
            <span className="font-semibold text-slate-400">Remedy:</span>
            <span>{v.remedy}</span>
          </div>
        </div>
      ))}
      {onOpenWaiverModal && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onOpenWaiverModal();
          }}
          className="w-full mt-2 py-1 px-2 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[10px] font-mono font-bold flex items-center justify-center gap-1.5 transition-colors"
        >
          <FileText className="h-3 w-3" />
          <span>Request Admin Policy Waiver</span>
          <ChevronRight className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function renderPopover(
  isCritical: boolean,
  badgeLabel: string,
  violations: PolicyViolationUI[],
  onClose: () => void,
  onOpenWaiverModal?: () => void
): React.ReactNode {
  return (
    <>
      <div
        className="fixed inset-0 z-40"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
      />
      <div
        className="absolute left-0 top-full mt-1.5 w-72 sm:w-80 rounded-lg bg-[#0b1120] border border-slate-700 shadow-2xl p-3 z-50 backdrop-blur-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-1.5 text-xs font-bold font-mono">
            <AlertTriangle className={`h-3.5 w-3.5 ${isCritical ? 'text-rose-400' : 'text-amber-400'}`} />
            <span className={isCritical ? 'text-rose-300' : 'text-amber-300'}>{badgeLabel}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white p-0.5 rounded transition-colors"
            aria-label="Close details"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
        {renderViolationsList(violations, onOpenWaiverModal)}
      </div>
    </>
  );
}

export const PolicyConflictBadge: React.FC<PolicyConflictBadgeProps> = ({
  hasConflict = true,
  requiresSpecialWaiver = false,
  violations = [],
  compact = false,
  onOpenWaiverModal,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!hasConflict && !requiresSpecialWaiver && violations.length === 0) return null;

  const isCritical = hasConflict || violations.some((v) => v.severity === 'critical');
  const badgeLabel = isCritical ? 'POLICY CONFLICT' : 'WAIVER REQUIRED';
  const themeClasses = isCritical
    ? 'bg-rose-950/90 text-rose-300 border-rose-500/60 hover:bg-rose-900/90 hover:border-rose-400'
    : 'bg-amber-950/90 text-amber-300 border-amber-500/60 hover:bg-amber-900/90 hover:border-amber-400';

  const defaultViolations: PolicyViolationUI[] = violations.length > 0 ? violations : [
    {
      ruleCode: isCritical ? 'POL-TERRITORY-EXCLUSION' : 'POL-WAIVER-PENDING',
      severity: isCritical ? 'critical' : 'warning',
      message: isCritical
        ? 'Asset scope does not satisfy inherited studio theatrical perpetual licensing baseline.'
        : 'Production override requires executive Legal Admin signature.',
      remedy: 'Execute buyout addendum or obtain Admin Policy Override.',
    },
  ];

  return (
    <div className="relative inline-block text-left">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className={`inline-flex items-center gap-1 font-mono font-bold rounded px-1.5 py-0.5 border shadow-sm transition-all text-[10px] cursor-pointer ${themeClasses}`}
        title="Click to view policy violations and required statutory remedies"
        aria-expanded={isOpen}
      >
        {isCritical ? (
          <ShieldX className="h-3 w-3 text-rose-400 flex-shrink-0 animate-pulse" />
        ) : (
          <ShieldAlert className="h-3 w-3 text-amber-400 flex-shrink-0" />
        )}
        {!compact && <span>{badgeLabel}</span>}
      </button>

      {isOpen && renderPopover(isCritical, badgeLabel, defaultViolations, () => setIsOpen(false), onOpenWaiverModal)}
    </div>
  );
};

export default PolicyConflictBadge;
