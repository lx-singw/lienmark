/**
 * policy_types.ts
 * Studio Policy Administrative Governance Type Definitions.
 * Sprint 5.1 Studio Policy Engine & Governance Invariants.
 * Files <= 250 lines, functions <= 40 lines, zero-any TypeScript.
 */

export type LicensingScopeUI =
  | 'theatrical'
  | 'svod'
  | 'avod'
  | 'linear_broadcast'
  | 'in_flight'
  | 'promotional_trailer';

export type TerritoryScopeUI =
  | 'worldwide'
  | 'north_america'
  | 'emea'
  | 'latam'
  | 'apac';

export type StudioProfileTypeUI =
  | 'major_theatrical'
  | 'streamer_exclusive'
  | 'festival_acquisition'
  | 'custom';

export interface StudioPolicyConfigUI {
  policyId: string;
  orgId: string;
  profileType: StudioProfileTypeUI;
  requiredMediaScopes: LicensingScopeUI[];
  distributionTerritories: TerritoryScopeUI[];
  mandatoryPerpetualForTheatrical: boolean;
  prohibitUnvettedTrademarkFairUse: boolean;
  riskToleranceThreshold: number; // 0.00 to 1.00
  updatedAt: string;
}

export interface ProductionPolicyOverrideUI {
  overrideId: string;
  productionId: string;
  orgId: string;
  adminActorName: string;
  rationale: string;
  overriddenMediaScopes: LicensingScopeUI[];
  overriddenTerritories: TerritoryScopeUI[];
  allowTrademarkFairUse: boolean;
  waiverNotes: string;
  appliedAt?: string;
  ledgerEventId?: string;
  isActive?: boolean;
}

export type PolicyViolationSeverityUI = 'critical' | 'warning' | 'info';

export interface PolicyViolationUI {
  ruleCode: string;
  severity: PolicyViolationSeverityUI;
  message: string;
  remedy: string;
}

export interface PolicyEvaluationResultUI {
  isCompliant: boolean;
  violations: PolicyViolationUI[];
  effectivePolicyId: string;
  requiresSpecialWaiver: boolean;
}

export interface ProfilePresetDefinitionUI {
  profileType: StudioProfileTypeUI;
  title: string;
  subtitle: string;
  description: string;
  requiredMediaScopes: LicensingScopeUI[];
  distributionTerritories: TerritoryScopeUI[];
  mandatoryPerpetualForTheatrical: boolean;
  prohibitUnvettedTrademarkFairUse: boolean;
  riskToleranceThreshold: number;
}

export interface PolicyValidationResultUI {
  isValid: boolean;
  errors: string[];
}
