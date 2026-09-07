'use server';

/**
 * Lienmark Server Actions for Next.js 15 App Router
 * Evaluates clearance drift, counsel re-attestations, and Form E&O-2026.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import { revalidatePath, revalidateTag } from 'next/cache';
import { apiClient } from '@/lib/api_client';
import {
  AuditTrailResponse,
  DecisionState,
  DecisionStatus,
  DemoResetResponse,
  DemoSeedResponse,
  DemoStateResponse,
  DriftEvaluationResult,
  EvaluatedClaim,
  ExceptionsSchedule,
  ReattestationRequest,
  ReattestationResponse,
  ReviewAction,
  ReviewActionRequest,
  ReviewQueueItem,
  ReviewQueueResponse,
  SupersessionEvent,
} from '@/lib/types';

export interface ActionResponse<T> {
  readonly success: boolean;
  readonly data?: T;
  readonly error?: string;
  readonly details?: unknown;
}

export interface ClearanceStateData {
  readonly totalClaims: number;
  readonly carriedCount: number;
  readonly staleCount: number;
  readonly reattestedCount: number;
  readonly exceptionCount: number;
  readonly claims: EvaluatedClaim[];
}

export async function evaluateClearanceDeltaAction(
  targetVersionId: string = 'v8'
): Promise<ActionResponse<DriftEvaluationResult>> {
  try {
    const result = await apiClient.runDriftAnalysis(targetVersionId);
    return { success: true, data: result };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to evaluate clearance delta';
    return { success: false, error: message };
  }
}

export async function reattestClaimAction(
  request: ReattestationRequest
): Promise<ActionResponse<ReattestationResponse>> {
  if (!request?.stable_lineage_key || !request?.new_status) {
    return { success: false, error: 'Invalid request: stable_lineage_key and new_status required' };
  }
  if (!request.counsel_rationale || request.counsel_rationale.trim().length < 3) {
    return { success: false, error: 'Counsel rationale must be at least 3 characters' };
  }
  try {
    const response = await apiClient.submitReattestation({
      decision_id: request.decision_id || `dec_${request.stable_lineage_key}`,
      stable_lineage_key: request.stable_lineage_key,
      version_id: request.version_id || 'v8',
      new_status: request.new_status,
      counsel_rationale: request.counsel_rationale.trim(),
      reviewer_name: request.reviewer_name || 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
    });
    revalidatePath('/');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('exceptions-schedule');
    return { success: true, data: response };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to record counsel re-attestation';
    return { success: false, error: message };
  }
}

export async function getExceptionsScheduleAction(
  _productionId: string = 'proj_blockbuster_cinema'
): Promise<ActionResponse<ExceptionsSchedule>> {
  try {
    const schedule = await apiClient.getExceptionsSchedule();
    return { success: true, data: schedule };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to retrieve Exceptions Schedule';
    return { success: false, error: message };
  }
}

export async function fetchReviewQueueAction(): Promise<ActionResponse<ReviewQueueItem[]>> {
  try {
    const response: ReviewQueueResponse = await apiClient.getReviewQueue();
    // Deterministically preserve genuine empty list without silent golden fallback
    const items = Array.isArray(response?.items) ? response.items : [];
    return { success: true, data: items };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to retrieve review queue';
    return { success: false, error: message, data: [] };
  }
}

export async function submitReviewAction(
  action: 're_attest' | 'reject' | 'exception',
  lineageKey: string,
  rationale: string,
  reviewerName: string = 'Sarah Jenkins, Esq. (Lead Clearance Counsel)'
): Promise<ActionResponse<SupersessionEvent>> {
  const validActions = ['re_attest', 'reject', 'exception'];
  if (!validActions.includes(action) || !lineageKey?.trim()) {
    return { success: false, error: `Invalid review parameters: action=${action}, key=${lineageKey}` };
  }
  if (!rationale?.trim() || rationale.trim().length < 3) {
    return { success: false, error: 'Counsel rationale must be at least 3 characters' };
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
    const event = await apiClient.submitReviewAction(payload);
    revalidatePath('/');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('review-queue');
    revalidateTag('audit-trail');
    return { success: true, data: event };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to record clearance adjudication';
    return { success: false, error: message };
  }
}

export async function fetchAuditTrailAction(
  lineageKey?: string
): Promise<ActionResponse<SupersessionEvent[]>> {
  try {
    const response: AuditTrailResponse = await apiClient.getAuditTrail(lineageKey);
    // Explicitly return actual events list even if empty
    const events = Array.isArray(response?.events) ? response.events : [];
    return { success: true, data: events };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to retrieve audit trail';
    return { success: false, error: message, data: [] };
  }
}

export async function resetDemoAction(): Promise<ActionResponse<DemoResetResponse>> {
  try {
    const result = await apiClient.resetDemo();
    revalidatePath('/');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('clearance-state');
    return { success: true, data: result };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to reset demo state';
    return { success: false, error: message };
  }
}

export async function seedDemoAction(
  mode: 'baseline' | 'drifted' | 'resolved' | string
): Promise<ActionResponse<DemoSeedResponse>> {
  try {
    const result = await apiClient.seedDemo(mode);
    revalidatePath('/');
    revalidatePath('/report/proj_blockbuster_cinema');
    revalidateTag('clearance-state');
    return { success: true, data: result };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to seed demo mode';
    return { success: false, error: message };
  }
}

export async function getDemoStateAction(): Promise<ActionResponse<DemoStateResponse>> {
  try {
    const result = await apiClient.getDemoState();
    return { success: true, data: result };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to retrieve demo state';
    return { success: false, error: message };
  }
}

export async function fetchClearanceStateAction(
  _productionId: string = 'proj_blockbuster_cinema'
): Promise<ActionResponse<ClearanceStateData>> {
  try {
    const claims = await apiClient.getClaims();
    const claimsList = Array.isArray(claims) ? claims : [];
    const carriedCount = claimsList.filter((c) => c.state === DecisionState.CARRIED_FORWARD).length;
    const staleCount = claimsList.filter((c) => c.state === DecisionState.STALE).length;
    const reattestedCount = claimsList.filter((c) => c.state === DecisionState.RE_ATTESTED).length;
    const exceptionCount = claimsList.filter((c) => c.state === DecisionState.EXCEPTION).length;

    return {
      success: true,
      data: {
        totalClaims: claimsList.length,
        carriedCount,
        staleCount,
        reattestedCount,
        exceptionCount,
        claims: claimsList,
      },
    };
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Failed to retrieve clearance state';
    return { success: false, error: message };
  }
}
