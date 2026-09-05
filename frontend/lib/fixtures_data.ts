/**
 * Lienmark Golden Dataset & Fixtures Constants
 * Fictional film production 'Shadows Over Broadway' across Version 7 and Version 8.
 * Provides typed, deterministic baseline and fallback fixtures for the Next.js frontend.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementations.
 */

import {
  ActorType,
  ChangeKind,
  ClearanceBriefing,
  CounselDecision,
  CreativeDelta,
  CreativeUse,
  DecisionState,
  DecisionStatus,
  DriftEvaluationResult,
  EvaluatedClaim,
  EvidenceCitation,
  EvidenceStance,
  ExceptionsSchedule,
  ExceptionsScheduleItem,
  ExplanationFourDimensions,
  FixturesResponse,
  HealthCheckResponse,
  PriorDecisionDetails,
  ProductionVersion,
  PublicEvidenceSnapshot,
  ReviewActionType,
  ReviewQueueItem,
  SupersessionEvent,
  V7ClaimFixture,
  WorkflowStepTrace,
} from './types';

// ============================================================================
// Production Versions
// ============================================================================

export const GOLDEN_V7_VERSION: ProductionVersion = {
  version_id: 'v7',
  project_id: 'proj_blockbuster_cinema',
  label: 'Shadows Over Broadway - Locked Script v7',
  created_at: '2026-09-01T10:00:00.000Z',
  content_hash: 'a1b2c3d4e5f60718293a4b5c6d7e8f90',
  parent_version_id: null,
  source_type: 'screenplay',
};

export const GOLDEN_V8_VERSION: ProductionVersion = {
  version_id: 'v8',
  project_id: 'proj_blockbuster_cinema',
  label: 'Shadows Over Broadway - Production Revision v8',
  created_at: '2026-09-03T14:30:00.000Z',
  content_hash: 'f9e8d7c6b5a43210fedcba9876543210',
  parent_version_id: 'v7',
  source_type: 'screenplay',
};

// ============================================================================
// 12 Baseline V7 Claims Fixture
// ============================================================================

export const GOLDEN_V7_CLAIMS: V7ClaimFixture[] = [
  {
    use_id: 'use_v7_prop_vintage_telephone',
    key: 'prop_vintage_telephone',
    scene: 'Scene 04 - Detective Office',
    asset_type: 'prop',
    description: '1950s Western Electric Rotary Phone prop on mahogany desk.',
    prominence: 'Incidental background set dressing, 4s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_poster_paris_expo_1937',
    key: 'poster_paris_expo_1937',
    scene: 'Scene 08 - Hotel Corridor',
    asset_type: 'artwork',
    description: 'Framed vintage reproduction poster of 1937 Paris Exposition.',
    prominence: 'Background hallway blur, 3s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_car_ford_sedan_1949',
    key: 'car_ford_sedan_1949',
    scene: 'Scene 12 - Street Exterior',
    asset_type: 'prop',
    description: '1949 Ford Custom Tudor Sedan parked curbside under streetlamp.',
    prominence: 'Exterior street background, 6s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_trademark_acme_coffee',
    key: 'trademark_acme_coffee',
    scene: 'Scene 15 - Diner Booth',
    asset_type: 'trademark',
    description: 'Fictional Acme Coffee enamel sign painted on wall above booth.',
    prominence: 'Set dressing background, 5s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_artwork_abstract_expressionist',
    key: 'artwork_abstract_expressionist',
    scene: 'Scene 21 - Penthouse Loft',
    asset_type: 'artwork',
    description: 'Abstract expressionist oil canvas hanging behind executive desk.',
    prominence: 'Medium shot background, 8s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_likeness_mayor_cameo',
    key: 'likeness_mayor_cameo',
    scene: 'Scene 26 - Courtroom Gallery',
    asset_type: 'likeness',
    description: 'Background courtroom gallery extra resembling former city mayor.',
    prominence: 'Crowd scene background, 2s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_architecture_tribunal_facade',
    key: 'architecture_tribunal_facade',
    scene: 'Scene 30 - Civic Center',
    asset_type: 'location',
    description: 'Exterior historic facade of county courthouse.',
    prominence: 'Establishing wide exterior, 3s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_text_headline_gazette',
    key: 'text_headline_gazette',
    scene: 'Scene 34 - Newsstand',
    asset_type: 'text',
    description: "Prop newspaper headline reading 'MYSTERY WITNESS DISAPPEARS'.",
    prominence: 'Inserts prop, 2s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_wardrobe_fedora_brand',
    key: 'wardrobe_fedora_brand',
    scene: 'Scene 38 - Subway Platform',
    asset_type: 'trademark',
    description: 'Vintage Borsalino fedora hat worn by secondary character.',
    prominence: 'Character wardrobe, 10s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_music_incidental_radio_static',
    key: 'music_incidental_radio_static',
    scene: 'Scene 40 - Safehouse',
    asset_type: 'music',
    description: 'Foley ambient vintage radio broadcast static and low hum.',
    prominence: 'Incidental background audio, 12s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_poster_noir_detective_magazine',
    key: 'poster_noir_detective_magazine',
    scene: 'Scene 42 - 00:44:12',
    asset_type: 'artwork',
    description: "1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
    prominence: 'Out-of-focus background blur, 2s',
    status: 'APPROVED',
  },
  {
    use_id: 'use_v7_music_cue_midnight_serenade',
    key: 'music_cue_midnight_serenade',
    scene: 'Scene 18 - 00:19:40',
    asset_type: 'music',
    description: "'Midnight Serenade' jazz composition melody.",
    prominence: 'Background jazz trio performance in speakeasy, 20s',
    status: 'APPROVED',
  },
];

