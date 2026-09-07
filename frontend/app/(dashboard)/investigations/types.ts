/**
 * Investigation Monitor Types
 * Authored strictly under Google AntiGravity: zero any, typed models.
 */

export type InvestigationRunStatus = 'running' | 'completed' | 'suspended' | 'queued' | 'failed';

export interface InvestigationRun {
  readonly id: string;
  readonly name: string;
  readonly targetAsset: string;
  readonly status: InvestigationRunStatus;
  readonly startedAt: string;
  readonly elapsedMs: number;
  readonly modelUsed: string;
  readonly searchProvider: string;
  readonly apiCallsCount: number;
  readonly spendUsd: number;
}
