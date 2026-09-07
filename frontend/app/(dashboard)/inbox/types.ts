/**
 * Inbox Triage Types
 * Authored strictly under Google AntiGravity: zero any, typed models.
 */

export type TriageType = 'claim' | 'clarification' | 'budget';
export type TriageSeverity = 'blocker' | 'high' | 'medium' | 'low';

export interface TriageItem {
  readonly id: string;
  readonly type: TriageType;
  readonly title: string;
  readonly subtitle: string;
  readonly description: string;
  readonly severity: TriageSeverity;
  readonly sceneOrTimecode?: string;
  readonly assetType?: string;
  readonly suggestedAction?: string;
  readonly options?: ReadonlyArray<string>;
  readonly currentAmount?: string;
  readonly requestedAmount?: string;
  readonly lineageKey?: string;
  readonly createdAt: string;
}