// ============================================================================
// Fallback Responses
// ============================================================================

export function getGoldenFixturesResponse(): FixturesResponse {
  return {
    v7_version: { ...GOLDEN_V7_VERSION },
    v8_version: { ...GOLDEN_V8_VERSION },
    v7_claims: GOLDEN_V7_CLAIMS.map((claim) => ({ ...claim })),
  };
}

export function getGoldenHealthResponse(): HealthCheckResponse {
  return {
    status: 'healthy',
    service: 'Lienmark E&O Clearance Change Control',
    provenance: 'Google AntiGravity (Agentic Cinema Approved Toolchain)',
    track: 'Parallel Track ($15,000 Prize Pool)',
    integrations: {
      gemini: 'configured',
      parallel_search: 'configured',
      agent_platform: 'Google Cloud Agent Builder / ADK',
    },
    policy_version: 'E&O-2026.1-DEVPOST',
  };
}

export function getGoldenDriftEvaluationResult(): DriftEvaluationResult {
  const traces: WorkflowStepTrace[] = [
    {
      step_name: 'version_ingestion',
      component: 'LienmarkEngine',
      status: 'SUCCESS',
      duration_ms: 12.4,
      details: { v7_uses: 12, v8_uses: 12 },
    },
    {
      step_name: 'semantic_delta_analysis',
      component: 'Gemini 2.5 Flash',
      status: 'SUCCESS',
      duration_ms: 184.2,
      details: {
        is_material: true,
        prominence_shift:
          'Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue.',
        recommended_action: 'revalidate',
      },
    },
    {
      step_name: 'deterministic_dependency_invalidation',
      component: 'InvalidationEngine',
      status: 'SUCCESS',
      duration_ms: 8.5,
      details: {
        carried_forward: 10,
        reopened: 2,
        policy: 'E&O-2026.1-DEVPOST',
      },
    },
    {
      step_name: 'parallel_targeted_search_poster_noir_detective_magazine',
      component: 'Parallel Search API',
      status: 'SUCCESS',
      duration_ms: 142.5,
      details: {
        query: 'Crime Detective Magazine 1946 Shadows Over Broadway copyright renewal',
        source_title: 'US Copyright Office Historical Catalog - Renewal Records',
        source_url: 'https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective',
        stance: 'supporting',
        provider_call_id: 'prl_call_882910_poster',
      },
    },
    {
      step_name: 'parallel_targeted_search_music_cue_midnight_serenade',
      component: 'Parallel Search API',
      status: 'SUCCESS',
      duration_ms: 178.2,
      details: {
        query: 'Midnight Serenade jazz sync rights copyright owner 2026',
        source_title: 'ASCAP ACE Repertory & Billboard Rights Bulletin',
        source_url: 'https://ascap.com/ace-title-search/midnight-serenade-9921',
        stance: 'contradictory',
        provider_call_id: 'prl_call_993012_music',
      },
    },
  ];

  const counselBriefings: Record<string, ClearanceBriefing> = {
    poster_noir_detective_magazine: {
      claim_id: 'poster_noir_detective_magazine',
      asset_name: '1946 Crime Detective Magazine cover poster',
      counsel_summary:
        'Scene 42 focal dialogue escalation invalidates de minimis defense, but US Copyright Office records retrieved by Parallel confirm 1946 registration lapsed without renewal in 1974. Cover art is public domain.',
      parallel_evidence_stance: 'SUPPORTING',
      suggested_counsel_action:
        'Re-attest as APPROVED under Public Domain doctrine; attach LOC registration excerpt to exceptions schedule.',
      confidence: 0.96,
    },
    music_cue_midnight_serenade: {
      claim_id: 'music_cue_midnight_serenade',
      asset_name: "'Midnight Serenade' jazz composition melody",
      counsel_summary:
        'Prior public domain attestation invalid: Vanguard Media Holdings acquired exclusive worldwide synchronization rights as of August 2026.',
      parallel_evidence_stance: 'CONTRADICTORY',
      suggested_counsel_action:
        'Mark as UNRESOLVED EXCEPTION on Form E&O; initiate master license negotiation or replace cue with cleared alternate.',
      confidence: 0.98,
    },
  };

  const claims: EvaluatedClaim[] = [
    {
      stable_lineage_key: 'prop_vintage_telephone',
      asset_type: 'prop',
      description: '1950s Western Electric Rotary Phone prop on mahogany desk.',
      scene: 'Scene 04 - Detective Office',
      prominence: 'Incidental background set dressing, 4s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: prop_vintage_telephone',
        source_url: 'https://records.publicdomain.org/prop_vintage_telephone',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 110,
        call_id: 'prl_call_prop_vintage_telephone',
      },
    },
    {
      stable_lineage_key: 'poster_paris_expo_1937',
      asset_type: 'artwork',
      description: 'Framed vintage reproduction poster of 1937 Paris Exposition.',
      scene: 'Scene 08 - Hotel Corridor',
      prominence: 'Background hallway blur, 3s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: poster_paris_expo_1937',
        source_url: 'https://records.publicdomain.org/poster_paris_expo_1937',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 95,
        call_id: 'prl_call_poster_paris_expo_1937',
      },
    },
    {
      stable_lineage_key: 'car_ford_sedan_1949',
      asset_type: 'prop',
      description: '1949 Ford Custom Tudor Sedan parked curbside under streetlamp.',
      scene: 'Scene 12 - Street Exterior',
      prominence: 'Exterior street background, 6s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: car_ford_sedan_1949',
        source_url: 'https://records.publicdomain.org/car_ford_sedan_1949',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 102,
        call_id: 'prl_call_car_ford_sedan_1949',
      },
    },
    {
      stable_lineage_key: 'trademark_acme_coffee',
      asset_type: 'trademark',
      description: 'Fictional Acme Coffee enamel sign painted on wall above booth.',
      scene: 'Scene 15 - Diner Booth',
      prominence: 'Set dressing background, 5s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: trademark_acme_coffee',
        source_url: 'https://records.publicdomain.org/trademark_acme_coffee',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 120,
        call_id: 'prl_call_trademark_acme_coffee',
      },
    },
    {
      stable_lineage_key: 'artwork_abstract_expressionist',
      asset_type: 'artwork',
      description: 'Abstract expressionist oil canvas hanging behind executive desk.',
      scene: 'Scene 21 - Penthouse Loft',
      prominence: 'Medium shot background, 8s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: artwork_abstract_expressionist',
        source_url: 'https://records.publicdomain.org/artwork_abstract_expressionist',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 88,
        call_id: 'prl_call_artwork_abstract_expressionist',
      },
    },
    {
      stable_lineage_key: 'likeness_mayor_cameo',
      asset_type: 'likeness',
      description: 'Background courtroom gallery extra resembling former city mayor.',
      scene: 'Scene 26 - Courtroom Gallery',
      prominence: 'Crowd scene background, 2s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: likeness_mayor_cameo',
        source_url: 'https://records.publicdomain.org/likeness_mayor_cameo',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 99,
        call_id: 'prl_call_likeness_mayor_cameo',
      },
    },
    {
      stable_lineage_key: 'architecture_tribunal_facade',
      asset_type: 'location',
      description: 'Exterior historic facade of county courthouse.',
      scene: 'Scene 30 - Civic Center',
      prominence: 'Establishing wide exterior, 3s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: architecture_tribunal_facade',
        source_url: 'https://records.publicdomain.org/architecture_tribunal_facade',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 104,
        call_id: 'prl_call_architecture_tribunal_facade',
      },
    },
    {
      stable_lineage_key: 'text_headline_gazette',
      asset_type: 'text',
      description: "Prop newspaper headline reading 'MYSTERY WITNESS DISAPPEARS'.",
      scene: 'Scene 34 - Newsstand',
      prominence: 'Inserts prop, 2s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: text_headline_gazette',
        source_url: 'https://records.publicdomain.org/text_headline_gazette',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 115,
        call_id: 'prl_call_text_headline_gazette',
      },
    },
    {
      stable_lineage_key: 'wardrobe_fedora_brand',
      asset_type: 'trademark',
      description: 'Vintage Borsalino fedora hat worn by secondary character.',
      scene: 'Scene 38 - Subway Platform',
      prominence: 'Character wardrobe, 10s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: wardrobe_fedora_brand',
        source_url: 'https://records.publicdomain.org/wardrobe_fedora_brand',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 91,
        call_id: 'prl_call_wardrobe_fedora_brand',
      },
    },
    {
      stable_lineage_key: 'music_incidental_radio_static',
      asset_type: 'music',
      description: 'Foley ambient vintage radio broadcast static and low hum.',
      scene: 'Scene 40 - Safehouse',
      prominence: 'Incidental background audio, 12s',
      state: DecisionState.CARRIED_FORWARD,
      reason_code: 'DEPENDENCIES_SATISFIED_UNCHANGED',
      revalidation_action: 'carry',
      evidence: {
        provider: 'Parallel',
        source_title: 'Public Registry Archive: music_incidental_radio_static',
        source_url: 'https://records.publicdomain.org/music_incidental_radio_static',
        excerpt: 'No active copyright or trademark conflicts registered.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 108,
        call_id: 'prl_call_music_incidental_radio_static',
      },
    },
    {
      stable_lineage_key: 'poster_noir_detective_magazine',
      asset_type: 'artwork',
      description: "1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'.",
      scene: 'Scene 42 - 00:44:12',
      prominence: 'Featured close-up focal shot with dialogue, 14s',
      state: DecisionState.STALE,
      reason_code: 'CREATIVE_CONTEXT_ALTERED',
      revalidation_action: 'revalidate',
      evidence: {
        provider: 'Parallel',
        source_title: 'US Copyright Office Historical Catalog - Renewal Records',
        source_url: 'https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective',
        excerpt:
          'Registration #B-1946-8821 expired 1974 without timely renewal. Cover artwork in public domain in the United States.',
        stance: EvidenceStance.SUPPORTING,
        latency_ms: 142.5,
        call_id: 'prl_call_882910_poster',
      },
    },
    {
      stable_lineage_key: 'music_cue_midnight_serenade',
      asset_type: 'music',
      description: "'Midnight Serenade' jazz composition melody.",
      scene: 'Scene 18 - 00:19:40',
      prominence: 'Background jazz trio performance in speakeasy, 20s',
      state: DecisionState.STALE,
      reason_code: 'EXTERNAL_EVIDENCE_SHIFT',
      revalidation_action: 'revalidate',
      evidence: {
        provider: 'Parallel',
        source_title: 'ASCAP ACE Repertory & Billboard Rights Bulletin',
        source_url: 'https://ascap.com/ace-title-search/midnight-serenade-9921',
        excerpt:
          'Worldwide exclusive synchronization and master rights assigned August 2026 to Vanguard Media Holdings LLC (Administered by Kobalt Music). Prior public domain assertions disputed under European term extension.',
        stance: EvidenceStance.CONTRADICTORY,
        latency_ms: 178.2,
        call_id: 'prl_call_993012_music',
      },
    },
  ];

  return {
    run_id: 'run_golden_fallback_01',
    base_version: 'v7',
    target_version: 'v8',
    total_claims: 12,
    carried_forward_count: 10,
    reopened_count: 2,
    claims,
    counsel_briefings: counselBriefings,
    execution_traces: traces,
    total_duration_ms: 525.8,
  };
}

