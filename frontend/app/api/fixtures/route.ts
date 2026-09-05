/**
 * Next.js App Router Route Handler: GET /api/fixtures
 * Returns the typed golden fixture state for the fictional production 'Shadows Over Broadway'.
 * Integrates with the FastAPI backend through the defensive API client with deterministic fallback.
 * Authored strictly under Google AntiGravity for Agentic Cinema compliance.
 */

import { NextResponse } from 'next/server';
import { apiClient } from '@/lib/api_client';
import { FixturesResponse } from '@/lib/types';
import { getGoldenFixturesResponse } from '@/lib/fixtures_data';

export const dynamic = 'force-dynamic';

/**
 * GET /api/fixtures
 * Returns version-bound locked script (V7) and production revision (V8) metadata
 * alongside the 12 canonical rights-bearing claims.
 */
export async function GET(): Promise<NextResponse<FixturesResponse | { error: string }>> {
  try {
    const data: FixturesResponse = await apiClient.getFixtures();
    return NextResponse.json(data, {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store, max-age=0',
        'X-Lienmark-Provider': 'Lienmark Clearance Engine',
      },
    });
  } catch (error: unknown) {
    console.error('[Route:GET /api/fixtures] Fallback to golden fixture state:', error);
    const fallbackData: FixturesResponse = getGoldenFixturesResponse();
    return NextResponse.json(fallbackData, {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'X-Lienmark-Source': 'deterministic-golden-fallback',
      },
    });
  }
}
