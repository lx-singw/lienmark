'use client';

/**
 * StudioPolicyEditor.tsx
 * Studio Policy Administrative Editor and Production Governance Panel.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Files <= 250 lines, functions <= 40 lines, zero-any TypeScript.
 */

import React, { useState } from 'react';
import { Unlock, Lock, Sliders, Building2, CheckCircle2 } from 'lucide-react';
import {
  LicensingScopeUI,
  TerritoryScopeUI,
  StudioProfileTypeUI,
  StudioPolicyConfigUI,
  ProductionPolicyOverrideUI,
} from './policy_types';
import { PROFILE_PRESETS, getProfileBadgeStyles } from './policy_utils';
import { PolicyScopeMatrix } from './PolicyScopeMatrix';
import { AdminOverridePanel } from './AdminOverridePanel';

export interface StudioPolicyEditorProps {
  initialConfig?: StudioPolicyConfigUI;
  initialOverride?: ProductionPolicyOverrideUI;
  productionId?: string;
  orgId?: string;
  isAdmin?: boolean;
  onSavePolicy?: (config: StudioPolicyConfigUI) => void;
  onCommitOverride?: (override: ProductionPolicyOverrideUI) => void;
}

const DEFAULT_CONFIG: StudioPolicyConfigUI = {
  policyId: 'pol_studio_theatrical_v1',
  orgId: 'org_paramount_global',
  profileType: 'major_theatrical',
  requiredMediaScopes: [...PROFILE_PRESETS.major_theatrical.requiredMediaScopes],
  distributionTerritories: [...PROFILE_PRESETS.major_theatrical.distributionTerritories],
  mandatoryPerpetualForTheatrical: true,
  prohibitUnvettedTrademarkFairUse: true,
  riskToleranceThreshold: 0.15,
  updatedAt: new Date().toISOString(),
};

function renderHeader(orgId: string, prodId: string, isAdmin: boolean, profileType: StudioProfileTypeUI) {
  const styles = getProfileBadgeStyles(profileType);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-800">
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
          <Building2 className="h-6 w-6" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-white tracking-wide">Studio Policy Administration</h2>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${styles.badgeClass}`}>
              {styles.label}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Studio: <span className="text-slate-300 font-semibold">{orgId}</span> &bull; Production:{' '}
            <span className="text-sky-400 font-semibold">{prodId}</span>
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 font-mono text-xs">
        {isAdmin ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-500/50">
            <Unlock className="h-3.5 w-3.5 text-emerald-400" /> Admin Clearance Authorized
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-950/80 text-amber-300 border border-amber-500/50">
            <Lock className="h-3.5 w-3.5 text-amber-400" /> Read-Only Counsel View
          </span>
        )}
      </div>
    </div>
  );
}

function renderPresetSection(currentType: StudioProfileTypeUI, onSelect: (t: StudioProfileTypeUI) => void) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
        <Sliders className="h-3.5 w-3.5 text-sky-400" /> Clearance Policy Tier Profiles
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {(['major_theatrical', 'streamer_exclusive', 'festival_acquisition'] as StudioProfileTypeUI[]).map((pType) => {
          const preset = PROFILE_PRESETS[pType];
          const pStyles = getProfileBadgeStyles(pType);
          const isSelected = currentType === pType;
          return (
            <button
              key={pType}
              type="button"
              onClick={() => onSelect(pType)}
              className={`p-2.5 rounded-xl border text-left transition-all ${
                isSelected
                  ? `${pStyles.badgeClass} ring-1 ring-white/20 shadow-lg scale-[1.01]`
                  : 'bg-slate-900/50 border-slate-800 hover:border-slate-700 text-slate-300'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-xs">{preset.title}</span>
                {isSelected && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-2">{preset.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export const StudioPolicyEditor: React.FC<StudioPolicyEditorProps> = ({
  initialConfig = DEFAULT_CONFIG,
  initialOverride,
  productionId = 'prod_noir_detective_2026',
  orgId = 'org_paramount_global',
  isAdmin = true,
  onSavePolicy,
  onCommitOverride,
}) => {
  const [config, setConfig] = useState<StudioPolicyConfigUI>(initialConfig);
  const [override, setOverride] = useState<ProductionPolicyOverrideUI>(
    initialOverride || {
      overrideId: 'ovr_none',
      productionId,
      orgId,
      adminActorName: '',
      rationale: '',
      overriddenMediaScopes: [],
      overriddenTerritories: [],
      allowTrademarkFairUse: false,
      waiverNotes: '',
      isActive: false,
    }
  );

  const handleSelectPreset = (pType: StudioProfileTypeUI) => {
    const preset = PROFILE_PRESETS[pType];
    setConfig((prev) => ({
      ...prev,
      profileType: pType,
      requiredMediaScopes: [...preset.requiredMediaScopes],
      distributionTerritories: [...preset.distributionTerritories],
      mandatoryPerpetualForTheatrical: preset.mandatoryPerpetualForTheatrical,
      prohibitUnvettedTrademarkFairUse: preset.prohibitUnvettedTrademarkFairUse,
      riskToleranceThreshold: preset.riskToleranceThreshold,
      updatedAt: new Date().toISOString(),
    }));
  };

  const handleToggleScope = (scope: LicensingScopeUI) => {
    setConfig((prev) => {
      const exists = prev.requiredMediaScopes.includes(scope);
      const updated = exists
        ? prev.requiredMediaScopes.filter((s) => s !== scope)
        : [...prev.requiredMediaScopes, scope];
      return { ...prev, profileType: 'custom', requiredMediaScopes: updated };
    });
  };

  const handleToggleTerritory = (territory: TerritoryScopeUI) => {
    setConfig((prev) => {
      const exists = prev.distributionTerritories.includes(territory);
      const updated = exists
        ? prev.distributionTerritories.filter((t) => t !== territory)
        : [...prev.distributionTerritories, territory];
      return { ...prev, profileType: 'custom', distributionTerritories: updated };
    });
  };

  return (
    <div className="w-full rounded-2xl bg-[#0b1120]/95 border border-slate-800/80 p-5 shadow-2xl backdrop-blur-xl text-slate-200 font-sans space-y-5">
      {renderHeader(orgId, productionId, isAdmin, config.profileType)}
      {renderPresetSection(config.profileType, handleSelectPreset)}
      <PolicyScopeMatrix
        config={config}
        onToggleMediaScope={handleToggleScope}
        onToggleTerritory={handleToggleTerritory}
        onTogglePerpetual={(val) =>
          setConfig((prev) => ({ ...prev, profileType: 'custom', mandatoryPerpetualForTheatrical: val }))
        }
        onToggleProhibitFairUse={(val) =>
          setConfig((prev) => ({ ...prev, profileType: 'custom', prohibitUnvettedTrademarkFairUse: val }))
        }
      />
      <AdminOverridePanel
        override={override}
        onChangeOverride={setOverride}
        isAdmin={isAdmin}
        productionId={productionId}
        onCommitOverride={onCommitOverride}
        onSavePolicy={onSavePolicy ? () => onSavePolicy(config) : undefined}
      />
    </div>
  );
};

export default StudioPolicyEditor;