export function getGoldenExceptionsSchedule(
  reattestations: Record<string, { status: DecisionStatus; rationale: string }> = {}
): ExceptionsSchedule {
  const baseClaims = getGoldenDriftEvaluationResult().claims;
  let carried = 0;
  let reopened = 0;
  let reattested = 0;
  let exceptions = 0;

  const items: ExceptionsScheduleItem[] = baseClaims.map((claim) => {
    let evalState: string = claim.state;
    let action: string;
    let reason: string | null = null;

    if (claim.state === DecisionState.CARRIED_FORWARD) {
      carried++;
      action = 'Carried forward unchanged from prior approved counsel attestation.';
    } else {
      reopened++;
      const userReattest = reattestations[claim.stable_lineage_key];
      if (userReattest) {
        if (userReattest.status === DecisionStatus.APPROVED) {
          evalState = DecisionState.RE_ATTESTED;
          reattested++;
          action = `Re-attested by Clearance Counsel: ${userReattest.rationale}`;
        } else {
          evalState = DecisionState.EXCEPTION;
          exceptions++;
          action = `Marked as UNRESOLVED EXCEPTION by Clearance Counsel: ${userReattest.rationale}`;
        }
      } else {
        evalState = DecisionState.EXCEPTION;
        exceptions++;
        reason = claim.reason_code;
        action = 'Pending counsel re-attestation following detected drift.';
      }
    }

    const citations: EvidenceCitation[] = claim.evidence
      ? [
          {
            source_title: claim.evidence.source_title,
            source_url: claim.evidence.source_url,
            excerpt: claim.evidence.excerpt,
            provider: claim.evidence.provider,
          },
        ]
      : [];

    return {
      stable_lineage_key: claim.stable_lineage_key,
      asset_type: claim.asset_type,
      description: claim.description,
      scene_or_timecode: claim.scene,
      v7_decision_status: 'APPROVED',
      v8_evaluation_state: evalState,
      invalidation_reason: reason,
      counsel_action: action,
      evidence_citations: citations,
    };
  });

  const unresolvedList = items.filter((it) => it.v8_evaluation_state === DecisionState.EXCEPTION);

  return {
    schedule_id: 'sched_proj_blockbuster_cinema_v8_fallback',
    project_id: 'proj_blockbuster_cinema',
    project_name: 'Lienmark Production Digital Twin',
    target_version_id: 'v8',
    base_version_id: 'v7',
    generated_at: new Date().toISOString(),
    policy_version: 'E&O-2026.1-DEVPOST',
    policy_number: 'E&O-2026.1-DEVPOST',
    carrier_header: {
      carrier_name: 'Standard Entertainment & Media Underwriters Syndicate',
      policy_number: 'E&O-2026.1-DEVPOST',
      broker_name: 'Gallagher / Front Row Insurance Brokers',
      warranty_clause: 'Warranted clearance schedule of exceptions; uncleared and unlisted rights are excluded from coverage.',
      underwriter_status: 'PENDING_REVIEW',
    },
    production_metadata: {
      production_title: 'Shadows Over Broadway',
      project_id: 'proj_blockbuster_cinema',
      base_version_id: 'v7',
      target_version_id: 'v8',
      target_cut_hash: 'f9e8d7c6b5a43210fedcba9876543210',
    },
    total_claims: 12,
    carried_forward_count: carried,
    reopened_count: reopened,
    re_attested_count: reattested,
    unresolved_exception_count: exceptions,
    items,
    unresolved_exceptions_schedule: unresolvedList,
    unresolved_exceptions: unresolvedList,
  };
}

