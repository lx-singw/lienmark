/**
 * conflict_fixtures.ts
 * Canonical fixture datasets for contradictory evidence and conflict arbitration.
 * Sprint 3.3: Contradictory Evidence & Conflict Arbitration UI.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import {
  AuthorityTier,
  type ConflictEvidencePair,
  ConflictResolutionStance,
  type EvidenceSourceRecord,
} from './conflict_types';

export const APOLLO_SOURCE_A: EvidenceSourceRecord = {
  id: 'src_nasa_public_domain',
  name: 'NASA Sound Collection & Public Domain Repository',
  organization: 'NASA / US Federal Government',
  authorityTier: AuthorityTier.TIER_1_GOVERNMENT,
  rightsStatus: 'Public Domain (17 U.S.C. § 105)',
  claimedOwner: 'United States Federal Government (Public)',
  licenseType: 'Unrestricted Public Domain Grant',
  term: 'Perpetual / Non-Expiring',
  url: 'https://images.nasa.gov/details/Apollo11_Eagle_Landed',
  excerpt:
    'NASA audio material is not protected by copyright unless specifically noted. Works of the federal government enter the public domain immediately upon creation under 17 U.S.C. § 105.',
  retrievedAt: '2026-09-03T14:28:11Z',
  confidenceScore: 0.98,
};

export const APOLLO_SOURCE_B: EvidenceSourceRecord = {
  id: 'src_cbs_master_rights',
  name: 'CBS News Historical Broadcast Rights Registry',
  organization: 'CBS Broadcasting Inc. / Paramount Global',
  authorityTier: AuthorityTier.TIER_2_MEDIA_TRADE,
  rightsStatus: 'Protected / Master Rights Reserved',
  claimedOwner: 'CBS Broadcasting Inc. / Paramount Global',
  licenseType: 'Exclusive Commercial Broadcast License',
  term: '50-Year Exclusive Renewal (Through 2039)',
  url: 'https://cbsnews.com/archives/licensing/apollo-11-broadcast-audio',
  excerpt:
    'CBS asserts proprietary master broadcast audio copyright in historic moon landing transmissions, claiming enhanced audio remastering, telemetry filtering, and original network broadcast synchronization rights.',
  retrievedAt: '2026-09-03T14:30:45Z',
  confidenceScore: 0.94,
};

export const SAMPLE_APOLLO_CONFLICT_PAIR: ConflictEvidencePair = {
  id: 'cfl_apollo_11_audio',
  claimId: 'claim_apollo_moon_broadcast',
  assetName: "Apollo 11 Audio Transmission — 'The Eagle Has Landed'",
  sceneTimecode: 'SC 09 (00:08:42)',
  stance: ConflictResolutionStance.CONTRADICTORY,
  sourceA: APOLLO_SOURCE_A,
  sourceB: APOLLO_SOURCE_B,
  fieldDiffs: [
    {
      fieldKey: 'rightsStatus',
      fieldLabel: 'Rights Status',
      sourceAValue: 'Public Domain (17 U.S.C. § 105)',
      sourceBValue: 'Protected / Master Rights Reserved',
      isConflicting: true,
      severity: 'critical',
      statutoryNote: 'Conflict between statutory public domain status and claimed commercial master rights.',
    },
    {
      fieldKey: 'claimedOwner',
      fieldLabel: 'Claimed Owner',
      sourceAValue: 'United States Federal Government (Public)',
      sourceBValue: 'CBS Broadcasting Inc. / Paramount Global',
      isConflicting: true,
      severity: 'critical',
      statutoryNote: 'Competing legal entities claiming exclusive ownership rights over identical material.',
    },
    {
      fieldKey: 'licenseType',
      fieldLabel: 'License Type',
      sourceAValue: 'Unrestricted Public Domain Grant',
      sourceBValue: 'Exclusive Commercial Broadcast License',
      isConflicting: true,
      severity: 'high',
      statutoryNote: 'Incompatible licensing models: open public domain grant vs. proprietary commercial broadcast sync.',
    },
    {
      fieldKey: 'term',
      fieldLabel: 'Term',
      sourceAValue: 'Perpetual / Non-Expiring',
      sourceBValue: '50-Year Exclusive Renewal (Through 2039)',
      isConflicting: true,
      severity: 'medium',
      statutoryNote: 'Discrepancy between perpetual non-expiring status and active commercial license window.',
    },
    {
      fieldKey: 'authorityTier',
      fieldLabel: 'Authority Tier',
      sourceAValue: 'Tier 1 Government',
      sourceBValue: 'Tier 2 Media/Trade',
      isConflicting: true,
      severity: 'info',
      statutoryNote: 'Tier 1 government registry evidence carries statutory presumption over Tier 2 commercial registry.',
    },
  ],
  elevationReason:
    'Direct conflict between Tier 1 statutory government work doctrine (17 U.S.C. § 105) and Tier 2 third-party master broadcast rights. Automated clearance strictly fails closed; algorithmic auto-approval is legally prohibited.',
  counselActionRequired:
    'Mandatory Counsel Adjudication: Clearance counsel must verify whether production audio uses raw NASA telemetry or CBS remastered audio. If CBS master audio is incorporated, an underwriting exception or commercial sync license is required.',
  statutoryDoctrine: '17 U.S.C. § 105 (Government Works) vs. Proprietary Master Remastering Doctrine',
  statutoryDamagesMaxUsd: 150000,
  detectedAt: '2026-09-03T14:31:00Z',
};
