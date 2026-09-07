/**
 * Frontend Types for Decisions & Cryptographic Ledger History
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

export interface DualSignature {
  readonly actor_id: string;
  readonly role: string;
  readonly key_id: string;
  readonly signature_algorithm: string;
  readonly signature_hex: string;
}

export interface DecisionTimelineEvent {
  readonly event_id: string;
  readonly sequence_number: number;
  readonly action_type: string;
  readonly timestamp_utc: string;
  readonly actor_id: string;
  readonly actor_name: string;
  readonly claim_id?: string | null;
  readonly claim_title?: string | null;
  readonly decision_status?: string | null;
  readonly counsel_rationale?: string | null;
  readonly entry_hash: string;
  readonly previous_event_hash: string;
  readonly payload_digest: string;
  readonly is_superseded: boolean;
  readonly superseded_event_id?: string | null;
  readonly dual_signatures: ReadonlyArray<DualSignature>;
}

export interface DecisionChainResponse {
  readonly production_id: string;
  readonly is_chain_valid: boolean;
  readonly chain_length: number;
  readonly head_event_hash?: string | null;
  readonly events: ReadonlyArray<DecisionTimelineEvent>;
}

export interface LedgerVerificationResponse {
  readonly event_id: string;
  readonly sequence_number: number;
  readonly entry_hash: string;
  readonly previous_event_hash: string;
  readonly payload_digest: string;
  readonly is_valid: boolean;
  readonly verification_message: string;
  readonly canonical_payload: Record<string, unknown>;
  readonly dual_signatures: ReadonlyArray<DualSignature>;
}

export interface SupersessionRecord {
  readonly event_id: string;
  readonly superseded_event_id: string;
  readonly superseding_action: string;
  readonly counsel_rationale: string;
  readonly timestamp: string;
  readonly actor_id: string;
}