// ============================================================================
// Sprint 3A: Golden Review Queue & Supersession Audit Trail
// ============================================================================

export const GOLDEN_REVIEW_QUEUE: ReviewQueueItem[] = [
  {
    queue_item_id: 'qitem_poster_noir_detective_magazine',
    stable_lineage_key: 'poster_noir_detective_magazine',
    asset_name: "1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'",
    description: "1946 Crime Detective Magazine cover poster 'Shadows Over Broadway'",
    asset_type: 'artwork',
    scene: 'Scene 42 - 00:44:12',
    scene_or_timecode: 'Scene 42 - 00:44:12',
    current_state: DecisionState.STALE,
    prior_decision: {
      decision_id: 'dec_v7_poster_noir_detective_magazine',
      version_id: 'v7',
      status: DecisionStatus.APPROVED,
      rationale: 'Cleared as incidental background decor under de minimis doctrine; out-of-focus 2s screen time.',
      reviewer_display_name: 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
      reviewed_at: '2026-09-01T11:45:00.000Z',
      context_hash: 'a7b8c9d0e1f234567890abcdef1234567890abcdef1234567890abcdef123456',
      scope_or_conditions: 'Incidental set dressing only; camera must not feature or read headline.',
    },
    four_dimensions: {
      creative_change: {
        has_changed: true,
        materiality: 'high',
        scene: 'Scene 42 - 00:44:12',
        before_prominence: 'Out-of-focus background blur, 2s',
        after_prominence: 'Featured close-up focal shot with dialogue, 14s',
        before_context: 'Prop hangs on far office wall in soft focus behind secondary actor. 2 seconds duration.',
        after_context: 'Lead detective pulls poster off wall, inspects cover closely, thrusts into camera plane for 14 seconds.',
        dialogue_shift: "Detective recites headline: 'Shadows Over Broadway! They knew everything back in 1946.'",
        context_description: 'Escalated from 2s background blur to 14s focal close-up with spoken dialogue recitation.',
        reason_codes: [
          'CONTEXT_HASH_MISMATCH',
          'PROMINENCE_ESCALATED',
          'SCRIPT_DIALOGUE_MODIFIED',
          'CREATIVE_CONTEXT_ALTERED',
        ],
      },
      external_evidence_change: {
        has_changed: true,
        stance: EvidenceStance.SUPPORTING,
        source_title: 'US Copyright Office Historical Catalog - Renewal Records',
        source_url: 'https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective',
        excerpt: 'Registration #B-1946-8821 expired 1974 without timely renewal. Cover artwork in public domain in the United States.',
        query_issued: 'Crime Detective Magazine 1946 Shadows Over Broadway copyright renewal',
        provider: 'Parallel',
        provider_call_id: 'prl_call_882910_poster',
        retrieval_latency_ms: 142.5,
        retrieved_at: '2026-09-03T14:31:02.184Z',
        payload_hash: '6a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef',
      },
      private_agreement_facts: {
        has_contract: false,
        agreement_id: null,
        licensor: 'None (Incidental Prop Rental / Public Domain)',
        licensee: 'Production Co.',
        grant_scope: 'Physical prop rental only; no intellectual property grant',
        scope: 'Physical prop rental only; no intellectual property grant',
        term: 'Production rental period',
        term_in_perpetuity: false,
        section_205_e_status: 'Inapplicable — work in public domain; no unrecorded copyright transfer exists.',
        contract_shield_applied: false,
        status_note: 'No production license negotiated; asset originally cleared as incidental de minimis prop.',
      },
      statutory_policy_reason: {
        reason_code: 'CREATIVE_CONTEXT_ALTERED',
        policy_rule: 'E&O-2026.1-DEVPOST Section 4.2',
        statutory_reference: '17 U.S.C. § 304(a)',
        doctrine: 'Public Domain Expiration via Pre-1978 Non-Renewal',
        eo_risk_rating: 'LOW',
        statutory_exposure: '17 U.S.C. § 504(c) ($150,000 statutory damages) mitigated to $0 by verified Public Domain status.',
        explanation: 'Prominence shift from 2s blur to 14s focal dialogue voids de minimis defense under Sandoval v. New Line Cinema. However, US Copyright Office registration lapsed in 1974 without Form RE renewal, placing work irrevocably in the public domain. Eligible for counsel re-attestation.',
      },
    },
    system_recommendation: {
      suggested_action: ReviewActionType.RE_ATTEST,
      suggested_status: DecisionStatus.APPROVED,
      confidence: 0.96,
      rationale: 'Re-attest as APPROVED under Public Domain doctrine; attach LOC registration excerpt to exceptions schedule.',
    },
    status: 'pending',
    target_version_id: 'v8',
    created_at: '2026-09-03T14:30:00.000Z',
  },
  {
    queue_item_id: 'qitem_music_cue_midnight_serenade',
    stable_lineage_key: 'music_cue_midnight_serenade',
    asset_name: "'Midnight Serenade' jazz composition melody",
    description: "'Midnight Serenade' jazz composition melody",
    asset_type: 'music',
    scene: 'Scene 18 - 00:19:40',
    scene_or_timecode: 'Scene 18 - 00:19:40',
    current_state: DecisionState.STALE,
    prior_decision: {
      decision_id: 'dec_v7_music_cue_midnight_serenade',
      version_id: 'v7',
      status: DecisionStatus.APPROVED,
      rationale: 'Approved based on cue-sheet notes claiming 1928 public domain jazz standard.',
      reviewer_display_name: 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
      reviewed_at: '2026-09-01T11:50:00.000Z',
      context_hash: 'b8c9d0e1f234567890abcdef1234567890abcdef1234567890abcdef1234567a',
      scope_or_conditions: 'Synchronization and master use in Scene 18 speakeasy sequence.',
    },
    four_dimensions: {
      creative_change: {
        has_changed: false,
        materiality: 'none',
        scene: 'Scene 18 - 00:19:40',
        before_prominence: 'Background jazz trio performance in speakeasy, 20s',
        after_prominence: 'Background jazz trio performance in speakeasy, 20s',
        before_context: 'Atmospheric jazz trumpet playing in background while characters talk at bar.',
        after_context: 'Atmospheric jazz trumpet playing in background while characters talk at bar.',
        dialogue_shift: 'No dialogue shift; identical timing and mixing across V7 and V8 cuts.',
        context_description: 'Creative staging, edit duration, and mix level are 100% identical (H_7 = H_8).',
        reason_codes: ['DEPENDENCIES_SATISFIED_UNCHANGED'],
      },
      external_evidence_change: {
        has_changed: true,
        stance: EvidenceStance.CONTRADICTORY,
        source_title: 'ASCAP ACE Repertory & Billboard Rights Bulletin',
        source_url: 'https://ascap.com/ace-title-search/midnight-serenade-9921',
        excerpt: 'Worldwide exclusive synchronization and master rights assigned August 2026 to Vanguard Media Holdings LLC (Administered by Kobalt Music). Prior public domain assertions disputed under European term extension.',
        query_issued: 'Midnight Serenade jazz sync rights copyright owner 2026',
        provider: 'Parallel',
        provider_call_id: 'prl_call_993012_music',
        retrieval_latency_ms: 178.2,
        retrieved_at: '2026-09-03T14:31:04.920Z',
        payload_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      },
      private_agreement_facts: {
        has_contract: false,
        agreement_id: null,
        licensor: 'None (Unlicensed / Disputed Estate)',
        licensee: 'Production Co.',
        grant_scope: 'None on file; relied on unverified cue sheet assumption',
        scope: 'None on file; relied on unverified cue sheet assumption',
        term: 'None',
        term_in_perpetuity: false,
        section_205_e_status: 'Inapplicable — No written license agreement exists to trigger statutory § 205(e) protection.',
        contract_shield_applied: false,
        status_note: 'Production holds no sync agreement; relied on faulty cue-sheet public domain notation. 17 U.S.C. § 205(e) contract shield inapplicable.',
      },
      statutory_policy_reason: {
        reason_code: 'EXTERNAL_EVIDENCE_SHIFT',
        policy_rule: 'E&O-2026.1-DEVPOST Section 5.1',
        statutory_reference: '17 U.S.C. §§ 106(4), 504(c)',
        doctrine: 'Unshielded Exclusive Rights Acquisition & Sync Rights Dispute',
        eo_risk_rating: 'CRITICAL',
        statutory_exposure: '17 U.S.C. § 504(c) ($150,000 statutory damages plus injunctive relief under § 502 halting distribution).',
        explanation: 'Contradictory ownership claim by Vanguard Media invalidates prior approval. In the absence of a valid perpetual contract, broadcast creates exposure to statutory willful damages up to $150,000 per violation. Must be scheduled as an unresolved exception.',
      },
    },
    system_recommendation: {
      suggested_action: ReviewActionType.EXCEPTION,
      suggested_status: DecisionStatus.REJECTED,
      confidence: 0.98,
      rationale: 'Mark as UNRESOLVED EXCEPTION on Form E&O; initiate master license negotiation or replace cue with cleared alternate.',
    },
    status: 'pending',
    target_version_id: 'v8',
    created_at: '2026-09-03T14:30:00.000Z',
  },
];

