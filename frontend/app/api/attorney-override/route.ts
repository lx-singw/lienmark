/**
 * Next.js App Router Route Handler: POST /api/attorney-override
 * Defensively handles counsel re-attestations and unresolved exception designations.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementations.
 */

import { NextResponse } from 'next/server';
import { revalidatePath, revalidateTag } from 'next/cache';
import { apiClient } from '@/lib/api_client';
import { DecisionStatus, ReattestationRequest, ReattestationResponse } from '@/lib/types';

export const dynamic = 'force-dynamic';

export async function POST(
  request: Request
): Promise<NextResponse<ReattestationResponse | { error: string; details?: unknown }>> {
  try {
    let body: unknown;
    const rawText = await request.text();
    try {
      body = rawText ? JSON.parse(rawText) : {};
    } catch (parseErr) {
      return NextResponse.json(
        { error: 'Invalid JSON payload received in request body', details: String(parseErr), raw: rawText },
        { status: 400 }
      );
    }

    if (typeof body !== 'object' || body === null) {
      return NextResponse.json(
        { error: 'Malformed request: payload must be a JSON object' },
        { status: 400 }
      );
    }

    const payload = body as Record<string, unknown>;
    const {
      decision_id,
      stable_lineage_key,
      version_id,
      new_status,
      counsel_rationale,
      reviewer_name,
    } = payload;

    // Defensive validation
    if (!stable_lineage_key || typeof stable_lineage_key !== 'string' || !stable_lineage_key.trim()) {
      return NextResponse.json(
        { error: 'Missing or invalid field: stable_lineage_key is required' },
        { status: 400 }
      );
    }

    const validStatuses = Object.values(DecisionStatus);
    if (!new_status || !validStatuses.includes(new_status as DecisionStatus)) {
      return NextResponse.json(
        {
          error: `Invalid new_status '${String(new_status)}'. Must be one of: ${validStatuses.join(', ')}`,
        },
        { status: 400 }
      );
    }

    if (
      !counsel_rationale ||
      typeof counsel_rationale !== 'string' ||
      counsel_rationale.trim().length < 3
    ) {
      return NextResponse.json(
        { error: 'counsel_rationale must be a non-empty string of at least 3 characters' },
        { status: 400 }
      );
    }

    const sanitizedRequest: ReattestationRequest = {
      decision_id:
        typeof decision_id === 'string' && decision_id.trim()
          ? decision_id.trim()
          : `dec_${stable_lineage_key.trim()}`,
      stable_lineage_key: stable_lineage_key.trim(),
      version_id: typeof version_id === 'string' && version_id.trim() ? version_id.trim() : 'v8',
      new_status: new_status as DecisionStatus,
      counsel_rationale: counsel_rationale.trim(),
      reviewer_name:
        typeof reviewer_name === 'string' && reviewer_name.trim()
          ? reviewer_name.trim()
          : 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
    };

    const response: ReattestationResponse = await apiClient.submitReattestation(sanitizedRequest);

    // Revalidate paths for real-time consistency
    try {
      revalidatePath('/');
      revalidatePath('/report/[production_id]', 'page');
      revalidatePath('/report/proj_blockbuster_cinema');
      revalidateTag('exceptions-schedule');
    } catch (revalError) {
      console.warn('[Route:POST /api/attorney-override] Path revalidation notice:', revalError);
    }

    return NextResponse.json(response, {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, max-age=0',
        'X-Lienmark-Attestation': 'recorded',
      },
    });
  } catch (error: unknown) {
    console.error('[Route:POST /api/attorney-override] Unhandled exception:', error);
    const errorMessage = error instanceof Error ? error.message : 'Internal server error';
    return NextResponse.json(
      {
        error: 'Failed to process counsel attestation override',
        details: errorMessage,
      },
      { status: 500 }
    );
  }
}
