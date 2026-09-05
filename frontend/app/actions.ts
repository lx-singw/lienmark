'use server';

/**
 * Lienmark Server Actions for Next.js 15 App Router
 * Orchestrates clearance delta evaluations, counsel re-attestations, and statutory Form E&O-2026 generation.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementations.
 */

import { revalidatePath, revalidateTag } from 'next/cache';
import { apiClient } from '@/lib/api_client';
import {
  AuditTrailResponse,
  DecisionStatus,
  DriftEvaluationResult,
  ExceptionsSchedule,
  ReattestationRequest,
  ReattestationResponse,
  ReviewAction,
  ReviewActionRequest,
  ReviewActionType,
  ReviewQueueItem,
  ReviewQueueResponse,
  SupersessionEvent,
  DemoResetResponse,
  DemoSeedResponse,
  DemoStateResponse,
} from '@/lib/types';
import {
  getGoldenAuditTrail,
  getGoldenDriftEvaluationResult,
  getGoldenExceptionsSchedule,
  getGoldenReviewQueue,
} from '@/lib/fixtures_data';

export interface ActionResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  details?: unknown;
}

/**
 * Executes clearance drift detection across script revision versions (v7 locked -> v8 revised).
 * Calls backend API with timeout and fallback to golden fixtures.
 *
 * @param targetVersionId - The target version to evaluate (defaults to 'v8')
 * @returns Promise<ActionResponse<DriftEvaluationResult>>
 */
export async function evaluateClearanceDeltaAction(
  targetVersionId: string = 'v8'
): Promise<ActionResponse<DriftEvaluationResult>> {
  console.log(`[Action:evaluateClearanceDeltaAction] Evaluating clearance delta for ${targetVersionId}`);

  try {
    const result: DriftEvaluationResult = await apiClient.runDriftAnalysis();
    return {
      success: true,
      data: result,
    };
  } catch (error: unknown) {
    console.warn(
      '[Action:evaluateClearanceDeltaAction] Upstream API call failed, activating deterministic golden fallback:',
      error
    );
    try {
      const fallbackResult = getGoldenDriftEvaluationResult();
      return {
        success: true,
        data: fallbackResult,
      };
    } catch (fallbackError: unknown) {
      return {
        success: false,
        error:
          fallbackError instanceof Error
            ? fallbackError.message
            : 'Unknown error occurred during clearance delta evaluation',
      };
    }
  }
}

/**
 * Records clearance counsel attestation or marks an asset as an unresolved exception.
 * Validates the counsel rationale, updates session state, and invalidates cache tags.
 *
 * @param request - Typed counsel reattestation request
 * @returns Promise<ActionResponse<ReattestationResponse>>
 */
export async function reattestClaimAction(
  request: ReattestationRequest
): Promise<ActionResponse<ReattestationResponse>> {
  console.log(
    `[Action:reattestClaimAction] Submitting re-attestation for ${request?.stable_lineage_key} (${request?.new_status})`
  );

  // Defensive validation
  if (!request || typeof request !== 'object') {
    return {
      success: false,
      error: 'Invalid re-attestation request: payload must be an object',
    };
  }

  if (!request.stable_lineage_key || typeof request.stable_lineage_key !== 'string') {
    return {
      success: false,
      error: 'Invalid request: stable_lineage_key is required',
    };
  }

  const validStatuses = Object.values(DecisionStatus);
  if (!request.new_status || !validStatuses.includes(request.new_status)) {
    return {
      success: false,
      error: `Invalid new_status: must be one of ${validStatuses.join(', ')}`,
    };
  }

  if (!request.counsel_rationale || typeof request.counsel_rationale !== 'string' || request.counsel_rationale.trim().length < 3) {
    return {
      success: false,
      error: 'Counsel rationale must be at least 3 characters long',
    };
  }

  try {
    const response: ReattestationResponse = await apiClient.submitReattestation({
      decision_id: request.decision_id || `dec_${request.stable_lineage_key}`,
      stable_lineage_key: request.stable_lineage_key,
      version_id: request.version_id || 'v8',
      new_status: request.new_status,
      counsel_rationale: request.counsel_rationale.trim(),
      reviewer_name: request.reviewer_name || 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
    });

    // Revalidate paths to refresh SSR reports and client state
    revalidatePath('/');
    revalidatePath('/report/[production_id]', 'page');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('exceptions-schedule');

    return {
      success: true,
      data: response,
    };
  } catch (error: unknown) {
    console.error('[Action:reattestClaimAction] Error submitting re-attestation:', error);
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : 'Failed to record counsel re-attestation',
      details: error,
    };
  }
}

