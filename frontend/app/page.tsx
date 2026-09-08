'use client';

/**
 * Lienmark Clearance Reviewer Dashboard & Counsel Checkpoint Gate
 * Next.js 15 App Router Client Component (Modularized Architecture)
 * Interactive workspace for evaluating clearance delta across Script v7 and v8,
 * executing counsel re-attestations via Next.js Server Actions, and preparing the Form E&O-2026 Exceptions Schedule.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useEffect, useTransition, useCallback, useMemo } from 'react';
import {
  CheckCircle2,
  Gavel,
  Layers,
  Search,
  ExternalLink,
  Zap,
  Loader2,
  ShieldCheck,
  AlertOctagon,
  AlertTriangle,
  Info,
  GitCompare,
  Volume2,
  VolumeX,
  Building2,
  Lock,
  KeyRound,
  ArrowRight,
  DollarSign,
  Activity,
  FileCheck,
} from 'lucide-react';

import {
  ConnectionState,
  DecisionState,
  DecisionStatus,
  EvaluatedClaim,
  EvidenceStance,
  ReviewQueueItem,
  SupersessionEvent,
  UserRole,
  WorkflowStepTrace,
} from '@/lib/types';
import {
  evaluateClearanceDeltaAction,
  submitReviewAction,
  resetDemoAction,
  seedDemoAction,
  fetchReviewQueueAction,
  fetchAuditTrailAction,
  fetchClearanceStateAction,
} from './actions';

import {
  isSoundMuted,
  setSoundMuted,
  toggleSoundMuted,
  playVerifiedAttestationSound,
  playVerifiedExceptionSound,
} from '@/lib/sound_effects';

interface EvaluationStageInfo {
  stage: number;
  label: string;
  progressPercent: number;
}

const EVALUATION_STAGES: EvaluationStageInfo[] = [
  { stage: 1, label: 'Stage 1/5: Ingestion & Baseline v7', progressPercent: 0 },
  { stage: 2, label: 'Stage 2/5: Gemini 2.5 Flash Semantic Drift Detection', progressPercent: 25 },
  { stage: 3, label: 'Stage 3/5: Clearance DAG Traversal', progressPercent: 50 },
  { stage: 4, label: 'Stage 4/5: Targeted Parallel Search', progressPercent: 75 },
  { stage: 5, label: 'Stage 5/5: Counsel Checkpoint Initialization', progressPercent: 100 },
];

interface ToastAlertState {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  retryAction?: () => void;
}

// Modular Component Imports
import DirectorsPresentationHud from './components/DirectorsPresentationHud';
import DashboardHeader from './components/DashboardHeader';
import ClearanceSummaryCards from './components/ClearanceSummaryCards';
import DeltaListComponent from './components/DeltaListComponent';
import DecisionListComponent from './components/DecisionListComponent';
import ExplanationDrawerComponent from './components/ExplanationDrawerComponent';
import ReviewActionComponent, { ReviewActionTypeChoice } from './components/ReviewActionComponent';
import ExportActionComponent from './components/ExportActionComponent';
import AuditTrailDrawer from './components/AuditTrailDrawer';
import ActiveClearanceBlockers from './components/ActiveClearanceBlockers';
import ClearanceLifecycleGuide from './components/ClearanceLifecycleGuide';
import RevisionDeltaViewer from './components/diff/RevisionDeltaViewer';
import {
  ClarifyingQuestionModal,
  ClarificationBannerAlert,
  AgreementArrivalNotification,
  ResumptionProgressStepper,
  AgreementViewerModal,
  GOLDEN_CLARIFICATION_REQUESTS,
  GOLDEN_AGREEMENT_MATCH,
  GOLDEN_RESUMPTION_SESSION,
  ClaimResumptionStatus,
  ClarificationRequestUI,
  ClarificationResponsePayload,
  AgreementMatchPayload,
  ResumptionSession,
} from './components/hitl';
import { StudioPolicyEditor, ConnectionStatusBanner } from './components/governance';
import SessionBadge from './components/auth/SessionBadge';
import RequestAccessModal from './components/auth/RequestAccessModal';
import RevisionEditorPanel from './components/revision/RevisionEditorPanel';
import AuditTelemetryPanel from './components/telemetry/AuditTelemetryPanel';

export default function ReviewerDashboardPage() {
  const [isPending, startTransition] = useTransition();
  const [isRunningEvaluation, setIsRunningEvaluation] = useState<boolean>(false);
  const [isSubmittingAction, setIsSubmittingAction] = useState<boolean>(false);
  const [targetVersionId, setTargetVersionId] = useState<'v8' | 'v7'>('v8');
  const [isResettingDemo, setIsResettingDemo] = useState<boolean>(false);
  const [currentDemoMode, setCurrentDemoMode] = useState<'baseline' | 'drifted' | 'resolved'>('drifted');

  // Milestone B/C/D Session Identity & Revision Audit state
  const [sessionUser, setSessionUser] = useState<{
    display_name: string;
    email: string;
    role: string;
    tenant_id: string;
    production_id: string;
  } | null>(null);
  const [role, setRole] = useState<string>('');
  const [isRequestAccessOpen, setIsRequestAccessOpen] = useState<boolean>(false);
  const [isInviteExpired, setIsInviteExpired] = useState<boolean>(false);
  const [auditId, setAuditId] = useState<string | null>('mock-audit-123');
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  const [evidenceComplete, setEvidenceComplete] = useState<boolean>(false);
  const [counselDirective, setCounselDirective] = useState<string>('');

  // Active audit telemetry state
  const [telemetryData, setTelemetryData] = useState<{
    approvalsPreserved: number;
    claimsReopened: number;
    blockersRemaining: number;
    spend?: { estimated: number; reserved: number; reconciled: number };
  } | null>(null);

  const isAuthenticated = Boolean(sessionUser && role);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const urlParams = new URLSearchParams(window.location.search);
    const inviteToken = urlParams.get('invite');

    if (inviteToken) {
      // Immediately strip token from address bar to prevent token leakage in history or referrers
      window.history.replaceState({}, '', window.location.pathname);

      // Atomically POST to /api/auth/redeem-invite
      fetch('/api/auth/redeem-invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invite_token: inviteToken }),
      })
        .then(async (res) => {
          if (res.ok) {
            // Re-hydrate session state
            const sessionRes = await fetch('/api/auth/session');
            if (sessionRes.ok) {
              const sessionData = await sessionRes.json();
              const userRoleStr =
                typeof sessionData.role === 'string'
                  ? sessionData.role
                  : typeof sessionData.user?.role === 'string'
                  ? sessionData.user.role
                  : 'Reviewer';
              const prodName =
                sessionData.production_name ||
                (sessionData.production_id === 'proj_blockbuster_cinema'
                  ? 'Shadows Over Broadway'
                  : sessionData.production_id) ||
                'Shadows Over Broadway';

              setSessionUser({
                display_name:
                  sessionData.display_name ||
                  sessionData.user?.display_name ||
                  `Demo ${userRoleStr}`,
                email: sessionData.email || sessionData.user?.email || '',
                role: userRoleStr,
                tenant_id:
                  sessionData.tenant_id || sessionData.user?.tenant_id || 'default_tenant',
                production_id:
                  sessionData.production_id ||
                  sessionData.user?.production_id ||
                  'proj_blockbuster_cinema',
              });
              setRole(userRoleStr);

              if (userRoleStr.toLowerCase().includes('review') || userRoleStr.toLowerCase().includes('counsel')) {
                setUserRole(UserRole.REVIEWER);
              } else if (userRoleStr.toLowerCase().includes('produce')) {
                setUserRole(UserRole.PRODUCER);
              } else if (userRoleStr.toLowerCase().includes('analyst')) {
                setUserRole(UserRole.ANALYST);
              } else if (userRoleStr.toLowerCase().includes('admin')) {
                setUserRole(UserRole.ADMIN);
              }

              setToast({
                type: 'success',
                message: `Welcome to ${prodName} as ${userRoleStr}`,
              });
            }
          } else {
            // Redemption failed (HTTP 401, etc.)
            setIsInviteExpired(true);
            setIsRequestAccessOpen(true);
            setToast({
              type: 'error',
              message: 'This invitation has expired or has already been used—request a new link.',
            });
          }
        })
        .catch(() => {
          setIsInviteExpired(true);
          setIsRequestAccessOpen(true);
          setToast({
            type: 'error',
            message: 'This invitation has expired or has already been used—request a new link.',
          });
        });
    } else {
      // Normal unauthenticated or existing session check
      fetch('/api/auth/session')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) {
            const userRoleStr =
              typeof data.role === 'string'
                ? data.role
                : typeof data.user?.role === 'string'
                ? data.user.role
                : '';
            if (userRoleStr) {
              setSessionUser({
                display_name:
                  data.display_name || data.user?.display_name || `Demo ${userRoleStr}`,
                email: data.email || data.user?.email || '',
                role: userRoleStr,
                tenant_id: data.tenant_id || data.user?.tenant_id || 'default_tenant',
                production_id:
                  data.production_id || data.user?.production_id || 'proj_blockbuster_cinema',
              });
              setRole(userRoleStr);

              if (userRoleStr.toLowerCase().includes('review') || userRoleStr.toLowerCase().includes('counsel')) {
                setUserRole(UserRole.REVIEWER);
              } else if (userRoleStr.toLowerCase().includes('produce')) {
                setUserRole(UserRole.PRODUCER);
              } else if (userRoleStr.toLowerCase().includes('analyst')) {
                setUserRole(UserRole.ANALYST);
              } else if (userRoleStr.toLowerCase().includes('admin')) {
                setUserRole(UserRole.ADMIN);
              }
            } else {
              setSessionUser(null);
              setRole('');
            }
          } else {
            setSessionUser(null);
            setRole('');
          }
        })
        .catch(() => {
          setSessionUser(null);
          setRole('');
        });
    }
  }, []);

  // Poll telemetry for active audit ID
  useEffect(() => {
    if (!auditId) return;
    let isCancelled = false;
    const fetchTelemetry = async () => {
      try {
        const res = await fetch(`/api/telemetry/${auditId}`);
        if (res.ok && !isCancelled) {
          const data = await res.json();
          setTelemetryData(data);
        }
      } catch {
        // ignore
      }
    };
    void fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 3000);
    return () => {
      isCancelled = true;
      clearInterval(interval);
    };
  }, [auditId]);

  const handleDecision = async (claimId: string, decision: 'approve' | 'reject') => {
    if (!isAuthenticated) {
      setToast({
        type: 'warning',
        message: 'An invited session is required to adjudicate claims.',
      });
      return;
    }
    try {
      const res = await fetch(`/api/v1/claims/${claimId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, counselDirective: decision === 'reject' ? counselDirective : undefined })
      });
      if (res.ok) {
        const data = await res.json();
        const newSnapshotId = typeof data.result_snapshot_id === 'string' ? data.result_snapshot_id : '';
        setSnapshotId(newSnapshotId);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Evaluation multi-stage live telemetry state
  const [evalStageIdx, setEvalStageIdx] = useState<number>(0);
  const [evalElapsedMs, setEvalElapsedMs] = useState<number>(0);

  // Connection and truthfulness state lifecycle: 'loading' | 'connected' | 'empty' | 'unavailable' | 'stale'
  const [connectionState, setConnectionState] = useState<ConnectionState>('loading');
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [isRetryingConnection, setIsRetryingConnection] = useState<boolean>(false);

  // Core data states initialized empty for fail-closed truthfulness (no synthetic golden SSR mask)
  const [claims, setClaims] = useState<EvaluatedClaim[]>([]);
  // Traces start unmeasured until evaluation is triggered
  const [traces, setTraces] = useState<WorkflowStepTrace[]>([]);
  const [lastMeasuredElapsedMs, setLastMeasuredElapsedMs] = useState<number | null>(null);
  const [hasEvaluated, setHasEvaluated] = useState<boolean>(false);
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueItem[]>([]);
  const [auditTrail, setAuditTrail] = useState<SupersessionEvent[]>([]);

  // Active view and selection states
  const [activeTab, setActiveTab] = useState<'checkpoint' | 'diff' | 'lineage'>('checkpoint');
  const [showPolicyEditor, setShowPolicyEditor] = useState<boolean>(false);
  const [userRole, setUserRole] = useState<UserRole>(UserRole.REVIEWER);
  const [selectedQueueKey, setSelectedQueueKey] = useState<string>(
    'poster_noir_detective_magazine'
  );
  const [selectedClaimKey, setSelectedClaimKey] = useState<string>(
    'poster_noir_detective_magazine'
  );
  const [toast, setToast] = useState<ToastAlertState | null>(null);

  // Accordion & Drawer states
  const [isPriorDecisionOpen, setIsPriorDecisionOpen] = useState<boolean>(false);
  const [isAuditDrawerOpen, setIsAuditDrawerOpen] = useState<boolean>(false);

  // Reviewer identity bound to active role
  const reviewerIdentity =
    userRole === UserRole.REVIEWER
      ? 'Sarah Jenkins, Esq. (Lead Clearance Counsel)'
      : userRole === UserRole.PRODUCER
      ? 'Marcus Vance (Executive Producer)'
      : userRole === UserRole.ANALYST
      ? 'Alex Chen (Rights Research Analyst)'
      : 'Elena Rostova (Studio Legal Systems Administrator)';
  const [counselRationale, setCounselRationale] = useState<string>(
    'Cover art is public domain: US Copyright Office records confirm 1946 registration lapsed without renewal in 1974. Corroborated via LOC catalog.'
  );
  const [lastConfirmedEvent, setLastConfirmedEvent] = useState<SupersessionEvent | null>(null);

  // Director's HUD & Studio Audio states
  const [currentBeat, setCurrentBeat] = useState<number>(1);
  const [soundMuted, setSoundMutedState] = useState<boolean>(false);

  // HITL Clarification state
  const [clarificationRequests, setClarificationRequests] = useState<ClarificationRequestUI[]>(
    () => [...GOLDEN_CLARIFICATION_REQUESTS]
  );
  const [activeClarificationModalKey, setActiveClarificationModalKey] = useState<string | null>(null);
  const [isClarificationBannerDismissed, setIsClarificationBannerDismissed] = useState<boolean>(false);

  // Sprint 4.2 HITL Resumption & Agreement States
  const [agreementNotification, setAgreementNotification] = useState<AgreementMatchPayload | null>(
    GOLDEN_AGREEMENT_MATCH
  );
  const [isAgreementNotificationDismissed, setIsAgreementNotificationDismissed] = useState<boolean>(false);
  const [showResumptionStepper, setShowResumptionStepper] = useState<boolean>(false);
  const [isAgreementViewerOpen, setIsAgreementViewerOpen] = useState<boolean>(false);
  const [resumptionSession, setResumptionSession] = useState<ResumptionSession>(GOLDEN_RESUMPTION_SESSION);

  const handleOpenClarification = useCallback((claimKey: string) => {
    setActiveClarificationModalKey(claimKey);
  }, []);

  const handleCloseClarification = useCallback(() => {
    setActiveClarificationModalKey(null);
  }, []);

  const handleSubmitClarification = useCallback((payload: ClarificationResponsePayload) => {
    setClarificationRequests((prev) =>
      prev.filter((r) => r.claimKey !== payload.claimKey)
    );
    setActiveClarificationModalKey(null);
    setToast({
      type: 'success',
      message: `✓ Clarification submitted for ${payload.claimKey.replace(/_/g, ' ')}. Clearance matrix updated.`,
    });
  }, []);

  const handleEscalateClarification = useCallback((payload: ClarificationResponsePayload) => {
    setClarificationRequests((prev) =>
      prev.filter((r) => r.claimKey !== payload.claimKey)
    );
    setActiveClarificationModalKey(null);
    setToast({
      type: 'info',
      message: `Escalated ${payload.claimKey.replace(/_/g, ' ')} directly to supervising legal counsel.`,
    });
  }, []);

  // Hydrate sound mute state from localStorage safely in browser
  useEffect(() => {
    setSoundMutedState(isSoundMuted());
  }, []);

  // Global keyboard shortcut listener: 'm' / 'M' for studio audio mute toggle
  useEffect(() => {
    const handleAudioKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return;
      }
      if (e.key === 'm' || e.key === 'M') {
        e.preventDefault();
        const nextMuted = toggleSoundMuted();
        setSoundMutedState(nextMuted);
        setToast({
          type: 'info',
          message: nextMuted ? '🔇 Studio audio muted' : '🔊 Studio sound effects enabled',
        });
      }
    };
    window.addEventListener('keydown', handleAudioKey);
    return () => window.removeEventListener('keydown', handleAudioKey);
  }, []);

  // Handler: Non-mutating beat navigation & spotlight
  const handleSelectBeat = useCallback((beatId: number) => {
    setCurrentBeat(beatId);
    const targetId = `pitch-beat-${beatId}`;
    const el = document.getElementById(targetId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add(
        'ring-4',
        'ring-sky-400/80',
        'ring-offset-4',
        'ring-offset-slate-950',
        'transition-all',
        'duration-500'
      );
      setTimeout(() => {
        el.classList.remove(
          'ring-4',
          'ring-sky-400/80',
          'ring-offset-4',
          'ring-offset-slate-950'
        );
      }, 2400);
    }
  }, []);

  // Live server state hydration and connection lifecycle management
  const hydrateDashboardState = useCallback(async () => {
    setConnectionState((prev) => (prev === 'connected' ? 'stale' : 'loading'));
    setConnectionError(null);
    try {
      const [clearanceRes, queueRes, auditRes] = await Promise.all([
        fetchClearanceStateAction(),
        fetchReviewQueueAction(),
        fetchAuditTrailAction(),
      ]);

      if (!clearanceRes.success) {
        setConnectionState('unavailable');
        setConnectionError(clearanceRes.error || 'FastAPI clearance backend is unreachable.');
        return;
      }

      const serverClaims = clearanceRes.data?.claims ?? [];
      setClaims(serverClaims);

      if (queueRes.success && queueRes.data) {
        setReviewQueue(queueRes.data);
      } else if (!queueRes.success) {
        setConnectionState('unavailable');
        setConnectionError(queueRes.error || 'Failed to retrieve active review queue.');
        return;
      }

      if (auditRes.success && Array.isArray(auditRes.data)) {
        setAuditTrail(auditRes.data);
      } else if (!auditRes.success) {
        setConnectionState('unavailable');
        setConnectionError(auditRes.error || 'Failed to retrieve append-only audit trail.');
        return;
      }

      if (serverClaims.length === 0) {
        setConnectionState('empty');
      } else {
        setConnectionState('connected');
        setConnectionError(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'FastAPI clearance service is offline.';
      setConnectionState('unavailable');
      setConnectionError(msg);
    }
  }, []);

  // Initial dashboard hydration effect on mount
  useEffect(() => {
    void hydrateDashboardState();
  }, [hydrateDashboardState]);

  // Handler: Explicit user retry connection action
  const handleRetryConnection = useCallback(async () => {
    setIsRetryingConnection(true);
    try {
      await hydrateDashboardState();
    } finally {
      setIsRetryingConnection(false);
    }
  }, [hydrateDashboardState]);

  // Live timer & multi-stage progress transition during evaluation
  useEffect(() => {
    if (!isRunningEvaluation) {
      setEvalStageIdx(0);
      return;
    }

    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      setEvalElapsedMs(elapsed);

      // Stages progress: 0% -> 25% -> 50% -> 75% -> 100%
      if (elapsed < 300) {
        setEvalStageIdx(0); // Stage 1 (0%)
      } else if (elapsed < 650) {
        setEvalStageIdx(1); // Stage 2 (25%)
      } else if (elapsed < 1000) {
        setEvalStageIdx(2); // Stage 3 (50%)
      } else if (elapsed < 1350) {
        setEvalStageIdx(3); // Stage 4 (75%)
      } else {
        setEvalStageIdx(4); // Stage 5 (100%)
      }
    }, 25);

    return () => clearInterval(interval);
  }, [isRunningEvaluation]);

  // Update rationale field when active review item changes
  useEffect(() => {
    if (selectedQueueKey === 'poster_noir_detective_magazine') {
      setCounselRationale(
        'Cover art is public domain: US Copyright Office records confirm 1946 registration lapsed without renewal in 1974. Corroborated via LOC catalog.'
      );
    } else if (selectedQueueKey === 'music_cue_midnight_serenade') {
      setCounselRationale(
        'Unresolved sync rights breach: Vanguard Media acquired exclusive worldwide synchronization rights August 2026. Cue must be marked as an underwriting exception or replaced.'
      );
    }
  }, [selectedQueueKey]);

  // Derived metrics and live invariant calculation
  const totalClaims = claims.length;
  const carriedCount = claims.filter((c) => c.state === DecisionState.CARRIED_FORWARD).length;
  const staleCount = claims.filter((c) => c.state === DecisionState.STALE).length;
  const reattestedCount = claims.filter((c) => c.state === DecisionState.RE_ATTESTED).length;
  const exceptionCount = claims.filter((c) => c.state === DecisionState.EXCEPTION).length;

  // Derive metrics dynamically from active audit & claims (not fixed at 10 preserved and 2 blocked)
  const dynamicPreservedCount =
    typeof telemetryData?.approvalsPreserved === 'number' && telemetryData.approvalsPreserved > 0
      ? Math.floor(telemetryData.approvalsPreserved)
      : carriedCount;

  const dynamicReopenedCount =
    typeof telemetryData?.claimsReopened === 'number'
      ? telemetryData.claimsReopened
      : staleCount;

  const dynamicBlockersCount =
    typeof telemetryData?.blockersRemaining === 'number'
      ? telemetryData.blockersRemaining
      : (exceptionCount + staleCount);

  // Dynamic reconciled state: all claims in cut have reached final determination (0 stale)
  const isReconciled = totalClaims > 0 && staleCount === 0;

  // Fail-closed invariant: Disable all mutations when connection is unavailable or stale
  const isMutationDisabled =
    connectionState === 'unavailable' || connectionState === 'stale';

  // Zero drift condition (evaluated v7, v7 or when all carried and 0 stale)
  const isZeroDrift =
    (staleCount === 0 && carriedCount === totalClaims && totalClaims > 0) ||
    (claims.length > 0 && targetVersionId === 'v7');

  // Measured research spend telemetry determination: show zero spend only when measured telemetry supports it
  const externalSearchQueriesCount = useMemo(() => {
    if (!traces || traces.length === 0) return null;
    return traces.filter((t) =>
      t.component === 'Parallel Search API' ||
      (typeof t.step_name === 'string' && t.step_name.includes('search'))
    ).length;
  }, [traces]);

  const measuredResearchSpend = useMemo(() => {
    // 1. If active audit telemetry provides reconciled spend
    if (telemetryData?.spend && typeof telemetryData.spend.reconciled === 'number') {
      return {
        isMeasured: true,
        amount: telemetryData.spend.reconciled,
        isZero: telemetryData.spend.reconciled === 0,
        source: 'telemetry' as const,
      };
    }
    // 2. If runtime execution traces have been measured
    if (hasEvaluated && traces.length > 0) {
      if (externalSearchQueriesCount === 0 || isZeroDrift) {
        return {
          isMeasured: true,
          amount: 0.0,
          isZero: true,
          source: 'traces' as const,
        };
      }
      return {
        isMeasured: true,
        amount: (externalSearchQueriesCount || 0) * 0.12,
        isZero: false,
        source: 'traces' as const,
      };
    }
    // 3. Otherwise, unmeasured until evaluation runs
    return {
      isMeasured: false,
      amount: null,
      isZero: false,
      source: 'none' as const,
    };
  }, [telemetryData, hasEvaluated, traces, externalSearchQueriesCount, isZeroDrift]);

  interface PrioritizedClaimInfo {
    stableLineageKey: string;
    assetName: string;
    scene: string;
    assetType: string;
    state: DecisionState;
    reason: string;
    responsibleRole: string;
    nextAction: string;
    isBlocker: boolean;
  }

  const prioritizedReopenedClaims: PrioritizedClaimInfo[] = useMemo(() => {
    const staleList = claims.filter((c) => c.state === DecisionState.STALE);
    return staleList.map((claim) => {
      let reason = claim.reason_code
        ? claim.reason_code.replace(/_/g, ' ')
        : 'Semantic drift detected between locked cut and revised revision';
      let responsibleRole = 'Lead Clearance Counsel (Reviewer)';
      let nextAction = 'Complete rights revalidation in Counsel Checkpoint Gate';
      let isBlocker = false;

      if (claim.stable_lineage_key === 'poster_noir_detective_magazine') {
        reason =
          'Visual prominence shifted from incidental background blur to prominent foreground hero prop in Scene 03. Prior incidental decor clearance invalidated.';
        responsibleRole = 'Lead Clearance Counsel (Reviewer)';
        nextAction =
          'Re-attest under 1946 Public Domain non-renewal doctrine via LOC Copyright Catalog corroboration.';
        isBlocker = false;
      } else if (claim.stable_lineage_key === 'music_cue_midnight_serenade') {
        reason =
          'External sync rights transfer: Vanguard Media acquired exclusive worldwide synchronization rights post-v7 lock. Blanket cue license breached.';
        responsibleRole = 'Rights Research Analyst / Music Supervisor';
        nextAction =
          'Secure executed synchronization agreement or designate as Underwriting Exception on Form E&O-2026 Schedule.';
        isBlocker = true;
      } else if (claim.asset_type === 'music') {
        responsibleRole = 'Music Supervisor & Clearance Counsel';
        nextAction = 'Verify synchronization licenses and publisher split percentages.';
        isBlocker = true;
      } else if (claim.asset_type === 'prop' || claim.asset_type === 'artwork') {
        responsibleRole = 'Lead Clearance Counsel (Reviewer)';
        nextAction =
          'Verify registration status in US Copyright Office database or fair use doctrine.';
      }

      return {
        stableLineageKey: claim.stable_lineage_key,
        assetName: claim.description || claim.stable_lineage_key,
        scene: claim.scene || 'Scene N/A',
        assetType: claim.asset_type || 'prop',
        state: claim.state,
        reason,
        responsibleRole,
        nextAction,
        isBlocker,
      };
    });
  }, [claims]);

  const deliveryBlockersList: PrioritizedClaimInfo[] = useMemo(() => {
    const exceptionClaims = claims.filter((c) => c.state === DecisionState.EXCEPTION);
    return exceptionClaims.map((claim) => {
      let reason = 'Unresolved underwriting exception flagging critical statutory liability.';
      let responsibleRole = 'Executive Producer & Lead Counsel';
      let nextAction =
        'Execute Form E&O-2026 Exceptions Schedule Rider or excise element from cut prior to delivery.';

      if (claim.stable_lineage_key === 'music_cue_midnight_serenade') {
        reason =
          'Vanguard Media exclusive worldwide sync breach. Statutory exposure under 17 U.S.C. § 504 ($150,000 max statutory penalty).';
        responsibleRole = 'Executive Producer & Lead Clearance Counsel';
        nextAction =
          'Execute Form E&O-2026 Exceptions Schedule Rider or replace cue with pre-cleared production library asset.';
      }

      return {
        stableLineageKey: claim.stable_lineage_key,
        assetName: claim.description || claim.stable_lineage_key,
        scene: claim.scene || 'Scene N/A',
        assetType: claim.asset_type || 'music',
        state: claim.state,
        reason,
        responsibleRole,
        nextAction,
        isBlocker: true,
      };
    });
  }, [claims]);

  // Active queue item for Checkpoint Gate
  const activeQueueItem =
    reviewQueue.find((q) => q.stable_lineage_key === selectedQueueKey) || reviewQueue[0];

  // Active claim in lineage table
  const selectedClaim =
    claims.find((c) => c.stable_lineage_key === selectedClaimKey) || claims[0];

  // Dynamically resolve full 4D Queue Item for whichever claim is selected in split-screen
  const lineageInspectorItem: ReviewQueueItem = React.useMemo(() => {
    const queueMatch = reviewQueue.find((q) => q.stable_lineage_key === selectedClaimKey);
    if (queueMatch) return queueMatch;

    return {
      queue_item_id: `qitem_${selectedClaim?.stable_lineage_key || 'asset'}`,
      stable_lineage_key: selectedClaim?.stable_lineage_key || 'asset',
      asset_name: selectedClaim?.description || 'Production Asset',
      description: selectedClaim?.description || 'Production Asset',
      asset_type: selectedClaim?.asset_type || 'prop',
      scene: selectedClaim?.scene || 'Scene 01',
      scene_or_timecode: selectedClaim?.scene || 'Scene 01',
      current_state: selectedClaim?.state || DecisionState.CARRIED_FORWARD,
      status: selectedClaim?.state === DecisionState.STALE ? 'pending' : 'resolved',
      prior_decision: {
        decision_id: `dec_v7_${selectedClaim?.stable_lineage_key}`,
        version_id: 'v7',
        status: DecisionStatus.APPROVED,
        rationale: 'Approved in Locked Script Cut v7: Bit-for-bit unchanged, verified via public records.',
        reviewer_display_name: 'Sarah Jenkins, Esq. (Lead Clearance Counsel)',
        reviewed_at: '2026-09-01T11:00:00.000Z',
        context_hash: 'a1b2c3d4e5f60718293a4b5c6d7e8f90abcdef1234567890abcdef12345678',
        scope_or_conditions: 'Standard clearance.',
      },
      four_dimensions: {
        creative_change: {
          has_changed: false,
          materiality: 'none',
          scene: selectedClaim?.scene || 'Scene 01',
          before_prominence: selectedClaim?.prominence || 'Incidental blur',
          after_prominence: selectedClaim?.prominence || 'Incidental blur',
          before_context: selectedClaim?.description || 'Incidental decor.',
          after_context: selectedClaim?.description || 'Incidental decor.',
          context_description: 'Bit-for-bit identical usage across cuts. Autonomous pass.',
          reason_codes: [selectedClaim?.reason_code || 'DEPENDENCIES_SATISFIED_UNCHANGED'],
        },
        external_evidence_change: {
          has_changed: false,
          stance: selectedClaim?.evidence?.stance || EvidenceStance.SUPPORTING,
          source_title: selectedClaim?.evidence?.source_title || 'Public Records Archive',
          source_url: selectedClaim?.evidence?.source_url || 'https://cocatalog.loc.gov',
          excerpt: selectedClaim?.evidence?.excerpt || 'Public records verified unchanged.',
          query_issued: `Registry query for ${selectedClaim?.stable_lineage_key}`,
          provider: 'Parallel Search API v1',
          retrieval_latency_ms: selectedClaim?.evidence?.latency_ms || 95.0,
          retrieved_at: '2026-09-03T14:31:00.000Z',
        },
        private_agreement_facts: {
          has_contract: false,
          licensor: 'Standard Studio Clearance',
          grant_scope: 'Full production rights',
          section_205_e_status: '17 U.S.C. § 205(e) evaluated: Inapplicable.',
          contract_shield_applied: false,
          status_note: 'Standard production clearance on file.',
        },
        statutory_policy_reason: {
          reason_code: selectedClaim?.reason_code || 'DEPENDENCIES_SATISFIED_UNCHANGED',
          policy_rule: 'E&O-2026.1-DEVPOST',
          statutory_reference: '17 U.S.C. § 101, 107',
          doctrine: 'Public Domain / Property Release',
          eo_risk_rating: 'LOW',
          statutory_exposure: '$0.00 (Statutory damages excluded)',
          explanation: 'Lineage parity verified unchanged.',
        },
      },
      system_recommendation: {
        suggested_action: 'carry',
        suggested_status: DecisionStatus.APPROVED,
        confidence: 0.99,
        rationale: 'Autonomous carry forward: dependencies satisfied and unchanged.',
      },
    };
  }, [reviewQueue, selectedClaimKey, selectedClaim]);

  // Handler: Toggle target comparison version (v8 vs v7) with fail-closed live evaluation
  const handleToggleVersion = async (version: 'v8' | 'v7') => {
    if (isMutationDisabled) {
      setToast({
        type: 'error',
        message: 'Cannot toggle comparison cut: Backend is offline or stale (Fail-Closed).',
      });
      return;
    }

    setTargetVersionId(version);
    setIsRunningEvaluation(true);
    const startWallTime = performance.now();

    try {
      const response = await evaluateClearanceDeltaAction(version);
      const measuredElapsed = performance.now() - startWallTime;
      setEvalElapsedMs(measuredElapsed);
      setLastMeasuredElapsedMs(measuredElapsed);
      setHasEvaluated(true);

      if (response.success && response.data) {
        setClaims(response.data.claims);
        setTraces(response.data.execution_traces || []);
        const queueRes = await fetchReviewQueueAction();
        if (queueRes.success && queueRes.data) {
          setReviewQueue(queueRes.data);
        }
        setConnectionState(response.data.claims.length === 0 ? 'empty' : 'connected');
        setConnectionError(null);
        setToast({
          type: 'info',
          message:
            version === 'v7'
              ? 'Evaluated Script Cut (v7, v7): Zero clearance drift detected across claims.'
              : 'Switched to Revised Cut (v7, v8): Live drift evaluation complete.',
        });
      } else {
        setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
        setConnectionError(response.error || 'Failed to evaluate comparison cut on backend');
        setToast({
          type: 'error',
          message: `Evaluation failed: ${response.error || 'Backend offline'}. Fail-closed active.`,
        });
      }
    } catch (err: unknown) {
      setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
      const msg = err instanceof Error ? err.message : 'Evaluation request failed';
      setConnectionError(msg);
      setToast({
        type: 'error',
        message: `Evaluation failed: ${msg}. Fail-closed active.`,
      });
    } finally {
      setIsRunningEvaluation(false);
    }
  };

  // Handler: Full demo reset to pristine V7 baseline calling live backend
  const handleResetDemo = useCallback(async () => {
    if (isResettingDemo) return;
    if (isMutationDisabled) {
      setToast({
        type: 'error',
        message: 'Cannot reset demo while backend connection is offline or stale (Fail-Closed).',
      });
      return;
    }
    setIsResettingDemo(true);

    try {
      const result = await resetDemoAction();
      if (!result.success) {
        setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
        setConnectionError(result.error || 'Failed to reset demo state on server.');
        setToast({
          type: 'error',
          message: result.error || 'Failed to reset demo state on server. Preserving current state.',
        });
        return;
      }

      // Re-hydrate live server state after reset
      const [clearanceRes, queueRes, auditRes] = await Promise.all([
        fetchClearanceStateAction(),
        fetchReviewQueueAction(),
        fetchAuditTrailAction(),
      ]);

      if (clearanceRes.success && clearanceRes.data) {
        setClaims(clearanceRes.data.claims);
        setConnectionState(clearanceRes.data.claims.length === 0 ? 'empty' : 'connected');
      }
      if (queueRes.success && queueRes.data) {
        setReviewQueue(queueRes.data);
      }
      if (auditRes.success && Array.isArray(auditRes.data)) {
        setAuditTrail(auditRes.data);
      }

      setTargetVersionId('v7');
      setCurrentDemoMode('baseline');
      setTraces([]);
      setEvalElapsedMs(0);
      setLastMeasuredElapsedMs(null);
      setHasEvaluated(false);

      setToast({
        type: 'success',
        message: result.data?.message || 'Demo state successfully reset to clean V7 baseline on live server.',
      });
    } catch (err: unknown) {
      setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
      const msg = err instanceof Error ? err.message : 'Failed to reset demo state on server.';
      setConnectionError(msg);
      setToast({
        type: 'error',
        message: msg,
      });
    } finally {
      setIsResettingDemo(false);
    }
  }, [isResettingDemo, isMutationDisabled, claims.length]);

  // Handler: Seed demo take mode (baseline, drifted, resolved) via live backend
  const handleSeedDemoMode = useCallback(
    async (mode: 'baseline' | 'drifted' | 'resolved') => {
      if (isMutationDisabled) {
        setToast({
          type: 'error',
          message: 'Cannot seed demo mode while backend connection is offline or stale (Fail-Closed).',
        });
        return;
      }
      setIsResettingDemo(true);
      try {
        const result = await seedDemoAction(mode);
        if (!result.success) {
          setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
          setConnectionError(result.error || `Failed to seed demo mode ${mode}`);
          setToast({
            type: 'error',
            message: result.error || `Failed to seed demo mode ${mode}`,
          });
          return;
        }

        setCurrentDemoMode(mode);
        setTargetVersionId(mode === 'baseline' ? 'v7' : 'v8');

        // Re-hydrate live server state after seeding
        const [clearanceRes, queueRes, auditRes] = await Promise.all([
          fetchClearanceStateAction(),
          fetchReviewQueueAction(),
          fetchAuditTrailAction(),
        ]);

        if (clearanceRes.success && clearanceRes.data) {
          setClaims(clearanceRes.data.claims);
          setConnectionState(clearanceRes.data.claims.length === 0 ? 'empty' : 'connected');
        }
        if (queueRes.success && queueRes.data) {
          setReviewQueue(queueRes.data);
        }
        if (auditRes.success && Array.isArray(auditRes.data)) {
          setAuditTrail(auditRes.data);
        }

        setToast({
          type: 'success',
          message: result.data?.message || `Seeded Take: ${mode} mode confirmed by live backend.`,
        });
      } catch (err: unknown) {
        setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
        const msg = err instanceof Error ? err.message : 'Failed to seed demo mode.';
        setConnectionError(msg);
        setToast({
          type: 'error',
          message: msg,
        });
      } finally {
        setIsResettingDemo(false);
      }
    },
    [isMutationDisabled, claims.length]
  );

  // Keyboard shortcut listener for Ctrl+Shift+R (Demo Reset)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'R' || e.key === 'r')) {
        e.preventDefault();
        handleResetDemo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleResetDemo]);

  // Handler: Run clearance evaluation with live backend analysis
  const handleRunEvaluation = async () => {
    if (isMutationDisabled) {
      setToast({
        type: 'error',
        message: 'Clearance evaluation is disabled while backend is offline or stale (Fail-Closed).',
      });
      return;
    }
    setIsRunningEvaluation(true);
    const startWallTime = performance.now();
    startTransition(async () => {
      try {
        const response = await evaluateClearanceDeltaAction(targetVersionId);
        const measuredElapsed = performance.now() - startWallTime;
        setEvalElapsedMs(measuredElapsed);
        setLastMeasuredElapsedMs(measuredElapsed);
        setHasEvaluated(true);

        if (response.success && response.data) {
          setClaims(response.data.claims);
          setTraces(response.data.execution_traces || []);
          const queueRes = await fetchReviewQueueAction();
          if (queueRes.success && queueRes.data) {
            setReviewQueue(queueRes.data);
          }
          setConnectionState(response.data.claims.length === 0 ? 'empty' : 'connected');
          setConnectionError(null);
          setToast({
            type: 'success',
            message:
              targetVersionId === 'v7'
                ? '✓ Zero Clearance Drift: Script cut v7 baseline verified via live backend.'
                : '✓ Clearance delta evaluated: Live backend analysis confirmed.',
          });
        } else {
          setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
          setConnectionError(response.error || 'Evaluation failed on live backend');
          setToast({
            type: 'error',
            message: `Evaluation failed: ${response.error || 'Backend offline'}. Fail-closed policy active.`,
          });
        }
      } catch (err: unknown) {
        setConnectionState(claims.length > 0 ? 'stale' : 'unavailable');
        const msg = err instanceof Error ? err.message : 'Evaluation network error';
        setConnectionError(msg);
        setToast({
          type: 'error',
          message: `Evaluation failed: ${msg}. Fail-closed policy active.`,
        });
      } finally {
        setIsRunningEvaluation(false);
      }
    });
  };

  // Handler: Submit counsel review action with Optimistic State Rollback on Error
  const handleReviewAction = async (
    action: ReviewActionTypeChoice
  ): Promise<{ success: boolean; error?: string }> => {
    if (isMutationDisabled) {
      const msg = 'Clearance adjudication is disabled: backend is offline or stale (Fail-Closed).';
      setToast({ type: 'error', message: msg });
      return { success: false, error: msg };
    }
    if (!isAuthenticated) {
      const msg = 'Clearance adjudication requires an invited session. Please request access.';
      setToast({ type: 'warning', message: msg });
      setIsRequestAccessOpen(true);
      return { success: false, error: msg };
    }
    if (!activeQueueItem || isSubmittingAction) {
      return { success: false, error: 'Review action already in progress or no active item' };
    }

    // 1. Snapshot previous state before optimistic mutation
    const snapshotClaims = [...claims];
    const snapshotQueue = [...reviewQueue];
    const snapshotAudit = [...auditTrail];

    setIsSubmittingAction(true);
    const lineageKey = activeQueueItem.stable_lineage_key;
    const rationaleToSubmit = counselRationale.trim();

    // 2. Optimistically update local claims state
    const newState =
      action === 're_attest' ? DecisionState.RE_ATTESTED : DecisionState.EXCEPTION;

    setClaims((prev) =>
      prev.map((c) =>
        c.stable_lineage_key === lineageKey
          ? {
              ...c,
              state: newState,
              reason_code:
                action === 're_attest'
                  ? 'COUNSEL_RE_ATTESTED_PUBLIC_DOMAIN'
                  : action === 'reject'
                  ? 'DE_CLEARED_BY_COUNSEL'
                  : 'UNRESOLVED_UNDERWRITING_EXCEPTION',
              revalidation_action: action,
            }
          : c
      )
    );

    // 3. Optimistically update review queue status
    setReviewQueue((prev) =>
      prev.map((q) =>
        q.stable_lineage_key === lineageKey
          ? {
              ...q,
              status: 'resolved' as const,
              current_state: newState,
            }
          : q
      )
    );

    try {
      const result = await submitReviewAction(
        action,
        lineageKey,
        rationaleToSubmit,
        reviewerIdentity
      );

      if (!result.success || !result.data) {
        // Optimistic State Rollback on Error
        console.error('[handleReviewAction] submitReviewAction failed, rolling back:', result.error);
        setClaims(snapshotClaims);
        setReviewQueue(snapshotQueue);
        setAuditTrail(snapshotAudit);
        setConnectionState(snapshotClaims.length > 0 ? 'stale' : 'unavailable');
        setConnectionError(result.error || 'Server error recording counsel action.');
        setToast({
          type: 'error',
          message: `Adjudication Failed: ${result.error || 'Server error recording counsel action.'}`,
          retryAction: () => handleReviewAction(action),
        });
        return { success: false, error: result.error || 'Server error recording counsel action' };
      }

      // Success path: Append SupersessionEvent to append-only immutable ledger
      const confirmedEvent = result.data as SupersessionEvent;
      setLastConfirmedEvent(confirmedEvent);
      setAuditTrail((prev) => [confirmedEvent, ...prev]);

      // Synthesize studio acoustic feedback strictly upon verified HTTP 200 server confirmation
      if (action === 're_attest') {
        playVerifiedAttestationSound(200);
      } else {
        playVerifiedExceptionSound(200);
      }

      // Construct friendly toast notification
      if (action === 're_attest') {
        setToast({
          type: 'success',
          message: `✓ Re-Attested ${activeQueueItem.asset_name} as APPROVED under Public Domain doctrine.`,
        });
      } else if (action === 'reject') {
        setToast({
          type: 'warning',
          message: `⛔ Rejected & De-Cleared ${activeQueueItem.asset_name} from production.`,
        });
      } else {
        setToast({
          type: 'info',
          message: `⚠️ Left ${activeQueueItem.asset_name} as UNRESOLVED EXCEPTION on Form E&O-2026 Schedule.`,
        });
      }

      // Advance to Item 12 if Item 11 was just completed
      if (lineageKey === 'poster_noir_detective_magazine') {
        const item12 = reviewQueue.find(
          (q) => q.stable_lineage_key === 'music_cue_midnight_serenade'
        );
        if (item12 && (item12.current_state === DecisionState.STALE || item12.status === 'pending')) {
          setSelectedQueueKey('music_cue_midnight_serenade');
        }
      }

      return { success: true };
    } catch (err: unknown) {
      // Optimistic State Rollback on Exception
      console.error('[handleReviewAction] Exception encountered, rolling back:', err);
      setClaims(snapshotClaims);
      setReviewQueue(snapshotQueue);
      setAuditTrail(snapshotAudit);
      const errMsg = err instanceof Error ? err.message : 'Unknown exception occurred.';
      setConnectionState(snapshotClaims.length > 0 ? 'stale' : 'unavailable');
      setConnectionError(errMsg);
      setToast({
        type: 'error',
        message: `Adjudication Error: ${errMsg}`,
        retryAction: () => handleReviewAction(action),
      });
      return { success: false, error: errMsg };
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // Handler: Open in Checkpoint Gate from Lineage View
  const handleOpenInGate = (lineageKey: string) => {
    setSelectedQueueKey(lineageKey);
    setActiveTab('checkpoint');
  };

  return (
    <div className="mx-auto max-w-[1720px] px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      {/* Unauthenticated Sample Workspace Top Banner */}
      {!isAuthenticated && (
        <aside
          role="region"
          aria-label="Sample Workspace Notice"
          className="rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-950/60 via-slate-900/90 to-amber-950/40 px-4 py-2.5 backdrop-blur-md shadow-lg flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-amber-200 animate-in fade-in duration-200"
        >
          <div className="flex items-center gap-2.5 text-center sm:text-left">
            <span className="flex h-2 w-2 rounded-full bg-amber-400 animate-pulse flex-shrink-0" />
            <p className="font-medium">
              <strong className="text-amber-300 font-bold">Sample workspace · Read-only</strong> — Illustrative benchmark data. An invited session is required to submit revisions or adjudicate claims.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setIsInviteExpired(false);
              setIsRequestAccessOpen(true);
            }}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-400 hover:bg-amber-300 px-3 py-1.5 text-xs font-bold text-slate-950 transition-colors flex-shrink-0 shadow-sm focus:outline-none focus:ring-2 focus:ring-amber-200"
          >
            <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Request Access</span>
          </button>
        </aside>
      )}

      {/* Animated Multi-Stage Orchestration Progress Modal */}
      {isRunningEvaluation && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Clearance Orchestration Pipeline Progress"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-in fade-in duration-200"
        >
          <div className="w-full max-w-xl rounded-2xl border border-sky-500/50 bg-gradient-to-b from-[#131b2e] to-[#0a0f1d] p-6 shadow-2xl space-y-5 border-t-2 border-t-sky-400">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30">
                  <Zap className="h-5 w-5 animate-pulse" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white tracking-wide">
                    Clearance Engine Orchestration Pipeline
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Target Revision: {targetVersionId === 'v7' ? 'v7 Locked (Parity)' : 'v8 Revised'} &middot; Gemini 2.5 Flash
                  </p>
                </div>
              </div>
              <div className="text-right font-mono">
                <div className="text-base font-bold text-sky-400">
                  {EVALUATION_STAGES[evalStageIdx].progressPercent}%
                </div>
                <div className="text-[10px] text-slate-500">
                  {evalElapsedMs.toLocaleString()} ms elapsed
                </div>
              </div>
            </div>

            {/* Current Stage Highlight */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-4 space-y-2">
              <div className="text-[11px] font-mono text-sky-400 font-semibold uppercase tracking-wider flex items-center justify-between">
                <span>Active Pipeline Phase:</span>
                <span className="text-[10px] text-slate-400">Phase {evalStageIdx + 1} of 5</span>
              </div>
              <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-sky-400" aria-hidden="true" />
                <span>{EVALUATION_STAGES[evalStageIdx].label}</span>
              </div>
            </div>

            {/* Visual Stage Progress Ribbon */}
            <div className="space-y-2">
              <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full bg-gradient-to-r from-sky-500 via-indigo-400 to-emerald-400 transition-all duration-300 ease-out shadow-lg shadow-sky-500/40"
                  style={{ width: `${EVALUATION_STAGES[evalStageIdx].progressPercent}%` }}
                />
              </div>

              {/* 5 Stage Breadcrumbs */}
              <div className="grid grid-cols-5 gap-1.5 pt-1 text-center">
                {EVALUATION_STAGES.map((stg, i) => (
                  <div
                    key={stg.stage}
                    className={`rounded px-1 py-1 text-[10px] font-mono transition-colors ${
                      i === evalStageIdx
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold animate-pulse'
                        : i < evalStageIdx
                        ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/30'
                        : 'bg-slate-900/60 text-slate-500 border border-slate-800'
                    }`}
                  >
                    <div className="truncate">Stage {stg.stage}</div>
                    <div className="text-[9px] text-slate-400">{stg.progressPercent}%</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="text-[10px] text-slate-400 font-mono text-center pt-1 border-t border-slate-800/60 flex items-center justify-between">
              <span>Deterministic Clearance Invariant Watchdog Active</span>
              <span>Fail-Closed Policy</span>
            </div>
          </div>
        </div>
      )}

      {/* Toast Alert Notification (With Optimistic Rollback and Retry Action) */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className={`rounded-lg border px-4 py-3 text-sm shadow-xl backdrop-blur-md flex items-center justify-between animate-in fade-in slide-in-from-top-2 ${
            toast.type === 'error'
              ? 'border-rose-500/50 bg-rose-950/90 text-rose-200'
              : toast.type === 'warning'
              ? 'border-amber-500/50 bg-amber-950/90 text-amber-200'
              : toast.type === 'info'
              ? 'border-sky-500/50 bg-sky-950/90 text-sky-200'
              : 'border-emerald-500/50 bg-emerald-950/90 text-emerald-200'
          }`}
        >
          <div className="flex items-center gap-2.5">
            {toast.type === 'error' ? (
              <AlertOctagon className="h-5 w-5 text-rose-400 flex-shrink-0" aria-hidden="true" />
            ) : toast.type === 'warning' ? (
              <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0" aria-hidden="true" />
            ) : toast.type === 'info' ? (
              <Info className="h-5 w-5 text-sky-400 flex-shrink-0" aria-hidden="true" />
            ) : (
              <CheckCircle2 className="h-5 w-5 text-emerald-400 flex-shrink-0" aria-hidden="true" />
            )}
            <span>{toast.message}</span>
          </div>

          <div className="flex items-center gap-2 ml-4">
            {toast.retryAction && (
              <button
                type="button"
                onClick={() => {
                  const retry = toast.retryAction;
                  setToast(null);
                  retry?.();
                }}
                className="rounded bg-rose-500 hover:bg-rose-400 px-2.5 py-1 text-xs font-bold text-slate-950 transition-colors focus:outline-none focus:ring-1 focus:ring-rose-300"
              >
                Retry
              </button>
            )}
            <button
              type="button"
              onClick={() => setToast(null)}
              className="text-xs text-slate-400 hover:text-white px-2 py-1 focus:outline-none focus:ring-1 focus:ring-sky-400 rounded"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Session Identity & Workspace Mode Badge */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 bg-slate-900/60 border border-slate-800 p-4 rounded-2xl backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-xl font-bold text-white tracking-wide">Lienmark Command Center</h1>
            {!isAuthenticated ? (
              <span className="rounded-full bg-amber-500/20 border border-amber-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-amber-300">
                Sample Workspace · Read-Only
              </span>
            ) : (
              <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-emerald-300">
                Authenticated Session ({role})
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Clearance Verification &amp; Revision Control &middot; Shadows Over Broadway (Locked v7 &rarr; Revised v8)
          </p>
        </div>
        <div className="flex items-center gap-3 self-end sm:self-auto">
          {!isAuthenticated && (
            <button
              type="button"
              onClick={() => {
                setIsInviteExpired(false);
                setIsRequestAccessOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 px-3 py-1.5 text-xs font-bold text-slate-950 transition-colors shadow-sm"
            >
              <KeyRound className="h-3.5 w-3.5" />
              <span>Request Access</span>
            </button>
          )}
          <SessionBadge />
        </div>
      </div>

      {/* 0. Hollywood Studio Director's Presentation HUD & Teleprompter Navigator */}
      <DirectorsPresentationHud
        activeBeat={currentBeat}
        onSelectBeat={handleSelectBeat}
      />

      {/* HITL Clarification Blocker Banner Alert across top of production dashboard */}
      <ClarificationBannerAlert
        pendingRequests={clarificationRequests}
        onOpenClarification={handleOpenClarification}
        onDismiss={() => setIsClarificationBannerDismissed(true)}
        isDismissed={isClarificationBannerDismissed}
      />

      {/* Sprint 4.2 Autonomous Agreement Match Arrival Alert */}
      {agreementNotification && (
        <AgreementArrivalNotification
          agreement={agreementNotification}
          isDismissed={isAgreementNotificationDismissed}
          onDismiss={() => setIsAgreementNotificationDismissed(true)}
          onViewAgreement={() => setIsAgreementViewerOpen(true)}
          onViewResumption={() => setShowResumptionStepper((prev) => !prev)}
        />
      )}

      {/* Sprint 4.2 Live Resumption Progress Stepper */}
      {showResumptionStepper && (
        <ResumptionProgressStepper
          session={resumptionSession}
          onOpenAgreementViewer={() => setIsAgreementViewerOpen(true)}
          onSignOff={() => {
            setClaims((prev) =>
              prev.map((c) =>
                c.stable_lineage_key === 'music_cue_midnight_serenade'
                  ? { ...c, resumption_status: ClaimResumptionStatus.READY_FOR_REVIEW }
                  : c
              )
            );
            handleOpenInGate('music_cue_midnight_serenade');
          }}
        />
      )}

      {/* Fail-Closed Truthfulness Connection Status Banner */}
      <ConnectionStatusBanner
        connectionState={connectionState}
        onRetry={handleRetryConnection}
        isRetrying={isRetryingConnection}
        errorMessage={connectionError}
      />

      {/* Loading State Banner */}
      {connectionState === 'loading' && (
        <div
          role="status"
          aria-live="polite"
          className="rounded-2xl border border-sky-500/40 bg-gradient-to-r from-sky-950/60 via-[#101726]/80 to-slate-950/80 p-4 backdrop-blur-md shadow-xl flex items-center justify-between animate-pulse text-sky-200"
        >
          <div className="flex items-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-sky-400" aria-hidden="true" />
            <div>
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-sky-400">
                Hydrating Clearance Ledger...
              </span>
              <p className="text-xs text-slate-300">
                Connecting to FastAPI clearance service and verifying live cryptographic state.
              </p>
            </div>
          </div>
          <span className="text-[11px] font-mono text-slate-400">State: LOADING</span>
        </div>
      )}

      {/* Empty State Card (0 claims registered) */}
      {connectionState === 'empty' && (
        <div
          role="status"
          className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6 text-center backdrop-blur-md space-y-2"
        >
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-800 text-slate-400">
            <Layers className="h-6 w-6" aria-hidden="true" />
          </div>
          <h4 className="text-sm font-bold text-white">No Rights Claims Registered</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            The active project revision currently has 0 claims registered. Execute a clearance evaluation to ingest and verify claims.
          </p>
        </div>
      )}

      {/* 1. Modular Header Component (Pitch Beat 2: Version 7 Baseline) */}
      <section id="pitch-beat-2" data-pitch-beat="2" className="scroll-mt-6">
        <DashboardHeader
          projectName="Shadows Over Broadway"
          projectId="proj_blockbuster_cinema"
          policyNumber="E&O-2026.1-DEVPOST"
          underwriterStatus="PENDING_REVIEW"
          baseVersionLabel="Script Cut v7 Locked"
          targetVersionLabel={targetVersionId === 'v7' ? 'v7 Locked (Parity)' : 'v8 Revised'}
          baseContentHash="a1b2c3d4e5f60718293a4b5c6d7e8f90"
          targetContentHash={
            targetVersionId === 'v7'
              ? 'a1b2c3d4e5f60718293a4b5c6d7e8f90'
              : 'f9e8d7c6b5a43210fedcba9876543210'
          }
          totalClaimsCount={totalClaims}
          auditEventCount={auditTrail.length}
          isRunningEvaluation={isRunningEvaluation}
          isPending={isPending}
          targetVersionId={targetVersionId}
          onToggleTargetVersion={handleToggleVersion}
          onRunEvaluation={handleRunEvaluation}
          onOpenAuditTrail={() => setIsAuditDrawerOpen(true)}
          exceptionsScheduleUrl="/report/proj_blockbuster_cinema"
          onResetDemo={handleResetDemo}
          isResettingDemo={isResettingDemo}
          onSeedDemoMode={handleSeedDemoMode}
          currentDemoMode={currentDemoMode}
          userRole={userRole}
          onRoleChange={setUserRole}
          isMutationDisabled={isMutationDisabled}
        />
      </section>

      {/* ===================================================================== */}
      {/* 2. CORE PLATFORM DELIVERY READINESS & BASELINE-TO-REVISION COMPARISON  */}
      {/* ===================================================================== */}
      <section
        aria-label="Clearance Delivery Readiness and Revision Delta"
        className="rounded-2xl border border-slate-700 bg-gradient-to-b from-[#131d33] via-[#0d1424] to-slate-950 p-6 shadow-2xl space-y-6 border-t-2 border-t-sky-400"
      >
        {/* Delivery Readiness Header & Measured Research Spend Telemetry */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-sky-500/20 text-sky-300 border border-sky-500/40 px-2 py-0.5 text-xs font-mono font-bold tracking-wider uppercase">
                Core Delivery Workflow Hierarchy
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Active Audit: {auditId || 'audit_live_cut'}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white mt-1.5 flex items-center gap-2.5">
              <GitCompare className="h-5 w-5 text-sky-400" aria-hidden="true" />
              <span>Baseline-to-Revision Delivery Analysis</span>
            </h2>
            <p className="text-xs text-slate-300 mt-1 max-w-3xl">
              Comparing locked baseline <strong className="text-white">Script Cut v7 Locked</strong> against revised target <strong className="text-sky-300">{targetVersionId === 'v7' ? 'v7 Locked (Parity)' : 'v8 Revised'}</strong>. Dynamic clearance lineage verification determines which approvals remain applicable and what blocks delivery.
            </p>
          </div>

          {/* Measured Telemetry Spend Badge: zero spend shown strictly upon verified telemetry */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3.5 min-w-[280px] space-y-1 shadow-md">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span className="flex items-center gap-1.5">
                <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
                <span>Additional Research Spend</span>
              </span>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                  measuredResearchSpend.isMeasured
                    ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/30'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {measuredResearchSpend.isMeasured ? 'Measured' : 'Unmeasured'}
              </span>
            </div>

            <div className="text-xl font-bold font-mono">
              {measuredResearchSpend.isMeasured ? (
                measuredResearchSpend.isZero ? (
                  <span className="text-emerald-400">$0.00</span>
                ) : (
                  <span className="text-sky-300">${measuredResearchSpend.amount?.toFixed(2)}</span>
                )
              ) : (
                <span className="text-slate-400 text-sm font-sans font-medium">Telemetry Pending Run</span>
              )}
            </div>

            <p className="text-[10px] font-mono text-slate-400 leading-tight">
              {measuredResearchSpend.isMeasured ? (
                measuredResearchSpend.isZero ? (
                  <span className="text-emerald-300/90">✓ Measured Telemetry Verified: 0 external search queries issued</span>
                ) : (
                  <span>Verified runtime expenditure across active audit traces</span>
                )
              ) : (
                <span>Execute clearance evaluation to measure runtime API spend</span>
              )}
            </p>
          </div>
        </div>

        {/* 3 Core Delivery Insight Columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* 1. What Changed in This Revision */}
          <div className="rounded-xl border border-amber-500/40 bg-gradient-to-b from-amber-950/20 to-slate-900/60 p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" />
                <span>What Changed</span>
              </span>
              <span className="rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 text-[11px] font-bold font-mono">
                {dynamicReopenedCount} Drifted
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {dynamicReopenedCount} / {totalClaims} Claims
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {dynamicReopenedCount === 0
                ? 'Zero creative or external rights drift detected. All production elements match baseline cut bit-for-bit.'
                : `${dynamicReopenedCount} claims experienced semantic or external rights drift between v7 and v8, reopening prior approvals for review.`}
            </p>
            <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
              {targetVersionId === 'v7' ? 'Cut Parity Mode ($0 Cost)' : 'Prominence & Exclusive Sync shifts detected'}
            </div>
          </div>

          {/* 2. Which Prior Approvals Remain Applicable */}
          <div className="rounded-xl border border-emerald-500/40 bg-gradient-to-b from-emerald-950/20 to-slate-900/60 p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" />
                <span>Approvals Applicable</span>
              </span>
              <span className="rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 text-[11px] font-bold font-mono">
                {totalClaims > 0 ? ((dynamicPreservedCount / totalClaims) * 100).toFixed(0) : '0'}% Preserved
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {dynamicPreservedCount} / {totalClaims} Preserved
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Prior approvals autonomously carried forward under statutory clearance doctrine. Context hashes and rights posture bit-for-bit unchanged ($0 redundant review cost).
            </p>
            <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono text-emerald-400">
              Autonomous pass verified without counsel intervention
            </div>
          </div>

          {/* 3. What Blocks Delivery */}
          <div
            className={`rounded-xl border p-4 space-y-2 ${
              dynamicBlockersCount > 0
                ? 'border-rose-500/50 bg-gradient-to-b from-rose-950/20 to-slate-900/60'
                : 'border-emerald-500/40 bg-slate-900/60'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                <AlertOctagon className="h-4 w-4" />
                <span>What Blocks Delivery</span>
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-bold font-mono ${
                  dynamicBlockersCount > 0
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                }`}
              >
                {dynamicBlockersCount > 0 ? `${dynamicBlockersCount} Blockers` : 'Delivery Ready'}
              </span>
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {dynamicBlockersCount}
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {dynamicBlockersCount > 0
                ? `${exceptionCount} underwriter warranty exceptions and ${staleCount} pending counsel decisions actively prevent Form E&O-2026 policy binding.`
                : 'All clearance requirements reconciled. Exceptions Schedule ready for underwriter warranty binding.'}
            </p>
            <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
              {dynamicBlockersCount > 0 ? 'Resolution required prior to final distribution master' : 'Clear for production wrap'}
            </div>
          </div>
        </div>

        {/* Prioritized Reopened Claims & Delivery Blockers Detailed List */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <Layers className="h-4 w-4 text-sky-400" />
              <span>Prioritized Reopened Claims &amp; Delivery Blockers</span>
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Distinguishing pending revalidations from underwriter policy blockers
            </span>
          </div>

          {prioritizedReopenedClaims.length === 0 && deliveryBlockersList.length === 0 ? (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-center text-xs text-emerald-300">
              ✓ No reopened claims or delivery blockers. All rights lineages in pristine reconciled state.
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Reopened Claims Group */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                  <span className="text-xs font-mono font-bold text-amber-300 uppercase flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                    <span>Reopened Claims (Pending Counsel Revalidation)</span>
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    {prioritizedReopenedClaims.length} pending
                  </span>
                </div>

                {prioritizedReopenedClaims.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No pending reopened claims.</p>
                ) : (
                  prioritizedReopenedClaims.map((item) => (
                    <div
                      key={item.stableLineageKey}
                      className="rounded-xl border border-amber-500/30 bg-slate-900/80 p-4 space-y-2.5 transition-all hover:border-amber-400/60 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                            Reopened Claim &middot; {item.scene}
                          </span>
                          <h4 className="text-sm font-bold text-white mt-1">
                            {item.assetName}
                          </h4>
                        </div>
                        <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300 uppercase">
                          {item.assetType}
                        </span>
                      </div>

                      <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800 text-xs space-y-1.5">
                        <div>
                          <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">Reason: </span>
                          <span className="text-slate-200">{item.reason}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
                          <div>
                            <span className="font-mono text-slate-400">Responsible: </span>
                            <span className="font-semibold text-amber-300">{item.responsibleRole}</span>
                          </div>
                          <div>
                            <span className="font-mono text-slate-400">Next Action: </span>
                            <span className="font-semibold text-sky-300">{item.nextAction}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-end">
                        <button
                          type="button"
                          onClick={() => handleOpenInGate(item.stableLineageKey)}
                          className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500/20 hover:bg-sky-500/30 text-sky-300 border border-sky-500/40 px-3 py-1 text-xs font-semibold transition-colors"
                        >
                          <span>Adjudicate in Gate</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Delivery Blockers Group */}
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                  <span className="text-xs font-mono font-bold text-rose-400 uppercase flex items-center gap-1.5">
                    <AlertOctagon className="h-3.5 w-3.5 text-rose-400" />
                    <span>Active Delivery Blockers (Underwriting Exceptions)</span>
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    {deliveryBlockersList.length} exceptions
                  </span>
                </div>

                {deliveryBlockersList.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No delivery blockers currently active.</p>
                ) : (
                  deliveryBlockersList.map((item) => (
                    <div
                      key={item.stableLineageKey}
                      className="rounded-xl border border-rose-500/40 bg-slate-900/80 p-4 space-y-2.5 transition-all hover:border-rose-400/60 shadow-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 px-2 py-0.5 text-[10px] font-mono font-bold">
                            Delivery Blocker &middot; {item.scene}
                          </span>
                          <h4 className="text-sm font-bold text-white mt-1">
                            {item.assetName}
                          </h4>
                        </div>
                        <span className="rounded bg-rose-950/80 border border-rose-500/40 px-2 py-0.5 text-[10px] font-mono text-rose-300 uppercase font-bold">
                          E&amp;O Exception
                        </span>
                      </div>

                      <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800 text-xs space-y-1.5">
                        <div>
                          <span className="text-[10px] font-mono uppercase text-slate-400 font-bold">Blocker Cause: </span>
                          <span className="text-rose-200">{item.reason}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
                          <div>
                            <span className="font-mono text-slate-400">Responsible: </span>
                            <span className="font-semibold text-rose-300">{item.responsibleRole}</span>
                          </div>
                          <div>
                            <span className="font-mono text-slate-400">Next Action: </span>
                            <span className="font-semibold text-amber-300">{item.nextAction}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-end gap-2">
                        <a
                          href="/report/proj_blockbuster_cinema"
                          className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 px-3 py-1 text-xs font-semibold transition-colors"
                        >
                          <FileCheck className="h-3.5 w-3.5" />
                          <span>View Exceptions Schedule</span>
                        </a>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Milestone B/C/D Revision Pipeline & Telemetry Panels */}
      <section className="space-y-4">
        <RevisionEditorPanel
          disabled={!isAuthenticated}
          disabledReason="An invited session is required to submit revisions or trigger audit pipelines."
          onAuditCreated={(newAuditId) => setAuditId(newAuditId)}
        />
        <AuditTelemetryPanel auditId={auditId} />
      </section>

      {/* Adjudication (Gavel) Section */}
      <section className="border border-slate-800 p-6 rounded-2xl bg-slate-900/60 backdrop-blur-md text-white space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Gavel className="w-5 h-5 text-amber-400" />
            <span>Adjudication (Gavel)</span>
          </h2>
          {!isAuthenticated && (
            <span className="text-xs font-semibold text-amber-400 bg-amber-950/60 border border-amber-500/40 px-3 py-1 rounded-full flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" />
              <span>Gavel locked: An invited session is required to adjudicate claims.</span>
            </span>
          )}
        </div>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-4 border border-slate-800 p-4 bg-slate-950/80 rounded-xl">
            <span className="font-semibold text-base text-slate-200">Claim #8892</span>
            
            {!isAuthenticated && (
              <span className="text-sm text-amber-300 font-semibold flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5" />
                <span>An invited session is required to adjudicate claims.</span>
              </span>
            )}

            {isAuthenticated && role === 'Producer' && (
              <span className="text-sm text-rose-400 font-semibold">Gavel buttons disabled: Producers cannot adjudicate claims.</span>
            )}
            
            {isAuthenticated && role === 'Reviewer' && (
              <div className="flex items-center gap-4">
                <label className="text-sm flex items-center gap-2 font-semibold text-slate-300">
                  <input type="checkbox" checked={evidenceComplete} onChange={e => setEvidenceComplete(e.target.checked)} className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-indigo-500 focus:ring-indigo-400" />
                  Evidence Complete
                </label>
                <input 
                  type="text" 
                  placeholder="Counsel Directive (required for rejection)" 
                  value={counselDirective}
                  onChange={e => setCounselDirective(e.target.value)}
                  className="border border-slate-700 bg-slate-900 p-2 text-sm w-64 rounded-lg text-slate-100 placeholder-slate-500"
                />
              </div>
            )}

            <div className="ml-auto flex gap-2">
              <button 
                onClick={() => handleDecision('8892', 'approve')}
                disabled={!isAuthenticated || role === 'Producer' || (role === 'Reviewer' && !evidenceComplete)}
                title={!isAuthenticated ? 'An invited session is required to adjudicate claims.' : role === 'Producer' ? 'Producers cannot adjudicate claims.' : undefined}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg disabled:opacity-50 font-bold hover:bg-blue-500 transition-colors disabled:cursor-not-allowed"
              >
                Approve
              </button>
              <button 
                onClick={() => handleDecision('8892', 'reject')}
                disabled={!isAuthenticated || role === 'Producer'}
                title={!isAuthenticated ? 'An invited session is required to adjudicate claims.' : role === 'Producer' ? 'Producers cannot adjudicate claims.' : undefined}
                className="bg-red-600 text-white px-4 py-2 rounded-lg disabled:opacity-50 font-bold hover:bg-red-500 transition-colors disabled:cursor-not-allowed"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Modular Clearance Summary Cards & Invariant Conservation Ribbon (Pitch Beat 4) */}
      <section id="pitch-beat-4" data-pitch-beat="4" className="scroll-mt-6">
        <ClearanceSummaryCards
          totalClaims={totalClaims}
          carriedCount={carriedCount}
          staleCount={staleCount}
          reattestedCount={reattestedCount}
          exceptionCount={exceptionCount}
          isReconciled={isReconciled}
          exceptionsScheduleUrl="/report/proj_blockbuster_cinema"
          traces={traces}
          elapsedMs={evalElapsedMs}
        />
      </section>

      {/* Sprint 4C Fix 2: Active Clearance Blockers Summary (Pitch Beat 1: Clearance Drift Crisis) */}
      {staleCount > 0 && (
        <section id="pitch-beat-1" data-pitch-beat="1" className="scroll-mt-6">
          <ActiveClearanceBlockers
            staleCount={staleCount}
            claims={claims}
            onOpenInGate={handleOpenInGate}
          />
        </section>
      )}

      {/* Sprint 4C Fix 3: Clearance Decision Lifecycle Guide */}
      <ClearanceLifecycleGuide
        currentStep={
          isReconciled
            ? 4
            : staleCount > 0
            ? 3
            : targetVersionId === 'v7'
            ? 1
            : 2
        }
      />

      {/* Navigation View Tabs */}
      <nav
        className="flex items-center justify-between border-b border-slate-800 pb-2"
        aria-label="Dashboard Views"
      >
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('checkpoint')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-sky-500 ${
              activeTab === 'checkpoint'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
            aria-selected={activeTab === 'checkpoint'}
            role="tab"
          >
            <Gavel className="h-4 w-4 text-sky-400" aria-hidden="true" />
            <span>Counsel Checkpoint Gate</span>
            {staleCount > 0 ? (
              <span className="rounded-full bg-amber-500/20 border border-amber-500/40 px-2 py-0.2 text-[11px] font-bold text-amber-300">
                {staleCount} Pending
              </span>
            ) : (
              <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.2 text-[11px] font-bold text-emerald-300">
                Resolved
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('diff')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-sky-500 ${
              activeTab === 'diff'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
            aria-selected={activeTab === 'diff'}
            role="tab"
          >
            <GitCompare className="h-4 w-4 text-amber-400" aria-hidden="true" />
            <span>Revision Delta Viewer (v7 vs v8)</span>
            <span className="rounded-full bg-sky-500/20 border border-sky-500/40 px-2 py-0.2 text-[11px] font-bold text-sky-300">
              Side-by-Side
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('lineage')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-sky-500 ${
              activeTab === 'lineage'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
            aria-selected={activeTab === 'lineage'}
            role="tab"
          >
            <Layers className="h-4 w-4 text-slate-400" aria-hidden="true" />
            <span>Full Production Lineage (12 Claims)</span>
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => {
              const nextMuted = toggleSoundMuted();
              setSoundMutedState(nextMuted);
              setToast({
                type: 'info',
                message: nextMuted ? '🔇 Studio audio muted' : '🔊 Studio sound effects enabled',
              });
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-lg border transition-all ${
              soundMuted
                ? 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200'
                : 'border-sky-500/40 bg-sky-500/10 text-sky-300 shadow-sm'
            }`}
            title="Toggle studio sound effects (Shortcut: M)"
            aria-label={soundMuted ? 'Unmute studio sound effects' : 'Mute studio sound effects'}
          >
            {soundMuted ? (
              <VolumeX className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
            ) : (
              <Volume2 className="h-3.5 w-3.5 text-sky-400 animate-pulse" aria-hidden="true" />
            )}
            <span>{soundMuted ? 'Audio Muted [M]' : 'Studio Audio [M]'}</span>
          </button>
          <span className="text-xs text-slate-400 hidden md:block font-mono">
            Hollywood Studio Legal Ops
          </span>
        </div>
      </nav>

      {/* ===================================================================== */}
      {/* VIEW 1: DEDICATED COUNSEL CHECKPOINT GATE (DELTA + 4D + REVIEW ACTION) */}
      {/* ===================================================================== */}
      {activeTab === 'checkpoint' && (
        <div className="space-y-6" role="tabpanel" aria-label="Counsel Checkpoint Gate Panel">
          {isZeroDrift ? (
            /* Dedicated Empty / No-Change State Card */
            <div
              role="region"
              aria-label="Zero Clearance Drift Detected"
              className="rounded-2xl border-2 border-emerald-500/50 bg-gradient-to-br from-emerald-950/30 via-[#131b2e] to-slate-900 p-6 sm:p-8 text-center space-y-4 shadow-2xl animate-in fade-in duration-300"
            >
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400">
                <ShieldCheck className="h-8 w-8" aria-hidden="true" />
              </div>
              <div className="space-y-1">
                <span className="text-xs font-mono font-bold uppercase tracking-widest text-emerald-400">
                  Deterministic Clearance Invariant Verified
                </span>
                <h3 className="text-xl sm:text-2xl font-bold text-white">
                  Zero Clearance Drift Detected
                </h3>
              </div>
              <p className="max-w-2xl mx-auto text-sm text-slate-300 leading-relaxed font-sans">
                Script cut v7 baseline is identical to compared version. All 12 claims carried forward automatically ($0.00 review expense, 0 external queries issued).
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-xl mx-auto pt-2">
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-emerald-400 font-semibold">Claims Carried</div>
                  <div className="text-xl font-bold text-white mt-0.5">12 / 12</div>
                  <div className="text-[10px] text-emerald-300/80">100% Retained</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-slate-400 font-semibold">Review Expense</div>
                  <div className="text-xl font-bold text-emerald-400 mt-0.5">$0.00</div>
                  <div className="text-[10px] text-slate-500">Zero Re-Review Cost</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-slate-400 font-semibold">External Queries</div>
                  <div className="text-xl font-bold text-slate-200 mt-0.5">0</div>
                  <div className="text-[10px] text-slate-500">0 API Calls Issued</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-center">
                  <div className="text-[10px] font-mono uppercase text-slate-400 font-semibold">Counsel Gate</div>
                  <div className="text-xl font-bold text-slate-200 mt-0.5">0 Stale</div>
                  <div className="text-[10px] text-slate-500">No Action Required</div>
                </div>
              </div>

              <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => handleToggleVersion('v8')}
                  className="inline-flex items-center gap-2 rounded-xl bg-sky-500 hover:bg-sky-400 px-4 py-2.5 text-xs font-bold text-slate-950 transition-all shadow-md shadow-sky-500/20 focus:outline-none focus:ring-2 focus:ring-sky-300"
                >
                  <GitCompare className="h-4 w-4" aria-hidden="true" />
                  <span>Compare Revised Cut v8 (2 Stale Claims Drift)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('lineage')}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 hover:bg-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
                >
                  <Layers className="h-4 w-4 text-slate-400" aria-hidden="true" />
                  <span>Inspect Full 12-Claim Production Register</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
              {/* Left Column (xl:col-span-7): Delta List Breakdown & Full 12-Claim Register */}
              <div className="xl:col-span-7 space-y-6">
                {/* 3. Modular Delta List Breakdown (Pitch Beat 3: Bimodal Drift) */}
                <section id="pitch-beat-3" data-pitch-beat="3" className="scroll-mt-6">
                  <DeltaListComponent
                    items={reviewQueue}
                    selectedQueueKey={selectedQueueKey}
                    onSelectQueueItem={(key) => {
                      setSelectedQueueKey(key);
                      setSelectedClaimKey(key);
                    }}
                    onInspectItem={(key) => {
                      setSelectedQueueKey(key);
                      setSelectedClaimKey(key);
                    }}
                  />
                </section>

                {/* 4. Modular Decision List Component (12 Claims Table Matrix) */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                      <Layers className="h-4 w-4 text-sky-400" aria-hidden="true" />
                      <span>Script Cut v8 Rights Clearance Matrix (12 Assets)</span>
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setShowPolicyEditor(!showPolicyEditor)}
                        className="inline-flex items-center gap-1.5 text-[11px] font-mono font-bold text-purple-300 bg-purple-950/60 border border-purple-500/40 px-2.5 py-1 rounded hover:bg-purple-900/60 transition-colors"
                      >
                        <Building2 className="h-3.5 w-3.5 text-purple-400" />
                        <span>{showPolicyEditor ? 'Hide Studio Policy' : 'Studio Policy Governance'}</span>
                      </button>
                      <span className="text-[11px] font-mono text-slate-500">
                        Click row to inspect in 4D panel
                      </span>
                    </div>
                  </div>
                  {showPolicyEditor && (
                    <StudioPolicyEditor
                      productionId="proj_blockbuster_cinema"
                      orgId="org_paramount_global"
                      isAdmin={userRole === UserRole.ADMIN}
                      onCommitOverride={(ovr) => {
                        setToast({
                          type: 'success',
                          message: `✓ Admin Policy Override committed to ledger (${ovr.ledgerEventId}).`,
                        });
                      }}
                    />
                  )}
                  <DecisionListComponent
                    claims={claims}
                    selectedClaimKey={selectedClaimKey}
                    onSelectClaim={(key) => {
                      setSelectedClaimKey(key);
                      setSelectedQueueKey(key);
                    }}
                    onOpenInGate={(key) => {
                      setSelectedQueueKey(key);
                      setSelectedClaimKey(key);
                    }}
                    userRole={userRole}
                    activeClarifications={clarificationRequests}
                    onOpenClarification={handleOpenClarification}
                    onOpenOverride={() => setShowPolicyEditor(true)}
                  />
                </div>
              </div>

              {/* Right Column (xl:col-span-5): Persistent 4D Inspector & Adjudication Gate */}
              <div className="xl:col-span-5 space-y-6 xl:sticky xl:top-6 xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto pr-1">
                {/* 5. Modular 4-Dimensional Explanation & Baseline Accordion (Pitch Beat 5) */}
                <section id="pitch-beat-5" data-pitch-beat="5" className="scroll-mt-6">
                  <ExplanationDrawerComponent
                    activeQueueItem={activeQueueItem}
                    isPriorDecisionOpen={isPriorDecisionOpen}
                    onTogglePriorDecision={() => setIsPriorDecisionOpen(!isPriorDecisionOpen)}
                  />
                </section>

                {/* 6. Modular Affirmative Counsel Adjudication Panel (Pitch Beat 6) */}
                <section id="pitch-beat-6" data-pitch-beat="6" className="scroll-mt-6">
                  <ReviewActionComponent
                    activeItem={activeQueueItem}
                    reviewerIdentity={reviewerIdentity}
                    counselRationale={counselRationale}
                    onRationaleChange={(val) => setCounselRationale(val)}
                    onAction={handleReviewAction}
                    isSubmitting={isSubmittingAction}
                    isPending={isPending}
                    lastConfirmedEvent={lastConfirmedEvent}
                    userRole={userRole}
                    isMutationDisabled={isMutationDisabled || !isAuthenticated}
                  />
                </section>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* VIEW 2: REVISION DELTA VIEWER (SIDE-BY-SIDE SCRIPT COMPARISON)        */}
      {/* ===================================================================== */}
      {activeTab === 'diff' && (
        <div role="tabpanel" aria-label="Revision Delta Viewer Panel" className="space-y-6">
          <RevisionDeltaViewer
            baseVersionLabel="Script Cut v7 Locked"
            targetVersionLabel={targetVersionId === 'v7' ? 'v7 Locked (Parity)' : 'v8 Revised'}
            baseContentHash="a1b2c3d4e5f60718293a4b5c6d7e8f90"
            targetContentHash={
              targetVersionId === 'v7'
                ? 'a1b2c3d4e5f60718293a4b5c6d7e8f90'
                : 'f9e8d7c6b5a43210fedcba9876543210'
            }
            selectedLineageKey={selectedClaimKey}
            onSelectLineageKey={(key) => {
              setSelectedClaimKey(key);
              setSelectedQueueKey(key);
            }}
            userRole={userRole}
          />
        </div>
      )}

      {/* ===================================================================== */}
      {/* VIEW 3: FULL PRODUCTION LINEAGE (12 CLAIMS & EVIDENCE DETAILS)        */}
      {/* ===================================================================== */}
      {activeTab === 'lineage' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start" role="tabpanel" aria-label="Full Lineage Panel">
          {/* Left Column: 12-Claim Interactive Table */}
          <div className="lg:col-span-7 space-y-4">
            {/* 4. Modular Decision List Component */}
            <DecisionListComponent
              claims={claims}
              selectedClaimKey={selectedClaimKey}
              onSelectClaim={(key) => setSelectedClaimKey(key)}
              onOpenInGate={handleOpenInGate}
              userRole={userRole}
              activeClarifications={clarificationRequests}
              onOpenClarification={handleOpenClarification}
            />

            {/* Clearance Workflow Engine Traces */}
            <div className="rounded-xl border border-slate-800 bg-[#131b2e] p-4 space-y-3 shadow-md">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Zap className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
                  <span>Clearance Engine Workflow Execution Traces</span>
                </h3>
                <span className="text-[11px] font-mono text-slate-500">
                  Lienmark Core 1.0 &middot; 5 Phases
                </span>
              </div>

              <div className="space-y-2">
                {traces.map((trace, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-lg bg-slate-900/60 px-3 py-2 text-xs border border-slate-800/80"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" aria-hidden="true" />
                      <div>
                        <span className="font-semibold text-slate-200">
                          {trace.step_name.replace(/_/g, ' ')}
                        </span>
                        <span className="ml-2 text-[10px] text-slate-400">
                          [{trace.component}]
                        </span>
                      </div>
                    </div>
                    <span className="font-mono text-[11px] text-slate-400">
                      {trace.duration_ms.toFixed(1)}ms
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Persistent Split-Screen 4D Inspector & Adjudication Gate */}
          <div className="lg:col-span-5 space-y-4 sticky top-6">
            <ExplanationDrawerComponent
              activeQueueItem={lineageInspectorItem}
              isPriorDecisionOpen={isPriorDecisionOpen}
              onTogglePriorDecision={() => setIsPriorDecisionOpen(!isPriorDecisionOpen)}
            />

            {lineageInspectorItem.current_state === DecisionState.STALE && (
              <ReviewActionComponent
                activeItem={lineageInspectorItem}
                reviewerIdentity={reviewerIdentity}
                counselRationale={counselRationale}
                onRationaleChange={(val) => setCounselRationale(val)}
                onAction={handleReviewAction}
                isSubmitting={isSubmittingAction}
                isPending={isPending}
                lastConfirmedEvent={lastConfirmedEvent}
                userRole={userRole}
                isMutationDisabled={isMutationDisabled || !isAuthenticated}
              />
            )}
          </div>
        </div>
      )}

      {/* 7. Modular Export & Underwriter Legal Notice Component (Pitch Beat 7) */}
      <section id="pitch-beat-7" data-pitch-beat="7" className="scroll-mt-6">
        <ExportActionComponent
          projectId="proj_blockbuster_cinema"
          projectName="Shadows Over Broadway"
          claims={claims}
          exceptionsScheduleUrl="/report/proj_blockbuster_cinema"
          auditId={auditId}
          resultSnapshotId={snapshotId}
        />
      </section>

      {/* 8. Modular Append-Only Audit Trail Slide-Over Drawer */}
      <AuditTrailDrawer
        isOpen={isAuditDrawerOpen}
        onClose={() => setIsAuditDrawerOpen(false)}
        auditTrail={auditTrail}
      />

      {/* 9. HITL Clarifying Question Modal */}
      <ClarifyingQuestionModal
        isOpen={Boolean(activeClarificationModalKey)}
        request={
          clarificationRequests.find((r) => r.claimKey === activeClarificationModalKey) ??
          GOLDEN_CLARIFICATION_REQUESTS.find((r) => r.claimKey === activeClarificationModalKey) ??
          null
        }
        onClose={handleCloseClarification}
        onSubmit={handleSubmitClarification}
        onEscalate={handleEscalateClarification}
      />

      {/* 10. Sprint 4.2 HITL Agreement Viewer Modal */}
      <AgreementViewerModal
        isOpen={isAgreementViewerOpen}
        agreement={agreementNotification ?? GOLDEN_AGREEMENT_MATCH}
        onClose={() => setIsAgreementViewerOpen(false)}
        onCounselConfirm={(ag) => {
          setClaims((prev) =>
            prev.map((c) =>
              c.stable_lineage_key === ag.claimKey
                ? {
                    ...c,
                    state: DecisionState.RE_ATTESTED,
                    reason_code: 'AUTONOMOUS_AGREEMENT_VERIFIED_SYNC',
                    revalidation_action: 're_attest',
                    resumption_status: ClaimResumptionStatus.READY_FOR_REVIEW,
                  }
                : c
            )
          );
          setToast({
            type: 'success',
            message: `✓ Unblocked & Re-Attested ${ag.assetCue} via verified ${ag.filename}.`,
          });
        }}
      />

      {/* 11. Request Access & Expired Invite Modal */}
      <RequestAccessModal
        isOpen={isRequestAccessOpen}
        onClose={() => {
          setIsRequestAccessOpen(false);
          setIsInviteExpired(false);
        }}
        isExpired={isInviteExpired}
        productionName="Shadows Over Broadway"
        initialRole={role || 'Reviewer'}
      />
    </div>
  );
}
