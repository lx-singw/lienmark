'use client';

/**
 * PolicyScopeMatrix.tsx
 * Interactive media scopes, distribution territories, and policy toggles matrix.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Files <= 250 lines, functions <= 40 lines, zero-any TypeScript.
 */

import React from 'react';
import { Film, Globe } from 'lucide-react';
import { LicensingScopeUI, TerritoryScopeUI, StudioPolicyConfigUI } from './policy_types';
import {
  ALL_LICENSING_SCOPES,
  ALL_TERRITORY_SCOPES,
  formatLicensingScope,
  formatTerritoryScope,
} from './policy_utils';

export interface PolicyScopeMatrixProps {
  config: StudioPolicyConfigUI;
  onToggleMediaScope: (scope: LicensingScopeUI) => void;
  onToggleTerritory: (territory: TerritoryScopeUI) => void;
  onTogglePerpetual: (val: boolean) => void;
  onToggleProhibitFairUse: (val: boolean) => void;
}

function renderScopes(scopes: LicensingScopeUI[], onToggle: (s: LicensingScopeUI) => void) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
        <Film className="h-3.5 w-3.5 text-purple-400" /> Required Media Licensing Scopes
      </label>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
        {ALL_LICENSING_SCOPES.map((scope) => {
          const info = formatLicensingScope(scope);
          const active = scopes.includes(scope);
          return (
            <button
              key={scope}
              type="button"
              onClick={() => onToggle(scope)}
              className={`p-2 rounded-lg border text-left text-xs transition-all ${
                active
                  ? 'bg-purple-950/70 border-purple-500/60 text-purple-200'
                  : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="font-mono text-[10px] font-bold">{info.shortCode}</div>
              <div className="truncate text-[11px] font-medium">{info.label}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function renderTerritories(territories: TerritoryScopeUI[], onToggle: (t: TerritoryScopeUI) => void) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
        <Globe className="h-3.5 w-3.5 text-emerald-400" /> Mandatory Distribution Territories
      </label>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
        {ALL_TERRITORY_SCOPES.map((territory) => {
          const info = formatTerritoryScope(territory);
          const active = territories.includes(territory);
          return (
            <button
              key={territory}
              type="button"
              onClick={() => onToggle(territory)}
              className={`p-2 rounded-lg border text-left text-xs transition-all ${
                active
                  ? 'bg-emerald-950/70 border-emerald-500/60 text-emerald-200'
                  : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="font-mono text-[10px] font-bold">{info.code}</div>
              <div className="truncate text-[11px] font-medium">{info.tag}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function renderToggles(
  mandatoryPerpetual: boolean,
  prohibitFairUse: boolean,
  onTogglePerpetual: (v: boolean) => void,
  onToggleFairUse: (v: boolean) => void
) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
      <label className="flex items-start gap-2.5 cursor-pointer">
        <input
          type="checkbox"
          checked={mandatoryPerpetual}
          onChange={(e) => onTogglePerpetual(e.target.checked)}
          className="mt-1 rounded bg-slate-800 border-slate-700 text-purple-500 focus:ring-0"
        />
        <div>
          <div className="text-xs font-bold text-slate-200">Mandatory Perpetual Theatrical Rights</div>
          <div className="text-[11px] text-slate-400">Strict rule: all theatrical sync licenses must be perpetual worldwide.</div>
        </div>
      </label>
      <label className="flex items-start gap-2.5 cursor-pointer">
        <input
          type="checkbox"
          checked={prohibitFairUse}
          onChange={(e) => onToggleFairUse(e.target.checked)}
          className="mt-1 rounded bg-slate-800 border-slate-700 text-purple-500 focus:ring-0"
        />
        <div>
          <div className="text-xs font-bold text-slate-200">Prohibit Unvetted Trademark Fair-Use</div>
          <div className="text-[11px] text-slate-400">Zero tolerance for fair-use defenses on commercial logos without counsel sign-off.</div>
        </div>
      </label>
    </div>
  );
}

export const PolicyScopeMatrix: React.FC<PolicyScopeMatrixProps> = ({
  config,
  onToggleMediaScope,
  onToggleTerritory,
  onTogglePerpetual,
  onToggleProhibitFairUse,
}) => {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {renderScopes(config.requiredMediaScopes, onToggleMediaScope)}
        {renderTerritories(config.distributionTerritories, onToggleTerritory)}
      </div>
      {renderToggles(
        config.mandatoryPerpetualForTheatrical,
        config.prohibitUnvettedTrademarkFairUse,
        onTogglePerpetual,
        onToggleProhibitFairUse
      )}
    </div>
  );
};

export default PolicyScopeMatrix;
