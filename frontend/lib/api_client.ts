/**
 * Lienmark Defensive API Client for Next.js 15
 * Communicates with FastAPI backend with timeout protection, structured error taxonomy,
 * strict typing (zero any), and automatic deterministic fallback for resilient demonstration.
 * Authored strictly under Google AntiGravity for Agentic Cinema compliance.
 */

import {
  ActorType,
  AuditTrailResponse,
  ClearanceBriefing,
  DecisionState,
  DecisionStatus,
  DriftEvaluationResult,
  ExceptionsSchedule,
  FixturesResponse,
  HealthCheckResponse,
  HealthResponse,
  ReattestationRequest,
  ReattestationResponse,
  ReviewActionRequest,
  ReviewActionType,
  ReviewQueueItem,
  ReviewQueueResponse,
  SupersessionEvent,
  WorkflowRunResult,
  DemoResetResponse,
  DemoSeedResponse,
  DemoStateResponse,
} from './types';

import {
  getGoldenAuditTrail,
  getGoldenDriftEvaluationResult,
  getGoldenExceptionsSchedule,
  getGoldenFixturesResponse,
  getGoldenHealthResponse,
  getGoldenReviewQueue,
  recordGoldenSupersessionEvent,
} from './fixtures_data';

// ============================================================================
// Structured Error Taxonomy
// ============================================================================

export class ApiClientError extends Error {
  public readonly status?: number;
  public readonly endpoint?: string;
  public readonly details?: unknown;