export const GOLDEN_AUDIT_TRAIL: SupersessionEvent[] = [
  {
    event_id: 'evt_v7_approval_poster',
    stable_lineage_key: 'poster_noir_detective_magazine',
    target_version_id: 'v7',
    prior_decision_id: 'dec_initial_ingest_poster',
    superseding_decision_id: 'dec_v7_poster_noir_detective_magazine',
    actor_type: ActorType.HUMAN_COUNSEL,
    action: ReviewActionType.RE_ATTEST,
    resulting_state: DecisionState.CARRIED_FORWARD,
    resulting_status: DecisionStatus.APPROVED,
    counsel_rationale: 'Initial clearance approval in Locked Script v7: De minimis background set dressing (2s).',
    reviewer_name: 'Sarah Jenkins, Esq.',
    reviewer_title: 'Lead Clearance Counsel (Fictional Demo Reviewer)',
    is_fictional_demo_reviewer: true,
    timestamp: '2026-09-01T11:45:00.000Z',
    event_hash: '2c8b7e6a1f0d3e5b8c7a9f2e4d6b8c0a1f3e5d7b9c1a3e5f7a9b1c3d5e7f9a1b',
  },
  {
    event_id: 'evt_v7_approval_music',
    stable_lineage_key: 'music_cue_midnight_serenade',
    target_version_id: 'v7',
    prior_decision_id: 'dec_initial_ingest_music',
    superseding_decision_id: 'dec_v7_music_cue_midnight_serenade',
    actor_type: ActorType.HUMAN_COUNSEL,
    action: ReviewActionType.RE_ATTEST,
    resulting_state: DecisionState.CARRIED_FORWARD,
    resulting_status: DecisionStatus.APPROVED,
    counsel_rationale: 'Initial clearance approval in Locked Script v7: Attested as public domain composition on cue sheet.',
    reviewer_name: 'Sarah Jenkins, Esq.',
    reviewer_title: 'Lead Clearance Counsel (Fictional Demo Reviewer)',
    is_fictional_demo_reviewer: true,
    timestamp: '2026-09-01T11:50:00.000Z',
    event_hash: '4d6e8f0a2b4c6e8a0f2d4e6b8c0a2f4e6d8b0c2a4e6f8a0b2c4d6e8f0a2b4c6e',
  },
  {
    event_id: 'evt_ai_drift_reopen_poster',
    stable_lineage_key: 'poster_noir_detective_magazine',
    target_version_id: 'v8',
    prior_decision_id: 'dec_v7_poster_noir_detective_magazine',
    superseding_decision_id: 'dec_v8_ai_flag_poster',
    actor_type: ActorType.AI_SYSTEM_RECOMMENDATION,
    action: 'REVALIDATE',
    resulting_state: DecisionState.STALE,
    resulting_status: DecisionStatus.NEEDS_REVIEW,
    counsel_rationale: 'AI Clearance Engine Drift Invalidation: Creative prominence escalated from 2s blur to 14s focal close-up with spoken dialogue. Prior de minimis clearance invalidated. Target revalidation query executed.',
    reviewer_name: 'Lienmark Clearance Engine (Automated Pipeline)',
    reviewer_title: 'Deterministic Invalidation Agent',
    is_fictional_demo_reviewer: false,
    timestamp: '2026-09-03T14:30:10.000Z',
    event_hash: '8a0b2c4d6e8f0a2b4c6e8a0f2d4e6b8c0a2f4e6d8b0c2a4e6f8a0b2c4d6e8f0a',
    parent_hash: '2c8b7e6a1f0d3e5b8c7a9f2e4d6b8c0a1f3e5d7b9c1a3e5f7a9b1c3d5e7f9a1b',
  },
  {
    event_id: 'evt_ai_evidence_reopen_music',
    stable_lineage_key: 'music_cue_midnight_serenade',
    target_version_id: 'v8',
    prior_decision_id: 'dec_v7_music_cue_midnight_serenade',
    superseding_decision_id: 'dec_v8_ai_flag_music',
    actor_type: ActorType.AI_SYSTEM_RECOMMENDATION,
    action: 'REVALIDATE',
    resulting_state: DecisionState.STALE,
    resulting_status: DecisionStatus.NEEDS_REVIEW,
    counsel_rationale: 'AI Clearance Engine External Shift Invalidation: Targeted Parallel search discovered August 2026 exclusive synchronization rights assignment to Vanguard Media Holdings LLC. Prior public domain clearance contradicted.',
    reviewer_name: 'Lienmark Clearance Engine (Automated Pipeline)',
    reviewer_title: 'Deterministic Invalidation Agent',
    is_fictional_demo_reviewer: false,
    timestamp: '2026-09-03T14:30:12.000Z',
    event_hash: '9b1c3d5e7f9a1b3c5e7a1f3e5b7c9a1f3e5d7b9c1a3e5f7a9b1c3d5e7f9a1b3c',
    parent_hash: '4d6e8f0a2b4c6e8a0f2d4e6b8c0a2f4e6d8b0c2a4e6f8a0b2c4d6e8f0a2b4c6e',
  },
];

// In-memory mutable array for fallback session persistence
let _fallbackAuditTrail: SupersessionEvent[] = [...GOLDEN_AUDIT_TRAIL];

export function getGoldenReviewQueue(
  reattestations: Record<string, { status: DecisionStatus; rationale: string; reviewer?: string; action?: ReviewActionType }> = {}
): ReviewQueueItem[] {
  return GOLDEN_REVIEW_QUEUE.map((item) => {
    const override = reattestations[item.stable_lineage_key];
    if (override) {
      const isApproved = override.status === DecisionStatus.APPROVED;
      return {
        ...item,
        status: 'resolved' as const,
        current_state: isApproved ? DecisionState.RE_ATTESTED : DecisionState.EXCEPTION,
      };
    }
    return { ...item };
  });
}

export function getGoldenAuditTrail(lineageKey?: string): SupersessionEvent[] {
  if (lineageKey) {
    return _fallbackAuditTrail.filter((e) => e.stable_lineage_key === lineageKey);
  }
  return [..._fallbackAuditTrail];
}

export function recordGoldenSupersessionEvent(event: SupersessionEvent): void {
  _fallbackAuditTrail.push(event);
}

