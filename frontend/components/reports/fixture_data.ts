/**
 * Lienmark Report Deliverables Default Fixtures
 * High-fidelity fallback data for studio deliverables previews and exports.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import {
  TabConfig,
  ExceptionsScheduleData,
  CueSheetResponse,
  WrapChecklistResponse,
  LegalAuditManifestResponse,
} from './types';

export const REPORT_TABS: ReadonlyArray<TabConfig> = [
  {
    id: 'exceptions_schedule',
    label: 'Form E&O-2026 Schedule',
    shortTitle: 'E&O Schedule',
    description: 'Certified clearance exceptions and carried claims exhibit',
    supportedFormats: ['pdf', 'csv', 'json'],
  },
  {
    id: 'cue_sheet',
    label: 'ASCAP/BMI Cue Sheet',
    shortTitle: 'Music Cue Sheet',
    description: 'PRO-standard musical works cue sheet with publisher splits',
    supportedFormats: ['csv', 'json', 'pdf'],
  },
  {
    id: 'wrap_checklist',
    label: 'Wrap Delivery Gate',
    shortTitle: 'Wrap Delivery',
    description: 'Post-production clearance conditions for distributor funds release',
    supportedFormats: ['csv', 'json', 'pdf'],
  },
  {
    id: 'audit_manifest',
    label: 'ISO 27001 Audit Manifest',
    shortTitle: 'Audit Manifest',
    description: 'Forensic cryptographic manifest conforming to SOC 2 & ISO 27001',
    supportedFormats: ['json', 'pdf'],
  },
];

export const DEFAULT_EXCEPTIONS_SCHEDULE: ExceptionsScheduleData = {
  production_id: 'proj_blockbuster_cinema',
  production_title: 'Project Noir',
  cut_hash: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
  ledger_head_hash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
  certified_at: '2026-09-07 19:45:00 UTC',
  underwriter_seal: 'CHUBB / TRAVELERS E&O CERTIFIED',
  cleared_claims: [
    {
      id: 'claim_noir_prop_01',
      title: 'Vintage Neon Diner Clock (Omega Corp)',
      category: 'Props & Set Dressing',
      status: 'CARRIED_FORWARD',
      timecode: '00:04:12:00',
      counsel_note: 'Licensed in perpetuity under Master Prop Agreement #409.',
    },
    {
      id: 'claim_noir_brand_02',
      title: 'Morrison Rye Whiskey Billboard',
      category: 'Trademarks & Brands',
      status: 'RE_ATTESTED',
      timecode: '00:12:44:18',
      counsel_note: 'Incidental de minimis background usage; counsel non-infringement memo filed.',
    },
    {
      id: 'claim_noir_music_03',
      title: 'Velvet Midnight (Source Jazz Cue)',
      category: 'Music Rights',
      status: 'APPROVED',
      timecode: '00:18:22:04',
      counsel_note: 'Direct master & sync license executed with Blue Note Records.',
    },
    {
      id: 'claim_noir_script_04',
      title: 'Detective Vance Monologue',
      category: 'Screenplay & Literary',
      status: 'CARRIED_FORWARD',
      timecode: '00:27:00:12',
      counsel_note: 'WGA certified chain-of-title verified back to original screenplay.',
    },
  ],
  exception_claims: [
    {
      id: 'claim_noir_exc_01',
      title: 'Archival News Broadcast Segment (1984)',
      category: 'Fair Use & Defamation',
      risk_level: 'MEDIUM',
      reason: '14-second archival snippet of municipal press conference. Fair use claimed.',
      policy_rule: 'EXHIBIT_B_SECTION_4_FAIR_USE',
      counsel_disposition: 'Endorsed under Special E&O Policy Rider #2026-09.',
    },
  ],
};

export const DEFAULT_CUE_SHEET: CueSheetResponse = {
  production_id: 'proj_blockbuster_cinema',
  production_title: 'Project Noir',
  total_cues: 3,
  total_duration_seconds: 245,
  cues: [
    {
      cue_number: 1,
      title: 'Noir Main Titles Theme',
      usage: 'MT',
      timecode_in: '00:00:00:00',
      timecode_out: '00:01:30:00',
      duration_seconds: 90,
      scene: 'Main Titles / Credits',
      composers: [{ name: 'Marcus Vance', pro: 'ASCAP', split_percentage: 100 }],
      publishers: [{ name: 'Noir Cinema Publishing', pro: 'ASCAP', split_percentage: 100 }],
      record_label: 'Blockbuster Music Works',
      pro_work_id: 'ASCAP-8849201',
      status: 'CLEARED',
      lineage_key: 'cue_main_theme',
    },
    {
      cue_number: 2,
      title: 'Rain on Asphalt (Background Score)',
      usage: 'BI',
      timecode_in: '00:08:15:10',
      timecode_out: '00:09:45:10',
      duration_seconds: 90,
      scene: 'Alley Investigation',
      composers: [{ name: 'Marcus Vance', pro: 'ASCAP', split_percentage: 100 }],
      publishers: [{ name: 'Noir Cinema Publishing', pro: 'ASCAP', split_percentage: 100 }],
      record_label: 'Blockbuster Music Works',
      pro_work_id: 'ASCAP-8849202',
      status: 'CLEARED',
      lineage_key: 'cue_rain_asphalt',
    },
    {
      cue_number: 3,
      title: 'Velvet Midnight (Club Source)',
      usage: 'VV',
      timecode_in: '00:18:22:04',
      timecode_out: '00:19:27:04',
      duration_seconds: 65,
      scene: 'The Blue Note Lounge',
      composers: [{ name: 'Elena Rostova', pro: 'BMI', split_percentage: 100 }],
      publishers: [{ name: 'Blue Sky Music BMI', pro: 'BMI', split_percentage: 100 }],
      record_label: 'Blue Note Records',
      pro_work_id: 'BMI-9912044',
      status: 'CLEARED',
      lineage_key: 'cue_velvet_midnight',
    },
  ],
};

export const DEFAULT_WRAP_CHECKLIST: WrapChecklistResponse = {
  production_id: 'proj_blockbuster_cinema',
  is_ready_for_funds_release: true,
  cleared_percentage: 100.0,
  total_items: 5,
  cleared_items: 5,
  blocking_reasons: [],
  signed_off: true,
  signed_off_by: 'Marcus Vance, Esq. (Lead Counsel)',
  signed_off_at: '2026-09-07 19:30:00 UTC',
  items: [
    {
      item_id: 'wrap_01',
      category: 'Screenplay & Literary',
      title: 'WGA Chain of Title & Writer Agreements',
      description: 'Fully executed literary purchase agreements and copyright registrations.',
      status: 'CLEARED',
    },
    {
      item_id: 'wrap_02',
      category: 'Music Rights',
      title: 'Master & Synchronization Clearance Licenses',
      description: 'All 3 cues cleared with executed master, sync, and PRO work registrations.',
      status: 'CLEARED',
    },
    {
      item_id: 'wrap_03',
      category: 'SAG-AFTRA & Cast',
      title: 'Cast Likeness & Publicity Releases',
      description: 'Principal and background actor clearance certificates verified and archived.',
      status: 'CLEARED',
    },
    {
      item_id: 'wrap_04',
      category: 'Props & Set Dressing',
      title: 'Prop Master Release Schedules',
      description: 'Art department and prop master vendor clearance logs verified.',
      status: 'CLEARED',
    },
    {
      item_id: 'wrap_05',
      category: 'Insurance & E&O',
      title: 'Certified Form E&O-2026 Policy Exhibit',
      description: 'Underwriting certificate issued by insurer with hash continuity locks.',
      status: 'CLEARED',
    },
  ],
};

export const DEFAULT_AUDIT_MANIFEST: LegalAuditManifestResponse = {
  manifest_version: '1.0.0',
  iso_standard: 'ISO/IEC 27001:2022 / SOC 2 Type II',
  generated_at: '2026-09-07T19:45:00Z',
  production_id: 'proj_blockbuster_cinema',
  head_hash: '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8',
  previous_hash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
  total_ledger_events: 14,
  chain_verified: true,
  claims_census: {
    music: 3,
    props: 6,
    brands: 2,
    screenplay: 1,
  },
  signatories: [
    {
      role: 'Lead Production Counsel',
      name: 'Marcus Vance, Esq.',
      key_id: 'key_ed25519_vance_01',
      timestamp: '2026-09-07T19:30:00Z',
    },
    {
      role: 'Supervising Underwriter',
      name: 'Sarah Jenkins (Chubb E&O)',
      key_id: 'key_rsa4096_chubb_99',
      timestamp: '2026-09-07T19:40:00Z',
    },
    {
      role: 'Legal Engineering Engine',
      name: 'Lienmark Autonomous Gate v6.3',
      key_id: 'lienmark_hsm_cluster_us_east',
      timestamp: '2026-09-07T19:45:00Z',
    },
  ],
  audit_trail_digest: 'd7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592',
};