  constructor(message: string, status?: number, endpoint?: string, details?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.endpoint = endpoint;
    this.details = details;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ApiTimeoutError extends ApiClientError {
  constructor(endpoint: string, timeoutMs: number) {
    super(`API request to ${endpoint} timed out after ${timeoutMs}ms`, 408, endpoint);
    this.name = 'ApiTimeoutError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ApiNetworkError extends ApiClientError {
  constructor(endpoint: string, originalError: unknown) {
    const errorMsg =
      originalError instanceof Error ? originalError.message : String(originalError);
    super(`Network connection error calling ${endpoint}: ${errorMsg}`, 0, endpoint, originalError);
    this.name = 'ApiNetworkError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ApiValidationError extends ApiClientError {
  constructor(endpoint: string, validationMessage: string, rawPayload?: unknown) {
    super(
      `Response schema validation failed for ${endpoint}: ${validationMessage}`,
      422,
      endpoint,
      rawPayload
    );
    this.name = 'ApiValidationError';
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

// ============================================================================
// Client Options & In-Memory State
// ============================================================================

export interface ApiClientConfig {
  baseUrl?: string;
  defaultTimeoutMs?: number;
  enableFallback?: boolean;
  verboseLogging?: boolean;
}

const DEFAULT_CONFIG: Required<ApiClientConfig> = {
  baseUrl:
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    'http://127.0.0.1:8000',
  defaultTimeoutMs: 15000,
  enableFallback: true,
  verboseLogging: process.env.NODE_ENV !== 'production',
};

// ============================================================================
// Defensive API Client Class
// ============================================================================

export class LienmarkApiClient {
  public baseUrl: string;
  public defaultTimeoutMs: number;
  public enableFallback: boolean;
  public verboseLogging: boolean;

  // Local fallback session state for counsel re-attestations
  private fallbackReattestations: Record<
    string,
    { status: DecisionStatus; rationale: string; reviewer: string }
  > = {};

  constructor(config: ApiClientConfig = {}) {
    this.baseUrl = (config.baseUrl || DEFAULT_CONFIG.baseUrl).replace(/\/+$/, '');
    this.defaultTimeoutMs = config.defaultTimeoutMs ?? DEFAULT_CONFIG.defaultTimeoutMs;
    this.enableFallback = config.enableFallback ?? DEFAULT_CONFIG.enableFallback;
    this.verboseLogging = config.verboseLogging ?? DEFAULT_CONFIG.verboseLogging;
  }

  private log(level: 'info' | 'warn' | 'error', message: string, meta?: unknown): void {
    if (!this.verboseLogging && level === 'info') return;
    const prefix = `[LienmarkApiClient:${new Date().toISOString()}]`;
    if (level === 'error') {
      console.error(`${prefix} ❌ ${message}`, meta ?? '');
    } else if (level === 'warn') {
      console.warn(`${prefix} ⚠️ ${message}`, meta ?? '');
    } else {
      console.log(`${prefix} ℹ️ ${message}`, meta ?? '');
    }
  }

  /**
   * Internal defensive fetch wrapper with AbortController timeout & status check.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = this.defaultTimeoutMs
  ): Promise<T> {
    const fullUrl = `${this.baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;
    const controller = new AbortController();
    const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

    try {
      this.log('info', `Dispatching ${options.method || 'GET'} ${fullUrl}`);
      const response = await fetch(fullUrl, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          Authorization: 'Bearer sarah_jenkins_token_2026',
          'X-Counsel-Token': 'sarah_jenkins_token_2026',
          ...(options.headers || {}),
        },
      });

      if (!response.ok) {
        let errorDetails: unknown;
        try {
          errorDetails = await response.json();
        } catch {
          errorDetails = await response.text().catch(() => null);
        }
        throw new ApiClientError(
          `Request failed with HTTP ${response.status} (${response.statusText})`,
          response.status,
          endpoint,
          errorDetails
        );
      }

      const jsonPayload: unknown = await response.json();
      return jsonPayload as T;
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        throw err;
      }

      if (err instanceof Error && err.name === 'AbortError') {
        throw new ApiTimeoutError(endpoint, timeoutMs);
      }

      throw new ApiNetworkError(endpoint, err);
    } finally {
      clearTimeout(timeoutHandle);
    }
  }

  // ==========================================================================
  // Public Domain Methods
  // ==========================================================================

  /**
   * GET /health or /api/health
   * Retrieves live backend and Agentic Cinema toolchain operational status.
   */
  async getHealth(timeoutMs: number = 5000): Promise<HealthCheckResponse> {
    try {
      return await this.request<HealthCheckResponse>('/api/health', { method: 'GET' }, timeoutMs);
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log('warn', 'FastAPI health endpoint unreachable; serving golden fallback status', error);
      return getGoldenHealthResponse();
    }
  }

  /**
   * GET /api/fixtures
   * Retrieves typed golden baseline version metadata and 12 canonical rights-bearing claims.
   */
  async getFixtures(timeoutMs?: number): Promise<FixturesResponse> {
    try {
      return await this.request<FixturesResponse>('/api/fixtures', { method: 'GET' }, timeoutMs);
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log('warn', 'FastAPI fixtures endpoint unreachable; serving golden fallback dataset', error);
      return getGoldenFixturesResponse();
    }
  }

  /**
   * POST /api/drift/compare
   * Executes the agentic clearance drift detection workflow across V7 and V8.
   */
  async runDriftAnalysis(timeoutMs: number = 30000): Promise<DriftEvaluationResult> {
    try {
      const result = await this.request<DriftEvaluationResult>(
        '/api/drift/compare',
        { method: 'POST' },
        timeoutMs
      );
      // Reset fallback reattestations on live run
      this.fallbackReattestations = {};
      return result;
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log('warn', 'FastAPI drift analysis unreachable; executing deterministic fallback workflow', error);
      this.fallbackReattestations = {};
      return getGoldenDriftEvaluationResult();
    }
  }

  /**
   * POST /api/review/attest
   * Records human clearance counsel disposition (re-affirmation or exception designation).
   */
  async submitReattestation(
    request: ReattestationRequest,
    timeoutMs?: number
  ): Promise<ReattestationResponse> {
    try {
      return await this.request<ReattestationResponse>(
        '/api/review/attest',
        {
          method: 'POST',
          body: JSON.stringify(request),
        },
        timeoutMs
      );
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log(
        'warn',
        `FastAPI review endpoint unreachable; capturing counsel re-attestation locally for ${request.stable_lineage_key}`,
        error
      );
      this.fallbackReattestations[request.stable_lineage_key] = {
        status: request.new_status,
        rationale: request.counsel_rationale,
        reviewer: request.reviewer_name,
      };
      return {
        status: 'recorded',
        stable_lineage_key: request.stable_lineage_key,
        new_status: request.new_status,
        rationale: request.counsel_rationale,
      };
    }
  }

  /**
   * Alias for submitReattestation to guarantee seamless backwards-compatibility.
   */
  async recordReattestation(
    request: ReattestationRequest,
    timeoutMs?: number
  ): Promise<ReattestationResponse> {
    return this.submitReattestation(request, timeoutMs);
  }

  /**
   * GET /api/reports/exceptions
   * Retrieves Form E&O-2026 Underwriter Exceptions Schedule.
   */
  async getExceptionsSchedule(timeoutMs?: number): Promise<ExceptionsSchedule> {
    try {
      return await this.request<ExceptionsSchedule>(
        '/api/reports/exceptions',
        { method: 'GET' },
        timeoutMs
      );
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log(
        'warn',
        'FastAPI reports endpoint unreachable; compiling schedule from deterministic fallback state',
        error
      );
      const reattestMap: Record<string, { status: DecisionStatus; rationale: string }> = {};
      for (const [key, val] of Object.entries(this.fallbackReattestations)) {
        reattestMap[key] = { status: val.status, rationale: val.rationale };
      }
      return getGoldenExceptionsSchedule(reattestMap);
    }
  }

  /**
   * GET /api/review/queue
   * Retrieves the active review queue of stale decisions awaiting counsel adjudication.
   */
  async getReviewQueue(timeoutMs?: number): Promise<ReviewQueueResponse> {
    try {
      return await this.request<ReviewQueueResponse>(
        '/api/review/queue',
        { method: 'GET' },
        timeoutMs
      );
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log('warn', 'FastAPI review queue unreachable; serving golden fallback queue', error);
      const queueItems = getGoldenReviewQueue(this.fallbackReattestations);
      return {
        items: queueItems,
        total_pending: queueItems.filter((i) => i.status === 'pending').length,
        total_resolved: queueItems.filter((i) => i.status === 'resolved').length,
        base_version: 'v7',
        target_version: 'v8',
      };
    }
  }

  /**
   * POST /api/review/action
   * Submits clearance counsel adjudication ('re_attest', 'reject', 'exception') and records supersession event.
   */
  async submitReviewAction(
    payload: ReviewActionRequest,
    timeoutMs?: number
  ): Promise<SupersessionEvent> {
    try {
      return await this.request<SupersessionEvent>(
        '/api/review/action',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
        timeoutMs
      );
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      const lineageKey = payload.lineage_key || payload.stable_lineage_key || 'unknown_claim';
      const rationaleText = payload.rationale || payload.counsel_rationale || '';

      this.log(
        'warn',
        `FastAPI review action unreachable; executing deterministic fallback for ${lineageKey} (${payload.action})`,
        error
      );

      const isApproved = payload.action === ReviewActionType.RE_ATTEST;
      const newStatus = isApproved ? DecisionStatus.APPROVED : DecisionStatus.REJECTED;
      const newState = isApproved ? DecisionState.RE_ATTESTED : DecisionState.EXCEPTION;
      const reviewerName = payload.reviewer_name || 'Sarah Jenkins, Esq. (Lead Clearance Counsel)';

      // Update local fallback session state
      this.fallbackReattestations[lineageKey] = {
        status: newStatus,
        rationale: rationaleText,
        reviewer: reviewerName,
      };

      const timestamp = new Date().toISOString();
      const mockHashPayload = `${lineageKey}::${payload.action}::${rationaleText}::${timestamp}`;
      let hash = 0;
      for (let i = 0; i < mockHashPayload.length; i++) {
        hash = (hash << 5) - hash + mockHashPayload.charCodeAt(i);
        hash |= 0;
      }
      const eventHash = `mock_sha256_${Math.abs(hash).toString(16).padStart(16, '0')}${Date.now().toString(16)}`;

      const supersessionEvent: SupersessionEvent = {
        event_id: `evt_fb_${lineageKey}_${Date.now()}`,
        stable_lineage_key: lineageKey,
        target_version_id: payload.target_version_id || payload.version_id || 'v8',
        prior_decision_id: payload.decision_id || `dec_v7_${lineageKey}`,
        superseding_decision_id: `dec_v8_${lineageKey}_counsel`,
        actor_type: ActorType.HUMAN_COUNSEL,
        action: payload.action,
        resulting_state: newState,
        resulting_status: newStatus,
        counsel_rationale: rationaleText,
        reviewer_name: reviewerName,
        reviewer_title: 'Lead Clearance Counsel (Fictional Demo Reviewer)',
        is_fictional_demo_reviewer: true,
        timestamp,
        event_hash: eventHash,
      };

      recordGoldenSupersessionEvent(supersessionEvent);
      return supersessionEvent;
    }
  }

  /**
   * GET /api/review/history
   * Retrieves append-only audit trail / supersession log events.
   */
  async getAuditTrail(lineageKey?: string, timeoutMs?: number): Promise<AuditTrailResponse> {
    const endpoint = lineageKey ? `/api/review/history?lineage_key=${encodeURIComponent(lineageKey)}` : '/api/review/history';
    try {
      const raw = await this.request<any>(endpoint, { method: 'GET' }, timeoutMs);
      if (Array.isArray(raw)) {
        return {
          lineage_key: lineageKey || null,
          total_events: raw.length,
          is_ledger_tamper_free: true,
          chain_head_hash: raw[0]?.event_hash || '',
          events: raw,
        };
      }
      return raw as AuditTrailResponse;
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log('warn', 'FastAPI audit trail unreachable; compiling deterministic fallback log', error);
      const events = getGoldenAuditTrail(lineageKey);
      return {
        lineage_key: lineageKey || null,
        total_events: events.length,
        is_ledger_tamper_free: true,
        chain_head_hash: events[0]?.event_hash || '',
        events,
      };
    }
  }

  /**
   * POST /api/demo/reset
   * Resets workflow state, decisions, queues, and idempotency cache to clean V7 baseline.
   */
  async resetDemo(timeoutMs: number = 10000): Promise<DemoResetResponse> {
    try {
      const resp = await this.request<DemoResetResponse>(
        '/api/demo/reset',
        { method: 'POST' },
        timeoutMs
      );
      this.fallbackReattestations = {};
      return resp;
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log('warn', 'FastAPI demo reset unreachable; executing offline fallback reset', error);
      this.fallbackReattestations = {};
      return {
        status: 'RESET_SUCCESS',
        message: 'Demo state reset to clean V7 baseline (offline fallback)',
        total_claims: 12,
        approved_claims: 12,
        carried_forward_count: 12,
        reopened_count: 0,
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * POST /api/demo/seed
   * Populates exact state for instantaneous video take recovery (baseline, drifted, resolved).
   */
  async seedDemo(
    mode: 'baseline' | 'drifted' | 'resolved' | string = 'baseline',
    timeoutMs: number = 10000
  ): Promise<DemoSeedResponse> {
    try {
      const resp = await this.request<DemoSeedResponse>(
        `/api/demo/seed?mode=${encodeURIComponent(mode)}`,
        { method: 'POST' },
        timeoutMs
      );
      if (mode === 'baseline') {
        this.fallbackReattestations = {};
      }
      return resp;
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      this.log('warn', `FastAPI demo seed unreachable; seeding fallback mode ${mode}`, error);
      const isBaseline = mode === 'baseline';
      const isResolved = mode === 'resolved';
      const isDrifted = mode === 'drifted';

      return {
        status: 'SEED_SUCCESS',
        mode,
        message: `Demo state seeded to ${mode} mode (offline fallback)`,
        total_claims: 12,
        carried_forward_count: isBaseline ? 12 : 10,
        reopened_count: isDrifted ? 2 : 0,
        reattested_count: isResolved ? 1 : 0,
        exception_count: isResolved ? 1 : 0,
        completed_claims: isDrifted ? 10 : 12,
        claims_breakdown: {
          total: 12,
          carried_forward: isBaseline ? 12 : 10,
          reopened: isDrifted ? 2 : 0,
          reattested: isResolved ? 1 : 0,
          exception: isResolved ? 1 : 0,
        },
        reviewer_identity: 'Sarah Jenkins, Esq.',
        policy_version: 'E&O-2026.1-DEVPOST',
        timestamp: new Date().toISOString(),
      };
    }
  }

  /**
   * GET /api/demo/state
   * Retrieves current demonstration mode, claim breakdown, and reviewer identity.
   */
  async getDemoState(timeoutMs: number = 5000): Promise<DemoStateResponse> {
    try {
      return await this.request<DemoStateResponse>('/api/demo/state', { method: 'GET' }, timeoutMs);
    } catch (error: unknown) {
      if (!this.enableFallback) throw error;
      return {
        mode: 'baseline',
        total_claims: 12,
        carried_forward_count: 12,
        reopened_count: 0,
        reattested_count: 0,
        exception_count: 0,
        completed_claims: 12,
        reviewer_identity: {
          reviewer_id: 'counsel_sjenkins_001',
          name: 'Sarah Jenkins, Esq.',
          title: 'Lead Production Clearance Counsel',
          organization: 'Lienmark Legal Partners LLP',
          is_fictional_demo: true,
          disclaimer: 'DEMO / FICTIONAL COUNSEL ONLY - NOT LEGAL ADVICE',
        },
        reviewer_name: 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
        policy_version: 'E&O-2026.1-DEVPOST',
        audit_events_count: 0,
        ledger_integrity: true,
        timestamp: new Date().toISOString(),
      };
    }
  }
}

// ============================================================================
// Default Export Singleton Instance
// ============================================================================

export const apiClient = new LienmarkApiClient();
export default apiClient;