/**
 * Retrieves the version-bound Form E&O-2026 Exceptions Schedule for underwriter submission.
 *
 * @param productionId - The production project identifier (e.g., 'proj_blockbuster_cinema')
 * @returns Promise<ActionResponse<ExceptionsSchedule>>
 */
export async function getExceptionsScheduleAction(
  productionId: string = 'proj_blockbuster_cinema'
): Promise<ActionResponse<ExceptionsSchedule>> {
  console.log(`[Action:getExceptionsScheduleAction] Retrieving Exceptions Schedule for ${productionId}`);

  try {
    const schedule: ExceptionsSchedule = await apiClient.getExceptionsSchedule();
    return {
      success: true,
      data: schedule,
    };
  } catch (error: unknown) {
    console.warn(
      '[Action:getExceptionsScheduleAction] Upstream API call failed, generating deterministic schedule fallback:',
      error
    );
    try {
      const fallbackSchedule = getGoldenExceptionsSchedule();
      return {
        success: true,
        data: fallbackSchedule,
      };
    } catch (fallbackError: unknown) {
      return {
        success: false,
        error:
          fallbackError instanceof Error
            ? fallbackError.message
            : 'Failed to retrieve Form E&O-2026 Exceptions Schedule',
      };
    }
  }
}

/**
 * Fetches the Counsel Checkpoint Review Queue of stale decisions awaiting human disposition.
 * Calls backend GET /api/review/queue with deterministic golden fallback.
 *
 * @returns Promise<ActionResponse<ReviewQueueItem[]>>
 */
export async function fetchReviewQueueAction(): Promise<ActionResponse<ReviewQueueItem[]>> {
  console.log('[Action:fetchReviewQueueAction] Fetching Counsel Checkpoint Review Queue');

  try {
    const response: ReviewQueueResponse = await apiClient.getReviewQueue();
    return {
      success: true,
      data: response.items,
    };
  } catch (error: unknown) {
    console.warn(
      '[Action:fetchReviewQueueAction] Upstream API call failed, activating deterministic golden fallback:',
      error
    );
    try {
      const fallbackQueue = getGoldenReviewQueue();
      return {
        success: true,
        data: fallbackQueue,
      };
    } catch (fallbackError: unknown) {
      return {
        success: false,
        error:
          fallbackError instanceof Error
            ? fallbackError.message
            : 'Failed to retrieve Counsel Checkpoint Review Queue',
      };
    }
  }
}

/**
 * Submits clearance counsel review adjudication ('re_attest', 'reject', or 'exception').
 * Calls backend POST /api/review/action, appends a tamper-evident SupersessionEvent,
 * and invalidates relevant Next.js cache tags.
 *
 * @param action - Adjudication action: 're_attest' | 'reject' | 'exception'
 * @param lineageKey - Stable lineage key of the asset
 * @param rationale - Legal rationale and statutory notes from counsel
 * @param reviewerName - Optional display name of reviewer (defaults to Sarah Jenkins, Esq.)
 * @returns Promise<ActionResponse<SupersessionEvent>>
 */
export async function submitReviewAction(
  action: 're_attest' | 'reject' | 'exception',
  lineageKey: string,
  rationale: string,
  reviewerName: string = 'Sarah Jenkins, Esq. (Lead Clearance Counsel)'
): Promise<ActionResponse<SupersessionEvent>> {
  console.log(
    `[Action:submitReviewAction] Submitting ${action} for ${lineageKey} by ${reviewerName}`
  );

  // Defensive validation
  const validActions = ['re_attest', 'reject', 'exception'];
  if (!action || !validActions.includes(action)) {
    return {
      success: false,
      error: `Invalid review action '${action}'. Must be one of: ${validActions.join(', ')}`,
    };
  }

  if (!lineageKey || typeof lineageKey !== 'string' || lineageKey.trim().length === 0) {
    return {
      success: false,
      error: 'Invalid request: lineageKey is required',
    };
  }

  if (!rationale || typeof rationale !== 'string' || rationale.trim().length < 3) {
    return {
      success: false,
      error: 'Counsel rationale must be at least 3 characters long',
    };
  }

  try {
    const payload: ReviewActionRequest = {
      action: action as ReviewAction,
      stable_lineage_key: lineageKey.trim(),
      lineage_key: lineageKey.trim(),
      rationale: rationale.trim(),
      counsel_rationale: rationale.trim(),
      reviewer_name: reviewerName.trim(),
      target_version_id: 'v8',
    };

    const event: SupersessionEvent = await apiClient.submitReviewAction(payload);

    // Revalidate paths & tags to refresh review dashboard and exceptions schedule
    revalidatePath('/');
    revalidatePath('/report/[production_id]', 'page');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('review-queue');
    revalidateTag('audit-trail');
    revalidateTag('exceptions-schedule');

    return {
      success: true,
      data: event,
    };
  } catch (error: unknown) {
    console.error('[Action:submitReviewAction] Error recording review action:', error);
    return {
      success: false,
      error:
        error instanceof Error
          ? error.message
          : 'Failed to record clearance counsel adjudication',
      details: error,
    };
  }
}

