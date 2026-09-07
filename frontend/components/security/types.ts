/**
 * Lienmark Security & Threat Defense Types (Sprint 7.1)
 * Models for prompt injection trapping, intake anomalies, and security banners.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

export type SecurityFlagType =
  | 'PROMPT_INJECTION'
  | 'ZERO_CLAIMS_ANOMALY'
  | 'UNAUTHORIZED_DIRECTIVE';

export type SecuritySeverity = 'critical' | 'warning' | 'info';

export interface SecurityFlag {
  readonly type: SecurityFlagType;
  readonly label: string;
  readonly reasonCode: string;
  readonly severity: SecuritySeverity;
  readonly description: string;
}

export interface AnomalyPayload {
  readonly rawSnippet?: string;
  readonly matchedRules?: ReadonlyArray<string>;
  readonly confidenceScore?: number;
  readonly sceneRef?: string;
  readonly wordCount?: number;
  readonly sceneCount?: number;
  readonly ledgerEntryHash?: string;
}

export interface SecurityWarningProps {
  readonly flag: SecurityFlag;
  readonly anomaly?: AnomalyPayload;
  readonly ledgerHref?: string;
  readonly className?: string;
}

export function parseSecurityFlag(flaggedReason?: string | null): SecurityFlag | null {
  if (!flaggedReason) return null;
  const normalized = flaggedReason.toLowerCase().trim();

  if (
    normalized === 'suspicious_embedded_instruction' ||
    normalized.includes('prompt_injection') ||
    normalized.includes('injection') ||
    normalized.includes('adversarial')
  ) {
    return {
      type: 'PROMPT_INJECTION',
      label: '[PROMPT INJECTION TRAPPED]',
      reasonCode: 'suspicious_embedded_instruction',
      severity: 'critical',
      description:
        'Adversarial instruction neutralized: untrusted payload trapped by Layer-1 Intake Sentinel.',
    };
  }

  if (
    normalized === 'statistically_improbable_clean_script' ||
    normalized.includes('zero_claims') ||
    normalized.includes('clean_script') ||
    normalized.includes('anomaly')
  ) {
    return {
      type: 'ZERO_CLAIMS_ANOMALY',
      label: '[INTAKE ANOMALY: ZERO CLAIMS]',
      reasonCode: 'statistically_improbable_clean_script',
      severity: 'warning',
      description:
        'Statistical anomaly detected: script exceeds scene/word threshold but yielded zero claims.',
    };
  }

  return null;
}
