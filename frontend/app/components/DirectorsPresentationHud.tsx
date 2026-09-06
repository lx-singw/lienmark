'use client';

/**
 * Lienmark Director's Presentation HUD & Master Teleprompter Guide
 * Component 2 of Hollywood Studio Legal Ops UI/UX Overhaul
 *
 * Maps directly to the 7 video beats in docs/pitch_script.md:
 *  1. 0:00–0:15: Beat 1 — Problem Exposition & Clearance Drift Crisis ($18k fee, 3-week studio hold)
 *  2. 0:15–0:35: Beat 2 — Version 7 Baseline Complete (12 Approved Claims under Policy E&O-2026.1-DEVPOST)
 *  3. 0:35–1:05: Beat 3 — Version 8 Ingestion & Bimodal Drift (Item 11 poster, Item 12 jazz cue)
 *  4. 1:05–1:25: Beat 4 — Mathematical Conservation & Parity (12 = 10 + 1 + 1 holding 12 -> 10/2 -> 1/1)
 *  5. 1:25–1:55: Beat 5 — Targeted Parallel Search Dispatched (83.3% query reduction, 142ms latency)
 *  6. 1:55–2:25: Beat 6 — Human Counsel Checkpoint (Sarah Jenkins Re-Attest/Reject)
 *  7. 2:25–2:45: Beat 7 — Form E&O-2026 Underwriting Schedule Export (SSR Printable Binder)
 *
 * Strictly Non-Mutating Navigation:
 *  - Clicking any beat or using keyboard shortcuts (1-7) calls onSelectBeat(beatId)
 *  - Scrolls to and spotlights relevant UI section without mutating backend state
 *  - Displays presenter teleprompter prompts with stress words and timing guidance
 *  - Includes persistent collapsible toggle (ChevronUp / ChevronDown)
 *
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Link from 'next/link';
import {
  Clapperboard,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  Play,
  Layers,
  Sparkles,
  Zap,
  Search,
  Gavel,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Copy,
  Check,
  Volume2,
  Lock,
  Compass,
  FileSpreadsheet,
} from 'lucide-react';

export interface DirectorsPresentationHudProps {
  activeBeat?: number; // 1-7
  onSelectBeat?: (beatId: number) => void;
  className?: string;
}

export interface PitchBeatData {
  id: number;
  timecode: string;
  durationSeconds: number;
  title: string;
  shortTitle: string;
  subtitle: string;
  badgeText: string;
  vocalTone: string;
  targetSectionId: string;
  targetSectionName: string;
  actionCue: string;
  teleprompterScript: string;
  stressWords: string[];
  keyMetrics: { label: string; value: string }[];
  codePointers: { label: string; file: string; lineRef?: string }[];
  invariantGuarantee: string;
  accentColor: {
    border: string;
    bg: string;
    text: string;
    badge: string;
    glow: string;
  };
}

export const PITCH_BEATS: PitchBeatData[] = [
  {
    id: 1,
    timecode: '0:00–0:15',
    durationSeconds: 15,
    title: 'Beat 1: Problem Exposition & Clearance Drift Crisis',
    shortTitle: 'Clearance Drift Crisis',
    subtitle: '$18k fee, 3-week studio hold',
    badgeText: '$18k Hold · Crisis',
    vocalTone: 'Measured, serious, exposing industry crisis',
    targetSectionId: 'pitch-beat-1',
    targetSectionName: 'Problem Exposition & Active Clearance Blockers',
    actionCue: '[CUT TO TITLE CARD & BINDER SPLIT SCREEN] ... [GRAPHIC OVERLAY: $18K FEE & 3-WEEK STUDIO HOLD]',
    teleprompterScript:
      "In film production, the hardest problem in rights clearance isn't finding a copyright record once. It’s knowing whether yesterday’s legal sign-off still protects today’s evolving cut and changing external evidence. [PAUSE 1.0s]\n\nThat silent divergence is **clearance drift**. Rescanning an entire binder across every revision wastes **eighteen thousand dollars** and delays studio delivery by **three weeks**. Unmonitored drift risks catastrophic E&O warranty claims.",
    stressWords: [
      'clearance drift',
      'eighteen thousand dollars',
      'three weeks',
      'catastrophic E&O warranty claims',
    ],
    keyMetrics: [
      { label: 'Review Fee Waste', value: '$18,000 / revision' },
      { label: 'Delivery Delay', value: '3-Week Studio Hold' },
      { label: 'Risk Factor', value: 'Silent Warranty Invalidation' },
    ],
    codePointers: [
      { label: 'Problem Statement', file: 'README.md', lineRef: 'L50-L55' },
      { label: 'Economic Model', file: 'docs/pitch_script.md', lineRef: 'Beat 1' },
    ],
    invariantGuarantee:
      'Invariant 1A & 1B: Clearance drift problem exposition & quantitative economic baseline ($18,000 legal reclearance expense, 3-week hold).',
    accentColor: {
      border: 'border-rose-500/50',
      bg: 'bg-rose-950/20',
      text: 'text-rose-400',
      badge: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
      glow: 'shadow-rose-500/20',
    },
  },
  {
    id: 2,
    timecode: '0:15–0:35',
    durationSeconds: 20,
    title: 'Beat 2: Version 7 Baseline Complete',
    shortTitle: 'Version 7 Baseline',
    subtitle: '12 Approved Claims under Policy E&O-2026.1-DEVPOST',
    badgeText: '12 Claims · Policy Locked',
    vocalTone: 'Grounded, reassuring, establishing certainty',
    targetSectionId: 'pitch-beat-2',
    targetSectionName: 'Dashboard Header & Golden Baseline Register',
    actionCue: '[CUT TO LIVE DASHBOARD: SCRIPT V7 BASELINE VIA FRONTEND/APP/PAGE.TSX] ... [SLOW PAN OVER 12 GREEN APPROVED ROWS]',
    teleprompterScript:
      'Here is our baseline: *Shadows Over Broadway*, Script Cut Version 7. Production counsel **Sarah Jenkins, Esq.** reviewed and approved **twelve** distinct rights-bearing assets under Policy **E&O-2026.1-DEVPOST**. [PAUSE 1.0s]\n\nEvery decision is bound to its exact scene context, duration, private agreements, and external evidence snapshots. In Version 7, the clearance file is **one hundred percent complete** and fully verified.',
    stressWords: [
      'Sarah Jenkins, Esq.',
      'twelve',
      'E&O-2026.1-DEVPOST',
      'one hundred percent complete',
    ],
    keyMetrics: [
      { label: 'Approved Claims', value: '12 of 12 (100%)' },
      { label: 'Policy Standard', value: 'E&O-2026.1-DEVPOST' },
      { label: 'Locked Hash', value: 'a1b2c3d4... (V7)' },
    ],
    codePointers: [
      { label: 'V7 Golden Baseline', file: 'backend/fixtures/golden_dataset.py', lineRef: 'L24' },
      { label: 'Statutory Policy Version', file: 'backend/core/invalidation_engine.py', lineRef: 'L48' },
    ],
    invariantGuarantee:
      'Invariant 2A & 2B: Locked baseline fixture validation & full 12-decision baseline approval under Policy E&O-2026.1-DEVPOST.',
    accentColor: {
      border: 'border-emerald-500/50',
      bg: 'bg-emerald-950/20',
      text: 'text-emerald-400',
      badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
      glow: 'shadow-emerald-500/20',
    },
  },
  {
    id: 3,
    timecode: '0:35–1:05',
    durationSeconds: 30,
    title: 'Beat 3: Version 8 Ingestion & Bimodal Drift',
    shortTitle: 'Bimodal Drift Detected',
    subtitle: 'Item 11 poster, Item 12 jazz cue',
    badgeText: '2 Drift Modes · Items 11 & 12',
    vocalTone: 'Dynamic, focused, revealing dual drift modes',
    targetSectionId: 'pitch-beat-3',
    targetSectionName: 'Delta List Breakdown & 4D Invalidation Inspector',
    actionCue: '[CLICK: "⚡ INGEST V8 & DETECT DRIFT"] ... [EXPAND DRAWER: ITEM 11 NOIR POSTER] ... [DRAWER ADVANCES: ITEM 12 JAZZ CUE]',
    teleprompterScript:
      "Now, production delivers Version 8. A traditional tool either rescans everything or goes blind. Lienmark's **Gemini 2.5 Flash** semantic delta engine instantly ingests the new cut and isolates **two** distinct drift modalities. [PAUSE 1.0s]\n\nFirst: **creative drift**. In Scene 42, the director zoomed in on this 1946 *Crime Detective* magazine poster (`poster_noir_detective_magazine`). It went from a two-second background blur into a **fourteen-second focal shot with dialogue**, collapsing the prior de minimis fair use defense. [PAUSE 1.0s]\n\nSecond: **external evidence drift**. For the Scene 18 jazz cue *Midnight Serenade* (`music_cue_midnight_serenade`), the script did not change by a single word. But out in the real world, music copyright registries updated, creating an adverse ownership dispute with Vanguard Media.",
    stressWords: [
      'Gemini 2.5 Flash',
      'two',
      'creative drift',
      'fourteen-second focal shot with dialogue',
      'external evidence drift',
    ],
    keyMetrics: [
      { label: 'Creative Drift (Item 11)', value: '2s blur -> 14s focal' },
      { label: 'External Drift (Item 12)', value: 'ASCAP Adverse Dispute' },
      { label: 'Delta Engine', value: 'Gemini 2.5 Flash' },
    ],
    codePointers: [
      { label: 'Semantic Delta Engine', file: 'backend/core/semantic_delta.py', lineRef: 'L65' },
      { label: 'Golden Fixtures', file: 'backend/fixtures/golden_dataset.py', lineRef: 'L209-L342' },
    ],
    invariantGuarantee:
      'Invariant 3A, 3B & 3C: Version parent binding (v8.parent == v7), creative context alteration, and external registry divergence.',
    accentColor: {
      border: 'border-amber-500/50',
      bg: 'bg-amber-950/20',
      text: 'text-amber-400',
      badge: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
      glow: 'shadow-amber-500/20',
    },
  },
  {
    id: 4,
    timecode: '1:05–1:25',
    durationSeconds: 20,
    title: 'Beat 4: Mathematical Conservation & Parity',
    shortTitle: 'Conservation & Parity',
    subtitle: '12 = 10 + 1 + 1 holding 12 -> 10/2 -> 1/1',
    badgeText: '12 = 10 + 1 + 1 · $0 Review',
    vocalTone: 'Crisp, mathematically authoritative',
    targetSectionId: 'pitch-beat-4',
    targetSectionName: 'Clearance Summary Cards & Invariant Conservation Ribbon',
    actionCue: '[METRIC RIBBON SNAPS: 10 CARRIED / 2 REOPENED] ... [HOVER: $0.00 REVIEW EXPENSE BADGE]',
    teleprompterScript:
      'Watch the **Deterministic Lineage Parity Guarantee**: Lienmark analyzes the causal dependency graph in `backend/core/invalidation_engine.py`. **Ten** decisions have identical context hashes and stable public evidence. Lienmark carries all ten decisions forward automatically. [PAUSE 1.0s]\n\nThat is 10 carried forward legal approvals: **zero dollars** spent on redundant attorney re-review, and **zero** external queries dispatched. Only the two affected decisions are reopened for counsel attention.',
    stressWords: [
      'Deterministic Lineage Parity Guarantee',
      'Ten',
      'zero dollars',
      'zero',
    ],
    keyMetrics: [
      { label: 'Carried Forward', value: '10 of 12 (83.3%)' },
      { label: 'Reopened for Review', value: '2 of 12 (16.7%)' },
      { label: 'Re-Review Cost', value: '$0.00 (100% saved)' },
    ],
    codePointers: [
      { label: 'Invalidation DAG', file: 'backend/core/invalidation_engine.py', lineRef: 'L120' },
      { label: 'Revalidation Planner', file: 'backend/services/revalidation_planner.py', lineRef: 'L40' },
    ],
    invariantGuarantee:
      'Invariant 4A & 4B: Selective invalidation holding 12 = 10 + 1 + 1 under 12 -> 10/2 -> 1/1 with zero-query carry forward.',
    accentColor: {
      border: 'border-sky-500/50',
      bg: 'bg-sky-950/20',
      text: 'text-sky-400',
      badge: 'bg-sky-500/20 text-sky-300 border-sky-500/40',
      glow: 'shadow-sky-500/20',
    },
  },
  {
    id: 5,
    timecode: '1:25–1:55',
    durationSeconds: 30,
    title: 'Beat 5: Targeted Parallel Search Dispatched',
    shortTitle: 'Targeted Parallel Search',
    subtitle: '83.3% query reduction, 142ms latency',
    badgeText: '83.3% Saved · 142ms API',
    vocalTone: 'High-tech, data-driven, highlighting API precision',
    targetSectionId: 'pitch-beat-5',
    targetSectionName: 'Parallel Search Corroboration & Lineage Telemetry',
    actionCue: '[CUT TO TELEMETRY TAB: 83.3% QUERY REDUCTION] ... [DISPLAY ITEM 11 CARD: LOC RENEWAL RECORDS] ... [DISPLAY ITEM 12 CARD: ASCAP ACE VANGUARD CLAIM]',
    teleprompterScript:
      'Instead of firing twelve expensive web searches, our budget governor dispatches the **Parallel Search API** in `backend/services/parallel_service.py` to re-ground strictly the two affected assets. That is an **eighty-three point three percent query reduction** (2 calls vs 12) at runtime. [PAUSE 1.0s]\n\nFor Item 11, Parallel searches the Library of Congress catalog in **142 milliseconds**, retrieving authoritative evidence that the 1946 registration expired without renewal, confirming the artwork is in the public domain. [PAUSE 1.0s]\n\nFor Item 12, Parallel queries ASCAP ACE repertory records, uncovering that sync rights were assigned to Vanguard Media last month. Stance: Contradictory. Lienmark strictly **fails closed**—public evidence never automatically clears a conflict.',
    stressWords: [
      'Parallel Search API',
      'eighty-three point three percent query reduction',
      '142 milliseconds',
      'fails closed',
    ],
    keyMetrics: [
      { label: 'Query Reduction', value: '83.3% (2 calls vs 12)' },
      { label: 'Item 11 Latency', value: '142.5ms (cocatalog.loc.gov)' },
      { label: 'Item 12 Policy', value: 'Fail-Closed Contradiction' },
    ],
    codePointers: [
      { label: 'Parallel Service Client', file: 'backend/services/parallel_service.py', lineRef: 'L45' },
      { label: 'Evidence Reconciler', file: 'backend/core/evidence_reconciler.py', lineRef: 'L45' },
    ],
    invariantGuarantee:
      'Invariant 5A, 5B & 5C: Exact 83.3% query reduction (2 vs 12), Library of Congress public domain citation, and fail-closed guardrail.',
    accentColor: {
      border: 'border-indigo-500/50',
      bg: 'bg-indigo-950/20',
      text: 'text-indigo-400',
      badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
      glow: 'shadow-indigo-500/20',
    },
  },
  {
    id: 6,
    timecode: '1:55–2:25',
    durationSeconds: 30,
    title: 'Beat 6: Human Counsel Checkpoint',
    shortTitle: 'Counsel Checkpoint Gate',
    subtitle: 'Sarah Jenkins Re-Attest/Reject',
    badgeText: 'Counsel Checkpoint · 1/1 Ledger',
    vocalTone: 'Deliberate, ethically grounded, human-in-the-loop',
    targetSectionId: 'pitch-beat-6',
    targetSectionName: 'Counsel Checkpoint Gate & Affirmative Adjudication Panel',
    actionCue: '[OPEN COUNSEL CHECKPOINT: SARAH JENKINS, ESQ.] ... [OPTIMISTIC UI UPDATE & TOAST CONFIRMATION] ... [ADVANCE TO ITEM 12 & CLICK EXCEPTION]',
    teleprompterScript:
      'Here is the human checkpoint: Lienmark separates AI decision support from legal adjudication via `backend/core/counsel_checkpoint.py`. For Item 11, Sarah Jenkins reviews the 4D breakdown, confirms public domain doctrine under 17 U.S.C. § 304, and clicks **Re-Attest**. [PAUSE 1.0s]\n\nVia Next.js Server Actions, Item 11 optimistically updates to 1 re-attested. The event is permanently chained into our tamper-evident **SHA-256 audit ledger** in `scripts/run_rehearsal.py`, preserving cryptographic proof of counsel sign-off. [PAUSE 1.0s]\n\nFor Item 12, counsel will not clear an adverse copyright claim. She designates the cue as **1 exception** on the schedule. Lienmark records the rejection, completing human review for Version 8.',
    stressWords: [
      'Sarah Jenkins',
      'Re-Attest',
      'SHA-256 audit ledger',
      '1 exception',
    ],
    keyMetrics: [
      { label: 'Adjudicator', value: 'Sarah Jenkins, Esq.' },
      { label: 'Chained Ledger', value: 'Tamper-Evident SHA-256' },
      { label: 'Disposition', value: '1 Re-Attested, 1 Exception' },
    ],
    codePointers: [
      { label: 'Counsel Checkpoint', file: 'backend/core/counsel_checkpoint.py', lineRef: 'L150' },
      { label: 'Server Action', file: 'frontend/app/actions.ts', lineRef: 'submitReviewAction' },
      { label: 'Audit Chaining', file: 'backend/core/counsel_checkpoint.py', lineRef: 'L620' },
    ],
    invariantGuarantee:
      'Invariant 6A, 6B & 6C: Human counsel adjudication, optimistic UI updates, and SHA-256 cryptographic audit chaining.',
    accentColor: {
      border: 'border-purple-500/50',
      bg: 'bg-purple-950/20',
      text: 'text-purple-400',
      badge: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
      glow: 'shadow-purple-500/20',
    },
  },
  {
    id: 7,
    timecode: '2:25–2:45',
    durationSeconds: 20,
    title: 'Beat 7: Form E&O-2026 Underwriting Schedule Export',
    shortTitle: 'Form E&O-2026 Binder',
    subtitle: 'SSR Printable Binder',
    badgeText: 'Form E&O-2026 · 10+1+1=12',
    vocalTone: 'Triumphant, conclusive, institutional polish',
    targetSectionId: 'pitch-beat-7',
    targetSectionName: 'Export Action Component & SSR Form E&O-2026 Report',
    actionCue: '[CLICK: "📄 EXPORT FORM E&O-2026 EXCEPTIONS SCHEDULE"] ... [ZOOM INTO 3-TIER BREAKDOWN & CLOSING LOGO]',
    teleprompterScript:
      'Finally, user exports the **Form E&O-2026 Exceptions Schedule** compiled by `backend/core/exceptions_schedule.py`. Rendered server-side for underwriter delivery via `frontend/app/report/[production_id]/page.tsx`, this document satisfies the mandatory clearance warranty conditions for carrier policy binding. [PAUSE 1.0s]\n\nNotice the mathematical conservation: **10 carried forward plus 1 re-attested plus 1 exception equals 12 total** under our **12 -> 10/2 -> 1/1** pipeline satisfying **12 = 10 + 1 + 1**. Clear, version-bound risk transparency for underwriters, brokers, and producers. That is **Lienmark**.',
    stressWords: [
      'Form E&O-2026 Exceptions Schedule',
      '10 carried forward plus 1 re-attested plus 1 exception equals 12 total',
      '12 -> 10/2 -> 1/1',
      '12 = 10 + 1 + 1',
      'Lienmark',
    ],
    keyMetrics: [
      { label: 'Schedule Version', value: 'Form E&O-2026 (SSR)' },
      { label: 'Parity Proof', value: '10 Carried + 1 Re-Attest + 1 Excp = 12' },
      { label: 'Target Runtime', value: '165s (2:45 total)' },
    ],
    codePointers: [
      { label: 'Schedule Generator', file: 'backend/core/exceptions_schedule.py', lineRef: 'L50' },
      { label: 'SSR Report Page', file: 'frontend/app/report/[production_id]/page.tsx', lineRef: 'L1' },
    ],
    invariantGuarantee:
      'Invariant 7A & 7B: High-fidelity SSR printable report with @media print and Mathematical Conservation Law (12 = 10 + 1 + 1 under 12 -> 10/2 -> 1/1).',
    accentColor: {
      border: 'border-cyan-500/50',
      bg: 'bg-cyan-950/20',
      text: 'text-cyan-400',
      badge: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
      glow: 'shadow-cyan-500/20',
    },
  },
];

const STORAGE_KEY_COLLAPSED = 'lienmark_directors_hud_collapsed';
const STORAGE_KEY_ACTIVE_BEAT = 'lienmark_directors_hud_active_beat';

export const DirectorsPresentationHud: React.FC<DirectorsPresentationHudProps> = ({
  activeBeat: controlledActiveBeat,
  onSelectBeat,
  className = '',
}) => {
  // Local state for collapsed banner with persistence (defaults to collapsed)
  const [isCollapsed, setIsCollapsed] = useState<boolean>(true);
  const [selectedBeatId, setSelectedBeatId] = useState<number>(1);
  const [hasCopiedScript, setHasCopiedScript] = useState<boolean>(false);
  const [isLargeTeleprompter, setIsLargeTeleprompter] = useState<boolean>(false);

  // Initialize from localStorage safely in useEffect
  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        const savedCollapsed = localStorage.getItem(STORAGE_KEY_COLLAPSED);
        if (savedCollapsed !== null) {
          setIsCollapsed(savedCollapsed === 'true');
        }
        const savedBeat = localStorage.getItem(STORAGE_KEY_ACTIVE_BEAT);
        if (savedBeat !== null) {
          const parsed = parseInt(savedBeat, 10);
          if (parsed >= 1 && parsed <= 7) {
            setSelectedBeatId(parsed);
          }
        }
      }
    } catch (e) {
      console.warn('[DirectorsPresentationHud] LocalStorage hydration warning', e);
    }
  }, []);

  // Sync with controlled prop if provided
  useEffect(() => {
    if (
      controlledActiveBeat !== undefined &&
      controlledActiveBeat >= 1 &&
      controlledActiveBeat <= 7
    ) {
      setSelectedBeatId(controlledActiveBeat);
    }
  }, [controlledActiveBeat]);

  // Persist collapsed state
  const handleToggleCollapse = useCallback(() => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        if (typeof window !== 'undefined') {
          localStorage.setItem(STORAGE_KEY_COLLAPSED, String(next));
        }
      } catch (e) {
        console.warn('[DirectorsPresentationHud] LocalStorage write error', e);
      }
      return next;
    });
  }, []);

  // Active beat data lookup
  const activeBeatData = useMemo(() => {
    return PITCH_BEATS.find((b) => b.id === selectedBeatId) || PITCH_BEATS[0];
  }, [selectedBeatId]);

  // Non-mutating selection handler with smooth scroll and spotlight effect
  const handleSelectBeat = useCallback(
    (beatId: number) => {
      if (beatId < 1 || beatId > 7) return;

      setSelectedBeatId(beatId);
      try {
        if (typeof window !== 'undefined') {
          localStorage.setItem(STORAGE_KEY_ACTIVE_BEAT, String(beatId));
        }
      } catch (e) {
        console.warn('[DirectorsPresentationHud] LocalStorage write error', e);
      }

      // 1. Fire non-mutating callback to host page
      if (onSelectBeat) {
        onSelectBeat(beatId);
      }

      // 2. Client-side Spotlight & Smooth Scroll Navigation
      const targetBeat = PITCH_BEATS.find((b) => b.id === beatId);
      if (targetBeat && typeof document !== 'undefined') {
        const targetElement =
          document.getElementById(targetBeat.targetSectionId) ||
          document.querySelector(`[data-pitch-beat="${beatId}"]`) ||
          document.querySelector(`[aria-label*="${targetBeat.shortTitle}"]`);

        if (targetElement) {
          targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });

          // Momentary non-destructive spotlight ring
          targetElement.classList.add(
            'ring-4',
            'ring-sky-400',
            'ring-offset-4',
            'ring-offset-[#0a0f1d]',
            'transition-all',
            'duration-500'
          );

          window.setTimeout(() => {
            targetElement.classList.remove(
              'ring-4',
              'ring-sky-400',
              'ring-offset-4',
              'ring-offset-[#0a0f1d]'
            );
          }, 2400);
        }
      }
    },
    [onSelectBeat]
  );

  const handleNextBeat = useCallback(() => {
    const nextId = selectedBeatId >= 7 ? 1 : selectedBeatId + 1;
    handleSelectBeat(nextId);
  }, [selectedBeatId, handleSelectBeat]);

  const handlePrevBeat = useCallback(() => {
    const prevId = selectedBeatId <= 1 ? 7 : selectedBeatId - 1;
    handleSelectBeat(prevId);
  }, [selectedBeatId, handleSelectBeat]);

  // Global Keyboard Shortcuts (1-7, H, ArrowLeft, ArrowRight)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isInput =
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.tagName === 'SELECT' ||
          target.isContentEditable);

      if (isInput) return;

      if (e.key >= '1' && e.key <= '7') {
        e.preventDefault();
        const beatNum = parseInt(e.key, 10);
        handleSelectBeat(beatNum);
      } else if (e.key === 'h' || e.key === 'H') {
        e.preventDefault();
        handleToggleCollapse();
      } else if (e.key === 'ArrowRight' && (e.altKey || e.ctrlKey)) {
        e.preventDefault();
        handleNextBeat();
      } else if (e.key === 'ArrowLeft' && (e.altKey || e.ctrlKey)) {
        e.preventDefault();
        handlePrevBeat();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSelectBeat, handleToggleCollapse, handleNextBeat, handlePrevBeat]);

  // Copy teleprompter script to clipboard
  const handleCopyScript = useCallback(() => {
    if (!activeBeatData) return;
    try {
      navigator.clipboard.writeText(
        `[${activeBeatData.timecode}] ${activeBeatData.title}\n` +
          `Vocal Tone: ${activeBeatData.vocalTone}\n\n` +
          `${activeBeatData.teleprompterScript.replace(/\*\*/g, '')}`
      );
      setHasCopiedScript(true);
      window.setTimeout(() => setHasCopiedScript(false), 2000);
    } catch (err) {
      console.error('[DirectorsPresentationHud] Copy error', err);
    }
  }, [activeBeatData]);

  // Helper to render script with stress words highlighted in bold-italic gold
  const renderFormattedTeleprompter = (script: string, stressWords: string[]) => {
    const paragraphs = script.split('\n\n');

    return (
      <div className="space-y-2.5">
        {paragraphs.map((p, pIdx) => {
          // Tokenize string around pause badges and bold markers
          const parts = p.split(/(\[PAUSE 1\.0s\]|\*\*[^*]+\*\*)/g);

          return (
            <p
              key={pIdx}
              className={`leading-relaxed text-slate-200 font-sans selection:bg-amber-500/30 selection:text-amber-200 ${
                isLargeTeleprompter ? 'text-base sm:text-lg' : 'text-sm sm:text-base'
              }`}
            >
              {parts.map((part, idx) => {
                if (part === '[PAUSE 1.0s]') {
                  return (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1 mx-1.5 px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-[11px] font-mono font-bold text-amber-300 align-middle shadow-sm"
                      title="Deliberate 1.0s speaker cadence pause"
                    >
                      <Clock className="h-3 w-3 inline text-amber-400" aria-hidden="true" />
                      1.0s PAUSE
                    </span>
                  );
                }

                if (part.startsWith('**') && part.endsWith('**')) {
                  const inner = part.slice(2, -2);
                  return (
                    <strong
                      key={idx}
                      className="font-bold italic text-amber-300 bg-amber-950/40 px-1 py-0.5 rounded border-b-2 border-amber-400"
                    >
                      {inner}
                    </strong>
                  );
                }

                return <span key={idx}>{part}</span>;
              })}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <section
      aria-label="Director's Presentation HUD & Teleprompter Guide"
      role="region"
      className={`no-print print:hidden rounded-2xl border border-slate-800 bg-gradient-to-b from-[#12192d] to-[#0a0f1d] shadow-2xl transition-all duration-300 ${className}`}
    >
      {/* ========================================================================= */}
      {/* 1. TOP HEADER & COMPACT BAR                                               */}
      {/* ========================================================================= */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-5 border-b border-slate-800/80 bg-slate-950/60 rounded-t-2xl">
        {/* Left: Brand Identity & Current Beat Pill */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-600/20 text-amber-400 border border-amber-500/40 flex-shrink-0 shadow-md shadow-amber-500/10">
            <Clapperboard className="h-4 w-4" aria-hidden="true" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                Director&apos;s Pitch HUD
              </span>
              <span className="rounded bg-amber-500/10 border border-amber-500/30 px-1.5 py-0.2 text-[10px] font-mono text-amber-300">
                165s (2:45) Pitch
              </span>
              <span className="hidden md:inline-flex rounded bg-slate-800/80 border border-slate-700 px-1.5 py-0.2 text-[10px] font-mono text-slate-400">
                Policy E&amp;O-2026.1-DEVPOST
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Authoritative Teleprompter &bull; Non-Mutating Navigation &bull; Keys [1–7]
            </p>
          </div>
        </div>

        {/* Center: Compact Beat Indicator (when collapsed or compact screen) */}
        {isCollapsed && (
          <div className="flex items-center gap-2">
            <span className="rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1 text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              <span>
                Beat {activeBeatData.id}: {activeBeatData.shortTitle}
              </span>
              <span className="text-[10px] font-mono text-amber-400">
                ({activeBeatData.timecode})
              </span>
            </span>

            {/* Quick 1-7 Micro Pills */}
            <div className="hidden lg:flex items-center gap-1">
              {PITCH_BEATS.map((beat) => (
                <button
                  key={beat.id}
                  type="button"
                  onClick={() => handleSelectBeat(beat.id)}
                  title={`Beat ${beat.id}: ${beat.title} (${beat.timecode})`}
                  className={`h-6 w-6 rounded text-[11px] font-mono font-bold transition-all focus:outline-none ${
                    beat.id === selectedBeatId
                      ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/30 scale-105'
                      : 'bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
                >
                  {beat.id}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Right: Operational Controls & Collapse Toggle */}
        <div className="flex items-center gap-2">
          {/* Script Documentation Link */}
          <Link
            href="/pitch-script"
            target="_blank"
            rel="noopener noreferrer"
            title="Inspect Master Pitch Script & Teleprompter Reference in Repository"
            className="hidden sm:inline-flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span className="font-mono text-[11px] text-amber-400">docs/pitch_script.md</span>
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </Link>

          {/* Quick Collapse / Expand Toggle Button */}
          <button
            type="button"
            onClick={handleToggleCollapse}
            aria-expanded={!isCollapsed}
            aria-controls="directors-hud-content"
            className="flex items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-900/90 hover:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-all focus:outline-none focus:ring-2 focus:ring-amber-400 shadow-sm"
          >
            {isCollapsed ? (
              <>
                <ChevronDown className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                <span>Expand HUD</span>
                <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">[H]</span>
              </>
            ) : (
              <>
                <ChevronUp className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                <span>Collapse</span>
                <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">[H]</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 2. EXPANDABLE HUD CONTENT AREA                                            */}
      {/* ========================================================================= */}
      {!isCollapsed && (
        <div id="directors-hud-content" className="p-4 sm:p-5 space-y-4">
          {/* Horizontal 7-Beat Timeline Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 px-1">
              <span className="flex items-center gap-1.5">
                <Compass className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                <span>Video Story Arc Timeline (165s Total Target Runtime)</span>
              </span>
              <span>Press [1–7] to Jump Instantly</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
              {PITCH_BEATS.map((beat) => {
                const isSelected = beat.id === selectedBeatId;
                return (
                  <button
                    key={beat.id}
                    type="button"
                    onClick={() => handleSelectBeat(beat.id)}
                    className={`text-left rounded-xl p-2.5 transition-all duration-200 border relative group focus:outline-none focus:ring-2 focus:ring-amber-400 ${
                      isSelected
                        ? `bg-gradient-to-b from-slate-900 to-slate-950 ${beat.accentColor.border} ring-1 ring-amber-400/40 shadow-lg ${beat.accentColor.glow}`
                        : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/60 hover:border-slate-700'
                    }`}
                  >
                    {/* Top Row: Shortcut & Timecode */}
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <span
                        className={`rounded px-1.5 py-0.2 text-[10px] font-mono font-bold ${
                          isSelected
                            ? 'bg-amber-400 text-slate-950'
                            : 'bg-slate-800 text-slate-400 group-hover:text-slate-200'
                        }`}
                      >
                        [{beat.id}]
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {beat.timecode}
                      </span>
                    </div>

                    {/* Beat Name */}
                    <div
                      className={`text-xs font-bold line-clamp-1 ${
                        isSelected ? beat.accentColor.text : 'text-slate-300'
                      }`}
                    >
                      {beat.shortTitle}
                    </div>

                    {/* Subtitle / Key metric badge */}
                    <div className="mt-1">
                      <span
                        className={`text-[9px] font-mono font-semibold px-1 py-0.2 rounded border block truncate ${
                          isSelected
                            ? beat.accentColor.badge
                            : 'bg-slate-800/60 text-slate-400 border-slate-800'
                        }`}
                      >
                        {beat.badgeText}
                      </span>
                    </div>

                    {/* Active Bottom Glow Line */}
                    {isSelected && (
                      <div className="absolute -bottom-[1px] left-2 right-2 h-[2px] bg-gradient-to-r from-amber-400 to-orange-400 rounded-full" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Beat Teleprompter & Presenter Guidance Card */}
          <div className="rounded-xl border border-slate-800 bg-[#0d1322] p-4 sm:p-5 space-y-4 shadow-xl">
            {/* Teleprompter Meta Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-bold uppercase tracking-wider font-mono ${activeBeatData.accentColor.badge}`}
                  >
                    Beat {activeBeatData.id} of 7 &bull; {activeBeatData.timecode} ({activeBeatData.durationSeconds}s)
                  </span>
                  <span className="text-xs text-slate-400 font-mono hidden md:inline">
                    Target: {activeBeatData.targetSectionName}
                  </span>
                </div>
                <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                  {activeBeatData.title}
                </h3>
              </div>

              {/* Presenter Utilities */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {/* Font Size Toggle */}
                <button
                  type="button"
                  onClick={() => setIsLargeTeleprompter((prev) => !prev)}
                  title="Toggle Teleprompter Font Size"
                  className="rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 px-2.5 py-1 text-xs text-slate-300 transition-colors"
                >
                  <span className="font-mono text-[11px]">
                    Font: {isLargeTeleprompter ? 'Large' : 'Normal'}
                  </span>
                </button>

                {/* Copy Script Button */}
                <button
                  type="button"
                  onClick={handleCopyScript}
                  title="Copy Spoken Script to Clipboard"
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 px-2.5 py-1 text-xs text-slate-300 transition-colors"
                >
                  {hasCopiedScript ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
                      <span className="text-emerald-400 font-semibold">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                      <span>Copy Script</span>
                    </>
                  )}
                </button>

                {/* Spotlight Section Button */}
                <button
                  type="button"
                  onClick={() => handleSelectBeat(activeBeatData.id)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 px-3 py-1 text-xs font-bold text-slate-950 transition-all shadow-md shadow-amber-500/20 focus:outline-none focus:ring-2 focus:ring-amber-300"
                >
                  <Play className="h-3 w-3 fill-slate-950" aria-hidden="true" />
                  <span>Spotlight UI Section</span>
                </button>
              </div>
            </div>

            {/* Vocal Tone & Cadence Banner */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center rounded-lg border border-slate-800/80 bg-slate-900/60 p-3">
              <div className="md:col-span-8 flex items-center gap-2">
                <Volume2 className="h-4 w-4 text-amber-400 flex-shrink-0" aria-hidden="true" />
                <div className="text-xs">
                  <span className="text-slate-400 font-semibold">Presenter Tone: </span>
                  <span className="text-amber-300 font-medium italic">
                    &ldquo;{activeBeatData.vocalTone}&rdquo;
                  </span>
                </div>
              </div>

              <div className="md:col-span-4 flex items-center justify-end gap-2 text-[11px] font-mono text-slate-400">
                <span className="text-slate-500">Pacing:</span>
                <span className="text-slate-300 font-semibold">~126 wpm</span>
                <span>&bull;</span>
                <span className="text-slate-300 font-semibold">1.0s Cadence Pauses</span>
              </div>
            </div>

            {/* On-Screen Action Cue */}
            <div className="rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-xs font-mono text-slate-400 flex items-start gap-2">
              <span className="text-amber-400 font-bold flex-shrink-0">Action Cue:</span>
              <span className="text-slate-300">{activeBeatData.actionCue}</span>
            </div>

            {/* Spoken Voiceover Narration Teleprompter with Stress Words */}
            <div className="rounded-xl border border-amber-500/30 bg-gradient-to-b from-[#141d33] to-[#0d1424] p-4 sm:p-5 shadow-inner">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-3">
                <span className="text-[11px] font-mono uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Spoken Voiceover Narration (Read Aloud)</span>
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  Gold/Underlined = Vocal Stress &bull; Badges = Pauses
                </span>
              </div>

              {renderFormattedTeleprompter(
                activeBeatData.teleprompterScript,
                activeBeatData.stressWords
              )}
            </div>

            {/* Quantitative Key Metrics & Repository Code Pointers */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-1">
              {/* Key Metrics */}
              <div className="md:col-span-6 rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1.5">
                <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">
                  Key Quantitative Invariants
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {activeBeatData.keyMetrics.map((metric, mIdx) => (
                    <div key={mIdx} className="rounded bg-slate-950/60 p-2 border border-slate-800/80">
                      <div className="text-[10px] text-slate-400 truncate">{metric.label}</div>
                      <div className="text-xs font-bold text-white mt-0.5 truncate">
                        {metric.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Code Pointers */}
              <div className="md:col-span-6 rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1.5">
                <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">
                  Verified Repository Code Pointers
                </div>
                <div className="space-y-1">
                  {activeBeatData.codePointers.map((pointer, pIdx) => (
                    <div
                      key={pIdx}
                      className="flex items-center justify-between text-xs font-mono bg-slate-950/60 px-2.5 py-1.5 rounded border border-slate-800/80"
                    >
                      <span className="text-slate-300">{pointer.label}</span>
                      <span className="text-sky-400">
                        {pointer.file}
                        {pointer.lineRef ? `:${pointer.lineRef}` : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Invariant Guarantee Banner */}
            <div className="rounded-lg border border-sky-500/30 bg-sky-950/20 px-3.5 py-2 text-xs flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-sky-400 flex-shrink-0" aria-hidden="true" />
                <span className="text-slate-300">
                  <strong>Invariant Guarantee:</strong> {activeBeatData.invariantGuarantee}
                </span>
              </div>
              <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] font-mono text-sky-300 flex-shrink-0">
                Non-Mutating Navigation
              </span>
            </div>

            {/* Bottom Navigation Pagination Controls */}
            <div className="flex items-center justify-between border-t border-slate-800 pt-3">
              <button
                type="button"
                onClick={handlePrevBeat}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400"
              >
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Previous Beat</span>
                <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">[Ctrl+←]</span>
              </button>

              <div className="flex items-center gap-1.5">
                {PITCH_BEATS.map((beat) => (
                  <button
                    key={beat.id}
                    type="button"
                    onClick={() => handleSelectBeat(beat.id)}
                    className={`h-2 rounded-full transition-all ${
                      beat.id === selectedBeatId
                        ? 'w-6 bg-amber-400'
                        : 'w-2 bg-slate-700 hover:bg-slate-500'
                    }`}
                    aria-label={`Jump to Beat ${beat.id}`}
                  />
                ))}
              </div>

              <button
                type="button"
                onClick={handleNextBeat}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400"
              >
                <span>Next Beat</span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">[Ctrl+→]</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default DirectorsPresentationHud;
