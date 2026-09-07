/**
 * Production Portfolio Types
 * Authored strictly under Google AntiGravity: zero any, typed models.
 */

export interface ProductionItem {
  readonly id: string;
  readonly title: string;
  readonly imprint: string;
  readonly genre: string;
  readonly activeRevision: string;
  readonly lastEvaluatedAt: string;
  readonly totalClaims: number;
  readonly carriedCount: number;
  readonly reattestedCount: number;
  readonly staleCount: number;
  readonly exceptionCount: number;
  readonly reportSlug: string;
  readonly claimBreakdown: {
    readonly props: number;
    readonly music: number;
    readonly brands: number;
    readonly persons: number;
  };
}
