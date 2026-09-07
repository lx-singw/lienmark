/**
 * Lienmark Deliverables Subsystem Types (Sprint 6.3)
 * Strict TypeScript interfaces for Cue Sheets, Wrap Checklist, Audit Manifest, and E&O Schedule.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

export type ReportTabKey =
  | 'exceptions_schedule'
  | 'cue_sheet'
  | 'wrap_checklist'
  | 'audit_manifest';

export type ExportFormat = 'pdf' | 'csv' | 'json';

export interface TabConfig {
  readonly id: ReportTabKey;
  readonly label: string;
  readonly shortTitle: string;
  readonly description: string;
  readonly supportedFormats: ReadonlyArray<ExportFormat>;
}

export type CueUsageType = 'BI' | 'BV' | 'VV' | 'VI' | 'MT' | 'ET' | 'BG';

export interface CueComposer {
  readonly name: string;
  readonly pro: string;
  readonly split_percentage: number;
}

export interface CuePublisher {
  readonly name: string;
  readonly pro: string;
  readonly split_percentage: number;
}

export interface CueSheetEntry {
  readonly cue_number: number;
  readonly title: string;
  readonly usage: CueUsageType;
  readonly timecode_in: string;
  readonly timecode_out: string;
  readonly duration_seconds: number;
  readonly scene?: string | null;
  readonly composers: ReadonlyArray<CueComposer>;
  readonly publishers: ReadonlyArray<CuePublisher>;
  readonly record_label?: string | null;
  readonly pro_work_id?: string | null;
  readonly status: string;
  readonly lineage_key: string;
}

export interface CueSheetResponse {
  readonly production_id: string;
  readonly production_title: string;
  readonly total_cues: number;
  readonly total_duration_seconds: number;
  readonly cues: ReadonlyArray<CueSheetEntry>;
}

export type WrapChecklistStatus = 'CLEARED' | 'BLOCKED' | 'FLAGGED';

export interface WrapChecklistItem {
  readonly item_id: string;
  readonly category: string;
  readonly title: string;
  readonly description: string;
  readonly status: WrapChecklistStatus;
  readonly blocking_reason?: string | null;
  readonly lineage_key?: string | null;
}

export interface WrapChecklistResponse {
  readonly production_id: string;
  readonly is_ready_for_funds_release: boolean;
  readonly cleared_percentage: number;
  readonly total_items: number;
  readonly cleared_items: number;
  readonly blocking_reasons: ReadonlyArray<string>;
  readonly items: ReadonlyArray<WrapChecklistItem>;
  readonly signed_off: boolean;
  readonly signed_off_by?: string | null;
  readonly signed_off_at?: string | null;
}

export interface Signatory {
  readonly role: string;
  readonly name: string;
  readonly key_id?: string;
  readonly timestamp?: string;
}

export interface LegalAuditManifestResponse {
  readonly manifest_version: string;
  readonly iso_standard: string;
  readonly generated_at: string;
  readonly production_id: string;
  readonly head_hash: string;
  readonly previous_hash: string;
  readonly total_ledger_events: number;
  readonly chain_verified: boolean;
  readonly claims_census: Record<string, number>;
  readonly signatories: ReadonlyArray<Signatory>;
  readonly audit_trail_digest: string;
}

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ClearedClaimItem {
  readonly id: string;
  readonly title: string;
  readonly category: string;
  readonly status: string;
  readonly timecode?: string;
  readonly counsel_note?: string;
}

export interface ExceptionClaimItem {
  readonly id: string;
  readonly title: string;
  readonly category: string;
  readonly risk_level: RiskLevel;
  readonly reason: string;
  readonly policy_rule?: string;
  readonly counsel_disposition?: string;
}

export interface ExceptionsScheduleData {
  readonly production_id: string;
  readonly production_title: string;
  readonly cut_hash: string;
  readonly ledger_head_hash: string;
  readonly cleared_claims: ReadonlyArray<ClearedClaimItem>;
  readonly exception_claims: ReadonlyArray<ExceptionClaimItem>;
  readonly certified_at: string;
  readonly underwriter_seal: string;
}

export interface ReportExportModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly initialTab?: ReportTabKey;
  readonly productionId?: string;
  readonly productionTitle?: string;
}
