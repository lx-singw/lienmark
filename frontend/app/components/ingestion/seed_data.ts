/**
 * Seed Ingestion Events
 * Canonical realistic milestone ingestion records for demonstration and offline fallback.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import type { IngestionEvent } from './types';

export const INITIAL_INGESTION_EVENTS: IngestionEvent[] = [
  {
    eventId: 'evt_gcs_001',
    timestampUtc: '2026-09-07 08:32:10 UTC',
    fileName: 'Shadows_Over_Broadway_Locked_v8.pdf',
    fileSizeBytes: 1468006, // ~1.4 MB
    orgId: 'studio-alpha',
    prodId: 'prod-001',
    gcsPath:
      'gs://lienmark-intake-storage/organizations/studio-alpha/productions/prod-001/locked/Shadows_Over_Broadway_Locked_v8.pdf',
    status: 'COMPLETED',
    runId: 'run_8f102c9a',
    source: 'CloudEvent Eventarc',
    sourceDetails: 'storage.objects.v1.finalized',
  },
  {
    eventId: 'evt_gcs_002',
    timestampUtc: '2026-09-07 08:15:44 UTC',
    fileName: 'Neon_Reign_Milestone_Cut_v3.pdf',
    fileSizeBytes: 3984588, // ~3.8 MB
    orgId: 'studio-alpha',
    prodId: 'prod-002',
    gcsPath:
      'gs://lienmark-intake-storage/organizations/studio-alpha/productions/prod-002/locked/Neon_Reign_Milestone_Cut_v3.pdf',
    status: 'PROCESSING',
    runId: 'run_9a215b3c',
    source: 'GCS Poller',
    sourceDetails: '10s bucket discovery scan',
  },
  {
    eventId: 'evt_gcs_003',
    timestampUtc: '2026-09-07 07:50:22 UTC',
    fileName: 'Solaris_Echo_LockedDraft_v2.pdf',
    fileSizeBytes: 839680, // ~820 KB
    orgId: 'cinema-corp',
    prodId: 'prod-003',
    gcsPath:
      'gs://lienmark-intake-storage/organizations/cinema-corp/productions/prod-003/locked/Solaris_Echo_LockedDraft_v2.pdf',
    status: 'QUEUED',
    runId: 'run_4d771e8f',
    source: 'Dropzone',
    sourceDetails: 'Direct signed URL upload',
  },
  {
    eventId: 'evt_gcs_004',
    timestampUtc: '2026-09-07 06:11:05 UTC',
    fileName: 'Draft_Notes_Unregistered.docx',
    fileSizeBytes: 143360, // ~140 KB
    orgId: 'studio-alpha',
    prodId: 'prod-001',
    gcsPath:
      'gs://lienmark-intake-storage/organizations/studio-alpha/productions/prod-001/locked/Draft_Notes_Unregistered.docx',
    status: 'REJECTED_OUT_OF_SCOPE',
    source: 'CloudEvent Eventarc',
    sourceDetails: 'storage.objects.v1.finalized',
    errorMessage:
      'Non-PDF file rejected: Only PDF documents (.pdf) are permitted in the locked milestone folder.',
  },
  {
    eventId: 'evt_gcs_005',
    timestampUtc: '2026-09-07 05:40:18 UTC',
    fileName: 'Harbor_Mist_Final_Locked.pdf',
    fileSizeBytes: 532480, // ~520 KB
    orgId: 'film-west',
    prodId: 'prod-004',
    gcsPath:
      'gs://lienmark-intake-storage/organizations/film-west/productions/prod-004/locked/Harbor_Mist_Final_Locked.pdf',
    status: 'COMPLETED',
    runId: 'run_1109a27c',
    source: 'Dropzone',
    sourceDetails: 'Direct signed URL upload',
  },
];
