/**
 * Lienmark Ingestion UI Domain Models & Interfaces
 * Governs cloud storage watchers, Dropzone uploads, and Eventarc activity feeds.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript definitions.
 */

export const IngestionStatus = {
  QUEUED: 'QUEUED',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  REJECTED_OUT_OF_SCOPE: 'REJECTED_OUT_OF_SCOPE',
  FAILED: 'FAILED',
} as const;

export type IngestionStatus =
  (typeof IngestionStatus)[keyof typeof IngestionStatus];

export const IngestionSource = {
  EVENTARC: 'CloudEvent Eventarc',
  POLLER: 'GCS Poller',
  DROPZONE: 'Dropzone',
} as const;

export type IngestionSource =
  (typeof IngestionSource)[keyof typeof IngestionSource];

export interface GcsTargetValidation {
  isValid: boolean;
  error?: string;
  orgId?: string;
  prodId?: string;
  filename?: string;
}

export interface StatusBadgeStyle {
  bg: string;
  text: string;
  border: string;
  label: string;
}

export interface IngestionEvent {
  eventId: string;
  timestampUtc: string;
  fileName: string;
  fileSizeBytes: number;
  orgId: string;
  prodId: string;
  gcsPath: string;
  status: IngestionStatus;
  runId?: string;
  source: IngestionSource;
  sourceDetails?: string;
  errorMessage?: string;
}

export interface WatcherStatus {
  eventarcHealthy: boolean;
  pollerActive: boolean;
  lastSyncUtc: string;
  bucketUri: string;
  activeWatchersCount: number;
}

export interface DropzoneModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete?: (runId: string) => void;
  defaultOrgId?: string;
  defaultProdId?: string;
  bucketName?: string;
}

export interface IngestionFeedFilterState {
  searchQuery: string;
  statusFilter: string;
  sourceFilter: string;
}
