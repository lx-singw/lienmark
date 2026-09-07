'use client';

/**
 * AdminOverridePanel.tsx
 * Admin Clearance Policy Override sub-panel with statutory signature and ledger stamping.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Files <= 250 lines, functions <= 40 lines, zero-any TypeScript.
 */

import React, { useState, useTransition } from 'react';
import { ShieldAlert, FileCheck, AlertCircle } from 'lucide-react';
import { ProductionPolicyOverrideUI } from './policy_types';
import { validatePolicyOverride, generateLedgerStamp } from './policy_utils';

export interface AdminOverridePanelProps {
  override: ProductionPolicyOverrideUI;
  onChangeOverride: (updater: (prev: ProductionPolicyOverrideUI) => ProductionPolicyOverrideUI) => void;
  isAdmin: boolean;
  productionId: string;
  onCommitOverride?: (override: ProductionPolicyOverrideUI) => void;
  onSavePolicy?: () => void;
}

function renderInputs(
  override: ProductionPolicyOverrideUI,
  isAdmin: boolean,
  onChange: (u: (p: ProductionPolicyOverrideUI) => ProductionPolicyOverrideUI) => void
) {
  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input
          type="text"
          placeholder="Admin Signatory Name (e.g., E. Vance, VP Legal)"
          value={override.adminActorName}
          disabled={!isAdmin}
          onChange={(e) => onChange((prev) => ({ ...prev, adminActorName: e.target.value }))}
          className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none"
        />
        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input
            type="checkbox"
            checked={override.allowTrademarkFairUse}
            disabled={!isAdmin}
            onChange={(e) => onChange((prev) => ({ ...prev, allowTrademarkFairUse: e.target.checked }))}
            className="rounded bg-slate-800 border-slate-700 text-amber-500"
          />
          <span>Waiver: Allow Trademark Fair-Use Exception</span>
        </label>
      </div>
      <textarea
        rows={2}
        placeholder="Legal rationale for production policy deviation (statutory basis, risk appraisal)..."
        value={override.rationale}
        disabled={!isAdmin}
        onChange={(e) => onChange((prev) => ({ ...prev, rationale: e.target.value }))}
        className="w-full p-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:border-purple-500 focus:outline-none"
      />
    </>
  );
}

function renderActions(
  isAdmin: boolean,
  isPending: boolean,
  onCommit: () => void,
  onSavePolicy?: () => void
) {
  return (
    <div className="flex items-center justify-end gap-2 pt-1">
      {onSavePolicy && (
        <button
          type="button"
          onClick={onSavePolicy}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 transition-colors"
        >
          Save Policy Template
        </button>
      )}
      <button
        type="button"
        disabled={!isAdmin || isPending}
        onClick={onCommit}
        className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold flex items-center gap-1.5 transition-all ${
          isAdmin
            ? 'bg-purple-600 hover:bg-purple-500 text-white shadow-md'
            : 'bg-slate-800 text-slate-500 cursor-not-allowed'
        }`}
      >
        <FileCheck className="h-3.5 w-3.5" />
        <span>{isPending ? 'Logging to Ledger...' : 'Sign & Commit Override'}</span>
      </button>
    </div>
  );
}

export const AdminOverridePanel: React.FC<AdminOverridePanelProps> = ({
  override,
  onChangeOverride,
  isAdmin,
  productionId,
  onCommitOverride,
  onSavePolicy,
}) => {
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isPending, startTransition] = useTransition();

  const handleCommit = () => {
    if (!isAdmin) return;
    const val = validatePolicyOverride(override);
    if (!val.isValid) return setValidationErrors(val.errors);
    setValidationErrors([]);
    startTransition(() => {
      const stamp = generateLedgerStamp(productionId, override.adminActorName);
      const updated: ProductionPolicyOverrideUI = {
        ...override,
        overrideId: `ovr_${Date.now()}`,
        appliedAt: new Date().toISOString(),
        ledgerEventId: stamp,
        isActive: true,
      };
      onChangeOverride(() => updated);
      onCommitOverride?.(updated);
    });
  };

  return (
    <div className="p-4 rounded-xl bg-slate-900/90 border border-purple-500/30 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-amber-400" />
          <h3 className="text-xs font-mono uppercase font-bold text-amber-300">Executive Admin Policy Override</h3>
        </div>
        {override.ledgerEventId ? (
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-500/40">
            LEDGER: {override.ledgerEventId}
          </span>
        ) : (
          <span className="font-mono text-[10px] text-slate-500">No Active Override</span>
        )}
      </div>

      {validationErrors.length > 0 && (
        <div className="p-2 rounded bg-rose-950/80 border border-rose-500/50 text-rose-300 text-xs font-mono space-y-1">
          {validationErrors.map((err, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <AlertCircle className="h-3 w-3 flex-shrink-0" />
              <span>{err}</span>
            </div>
          ))}
        </div>
      )}

      {renderInputs(override, isAdmin, onChangeOverride)}
      {renderActions(isAdmin, isPending, handleCommit, onSavePolicy)}
    </div>
  );
};

export default AdminOverridePanel;