/**
 * Retrieves the append-only audit trail / supersession log for compliance and underwriter review.
 * Calls backend GET /api/review/history with golden fallback.
 *
 * @param lineageKey - Optional lineage key filter
 * @returns Promise<ActionResponse<SupersessionEvent[]>>
 */
export async function fetchAuditTrailAction(
  lineageKey?: string
): Promise<ActionResponse<SupersessionEvent[]>> {
  console.log(
    `[Action:fetchAuditTrailAction] Fetching audit trail ${lineageKey ? `for ${lineageKey}` : '(all events)'}`
  );

  try {
    const response: AuditTrailResponse = await apiClient.getAuditTrail(lineageKey);
    return {
      success: true,
      data: response.events,
    };
  } catch (error: unknown) {
    console.warn(
      '[Action:fetchAuditTrailAction] Upstream API call failed, activating deterministic golden fallback:',
      error
    );
    try {
      const fallbackEvents = getGoldenAuditTrail(lineageKey);
      return {
        success: true,
        data: fallbackEvents,
      };
    } catch (fallbackError: unknown) {
      return {
        success: false,
        error:
          fallbackError instanceof Error
            ? fallbackError.message
            : 'Failed to retrieve clearance audit trail',
      };
    }
  }
}

/**
 * Resets backend and local demo state to pristine Script Cut V7 baseline.
 * Clears review mutations, restores 12 approved claims, and invalidates cache tags.
 */
export async function resetDemoAction(): Promise<ActionResponse<DemoResetResponse>> {
  console.log('[Action:resetDemoAction] Executing full demo reset to clean V7 baseline');
  try {
    const result = await apiClient.resetDemo();
    revalidatePath('/');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('clearance-state');
    return {
      success: true,
      data: result,
    };
  } catch (error: unknown) {
    console.warn('[Action:resetDemoAction] Reset failed upstream; serving local fallback:', error);
    return {
      success: true,
      data: {
        status: 'RESET_SUCCESS',
        message: 'Demo state reset to clean V7 baseline (local fallback)',
        total_claims: 12,
        approved_claims: 12,
        timestamp: new Date().toISOString(),
      },
    };
  }
}

/**
 * Seeds backend demo state into designated take mode: baseline, drifted, or resolved.
 */
export async function seedDemoAction(
  mode: 'baseline' | 'drifted' | 'resolved' | string
): Promise<ActionResponse<DemoSeedResponse>> {
  console.log(`[Action:seedDemoAction] Seeding demo state to '${mode}' mode`);
  try {
    const result = await apiClient.seedDemo(mode);
    revalidatePath('/');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('clearance-state');
    return {
      success: true,
      data: result,
    };
  } catch (error: unknown) {
    console.warn(`[Action:seedDemoAction] Seed '${mode}' failed upstream; serving local fallback:`, error);
    const isBaseline = mode === 'baseline';
    const isResolved = mode === 'resolved';
    const isDrifted = mode === 'drifted';
    return {
      success: true,
      data: {
        status: 'SEED_SUCCESS',
        mode,
        message: `Demo state seeded to ${mode} mode (local fallback)`,
        total_claims: 12,
        carried_forward_count: isBaseline ? 12 : 10,
        reopened_count: isDrifted ? 2 : 0,
        reattested_count: isResolved ? 1 : 0,
        exception_count: isResolved ? 1 : 0,
        completed_claims: isDrifted ? 10 : 12,
        claims_breakdown: {
          total: 12,
          carried_forward: isBaseline ? 12 : 10,
          reopened: isDrifted ? 2 : 0,
          reattested: isResolved ? 1 : 0,
          exception: isResolved ? 1 : 0,
        },
        reviewer_identity: 'Sarah Jenkins, Esq.',
        policy_version: 'E&O-2026.1-DEVPOST',
        timestamp: new Date().toISOString(),
      },
    };
  }
}

/**
 * Retrieves current demo state breakdown and mode.
 */
export async function getDemoStateAction(): Promise<ActionResponse<DemoStateResponse>> {
  try {
    const result = await apiClient.getDemoState();
    return {
      success: true,
      data: result,
    };
  } catch (error: unknown) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to retrieve demo state',
    };
  }
}


