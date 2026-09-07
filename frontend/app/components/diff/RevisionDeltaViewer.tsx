'use client';

/**
 * Lienmark Script RevisionDeltaViewer Component
 * Sprint 1.2: Visual Screenplay Delta Engine & Clearance Token Diff Inspector
 *
 * Capabilities:
 *  1. Visual side-by-side script comparison highlighting added, modified, and deleted clearance elements.
 *  2. Clear visual demarcation of scene headings (sluglines), dialogue alterations, and rights-bearing mentions.
 *  3. In-line token inspector for clearance dependencies with provenance links and invalidation rationales.
 *  4. Synchronized dual-pane view with line-matched numbering and change glyphs.
 *  5. Role-aware view status indicating current clearance authority.
 *
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
  GitCompare,
  PlusCircle,
  MinusCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Film,
  Music,
  Palette,
  Box,
  Tag,
  FileText,
  Eye,
  Filter,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  Info,
  Layers,
  Search,
  Lock,
} from 'lucide-react';
import { DecisionState, UserRole, hasClearanceAuthority } from '@/lib/types';

// ============================================================================
// Types & Interfaces
// ============================================================================

export type ScreenplayElementType =
  | 'scene_heading'
  | 'action'
  | 'character'
  | 'dialogue'
  | 'parenthetical'
  | 'transition';

export type DeltaClassification = 'added' | 'modified' | 'deleted' | 'unchanged';

export interface RightsBearingMention {
  id: string;
  text: string;
  assetType: 'artwork' | 'music' | 'prop' | 'trademark' | 'likeness' | 'location' | 'text' | string;
  lineageKey: string;
  classification: DeltaClassification;
  prominenceBefore?: string;
  prominenceAfter?: string;
  shiftDetails?: string;
  status: DecisionState;
  citations?: string;
}

export interface ScreenplayLine {
  id: string;
  lineNumber: number;
  type: ScreenplayElementType;
  text: string;
  classification: DeltaClassification;
  character?: string;
  mentions?: RightsBearingMention[];
}

export interface ScreenplayScene {
  sceneId: string;
  sceneNumber: string;
  timecode: string;
  classification: DeltaClassification;
  headingV7: string;
  headingV8: string;
  shiftType: 'creative' | 'evidence' | 'none' | 'added' | 'deleted';
  shiftExplanation?: string;
  v7Lines: ScreenplayLine[];
  v8Lines: ScreenplayLine[];
}

export interface RevisionDeltaViewerProps {
  baseVersionLabel?: string;
  targetVersionLabel?: string;
  baseContentHash?: string;
  targetContentHash?: string;
  selectedLineageKey?: string;
  onSelectLineageKey?: (key: string) => void;
  userRole?: UserRole;
  className?: string;
}

// ============================================================================
// Golden Demonstration Screenplay Delta Dataset
// ============================================================================

export const DEMO_SCREENPLAY_SCENES: ScreenplayScene[] = [
  // --------------------------------------------------------------------------
  // SCENE 42: Creative Drift (Hero Item 11 - Crime Detective Poster)
  // --------------------------------------------------------------------------
  {
    sceneId: 'sc_42',
    sceneNumber: 'SCENE 42',
    timecode: '00:44:12',
    classification: 'modified',
    shiftType: 'creative',
    shiftExplanation:
      'Creative Context Alteration: Poster shifted from 2s background blur into a 14s close-up focal insert with dialogue reading headline aloud, collapsing de minimis fair use defense.',
    headingV7: 'INT. DETECTIVE OFFICE - NIGHT (SCENE 42)',
    headingV8: 'INT. DETECTIVE OFFICE - NIGHT (SCENE 42)',
    v7Lines: [
      {
        id: 'v7_42_1',
        lineNumber: 412,
        type: 'action',
        text: 'Rain lashes against the grime-caked windowpanes. Raindrops streak across the cracked glass.',
        classification: 'unchanged',
      },
      {
        id: 'v7_42_2',
        lineNumber: 413,
        type: 'action',
        text: 'Jack steps into the room, shaking off his damp trench coat under the flickering amber incandescent bulb.',
        classification: 'unchanged',
      },
      {
        id: 'v7_42_3',
        lineNumber: 414,
        type: 'action',
        text: 'On the far wall, an out-of-focus framed 1946 Crime Detective Magazine poster hangs in soft background blur.',
        classification: 'modified',
        mentions: [
          {
            id: 'm_v7_poster',
            text: '1946 Crime Detective Magazine poster',
            assetType: 'artwork',
            lineageKey: 'poster_noir_detective_magazine',
            classification: 'modified',
            prominenceBefore: '2s background blur (soft focus, de minimis)',
            prominenceAfter: '14s close-up focal shot with dialogue',
            shiftDetails: 'Incidental background set dressing without narrative interaction.',
            status: DecisionState.CARRIED_FORWARD,
            citations: 'US Copyright Office Reg #B-1946-8821',
          },
        ],
      },
      {
        id: 'v7_42_4',
        lineNumber: 415,
        type: 'character',
        text: 'JACK',
        classification: 'unchanged',
      },
      {
        id: 'v7_42_5',
        lineNumber: 416,
        type: 'parenthetical',
        text: '(lighting a crumpled cigarette)',
        classification: 'unchanged',
      },
      {
        id: 'v7_42_6',
        lineNumber: 417,
        type: 'dialogue',
        text: "We're running out of time, Vance. If we don't have the ledgers by midnight, Apex calls the underwriters.",
        classification: 'unchanged',
      },
    ],
    v8Lines: [
      {
        id: 'v8_42_1',
        lineNumber: 412,
        type: 'action',
        text: 'Rain lashes against the grime-caked windowpanes. Raindrops streak across the cracked glass.',
        classification: 'unchanged',
      },
      {
        id: 'v8_42_2',
        lineNumber: 413,
        type: 'action',
        text: 'Jack steps into the room, shaking off his damp trench coat under the flickering amber incandescent bulb.',
        classification: 'unchanged',
      },
      {
        id: 'v8_42_3',
        lineNumber: 414,
        type: 'action',
        text: 'Jack strides past the desk, steps up to the wall, and rips down the framed 1946 Crime Detective Magazine poster. CAMERA ZOOMS IN TIGHT: FULL-SCREEN FOCAL INSERT (14 SECONDS) on the vivid pulp cover illustration depicting "SHADOWS OVER BROADWAY".',
        classification: 'modified',
        mentions: [
          {
            id: 'm_v8_poster',
            text: '1946 Crime Detective Magazine poster',
            assetType: 'artwork',
            lineageKey: 'poster_noir_detective_magazine',
            classification: 'modified',
            prominenceBefore: '2s background blur (soft focus, de minimis)',
            prominenceAfter: '14s close-up focal shot with dialogue',
            shiftDetails:
              'Material prominence surge: Featured focal insert + character dialogue recitation collapses prior fair use baseline. Statutory public domain re-attestation required.',
            status: DecisionState.STALE,
            citations: 'LOC Historical Catalog (cocatalog.loc.gov) confirms lapsed 1974 renewal.',
          },
        ],
      },
      {
        id: 'v8_42_4',
        lineNumber: 415,
        type: 'character',
        text: 'JACK',
        classification: 'unchanged',
      },
      {
        id: 'v8_42_5',
        lineNumber: 416,
        type: 'parenthetical',
        text: '(holding the poster up to the desk lamp, voice tense)',
        classification: 'modified',
      },
      {
        id: 'v8_42_6',
        lineNumber: 417,
        type: 'dialogue',
        text: 'Look at this headline: "Shadows Over Broadway"! They knew everything back in 1946. It was in print eighty years ago, right under their noses!',
        classification: 'modified',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // SCENE 18: External Evidence Drift (Hero Item 12 - Midnight Serenade)
  // --------------------------------------------------------------------------
  {
    sceneId: 'sc_18',
    sceneNumber: 'SCENE 18',
    timecode: '00:19:40',
    classification: 'modified',
    shiftType: 'evidence',
    shiftExplanation:
      'External Evidence Shift: Script text and audio cues are bit-for-bit identical, but external music copyright registries updated with an adverse ownership claim from Vanguard Media Holdings LLC.',
    headingV7: 'INT. SPEAKEASY LOUNGE - NIGHT (SCENE 18)',
    headingV8: 'INT. SPEAKEASY LOUNGE - NIGHT (SCENE 18)',
    v7Lines: [
      {
        id: 'v7_18_1',
        lineNumber: 182,
        type: 'action',
        text: 'Thick blue cigarette smoke hangs in atmospheric layers above velvet curved booths.',
        classification: 'unchanged',
      },
      {
        id: 'v7_18_2',
        lineNumber: 183,
        type: 'action',
        text: 'On the elevated bandstand, a muted jazz trumpet trio performs "Midnight Serenade" as atmospheric speakeasy background accompaniment (20 seconds).',
        classification: 'unchanged',
        mentions: [
          {
            id: 'm_v7_music',
            text: '"Midnight Serenade" jazz composition melody',
            assetType: 'music',
            lineageKey: 'music_cue_midnight_serenade',
            classification: 'unchanged',
            prominenceBefore: '20s background jazz performance',
            prominenceAfter: '20s background jazz performance',
            shiftDetails: 'Initial cue sheet listed as public domain arrangement.',
            status: DecisionState.CARRIED_FORWARD,
          },
        ],
      },
      {
        id: 'v7_18_3',
        lineNumber: 184,
        type: 'character',
        text: 'JACK',
        classification: 'unchanged',
      },
      {
        id: 'v7_18_4',
        lineNumber: 185,
        type: 'dialogue',
        text: 'The contract was signed in Chicago. We have the warranty clause right here in the briefcase.',
        classification: 'unchanged',
      },
    ],
    v8Lines: [
      {
        id: 'v8_18_1',
        lineNumber: 182,
        type: 'action',
        text: 'Thick blue cigarette smoke hangs in atmospheric layers above velvet curved booths.',
        classification: 'unchanged',
      },
      {
        id: 'v8_18_2',
        lineNumber: 183,
        type: 'action',
        text: 'On the elevated bandstand, a muted jazz trumpet trio performs "Midnight Serenade" as atmospheric speakeasy background accompaniment (20 seconds).',
        classification: 'unchanged',
        mentions: [
          {
            id: 'm_v8_music',
            text: '"Midnight Serenade" jazz composition melody',
            assetType: 'music',
            lineageKey: 'music_cue_midnight_serenade',
            classification: 'modified',
            prominenceBefore: '20s background jazz performance',
            prominenceAfter: '20s background jazz performance',
            shiftDetails:
              'External evidence invalidation: Vanguard Media Holdings LLC registered exclusive worldwide sync rights August 2026. Stance: CONTRADICTORY. Adjudication required: Exception or Replacement.',
            status: DecisionState.STALE,
            citations: 'ASCAP ACE Work #9921448 & Vanguard Assignment Bulletin (Aug 2026)',
          },
        ],
      },
      {
        id: 'v8_18_3',
        lineNumber: 184,
        type: 'character',
        text: 'JACK',
        classification: 'unchanged',
      },
      {
        id: 'v8_18_4',
        lineNumber: 185,
        type: 'dialogue',
        text: 'The contract was signed in Chicago. We have the warranty clause right here in the briefcase.',
        classification: 'unchanged',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // SCENE 04: Lineage Parity Locked (Hero Item 1 - Vintage Telephone)
  // --------------------------------------------------------------------------
  {
    sceneId: 'sc_04',
    sceneNumber: 'SCENE 04',
    timecode: '00:04:12',
    classification: 'unchanged',
    shiftType: 'none',
    shiftExplanation:
      'Deterministic Lineage Parity Verified: Bit-for-bit identical script context, placement, and external registries across revisions. Autonomous carry-forward with zero re-review cost.',
    headingV7: 'INT. DETECTIVE OFFICE - DAY (SCENE 04)',
    headingV8: 'INT. DETECTIVE OFFICE - DAY (SCENE 04)',
    v7Lines: [
      {
        id: 'v7_04_1',
        lineNumber: 48,
        type: 'action',
        text: 'Slanted morning sunlight cuts through dusty venetian blinds, striping the dark mahogany desk.',
        classification: 'unchanged',
      },
      {
        id: 'v7_04_2',
        lineNumber: 49,
        type: 'action',
        text: 'On the desk corner sits a 1950s Western Electric Rotary Phone (Model 500) in pristine black bakelite.',
        classification: 'unchanged',
        mentions: [
          {
            id: 'm_v7_phone',
            text: '1950s Western Electric Rotary Phone',
            assetType: 'prop',
            lineageKey: 'prop_vintage_telephone',
            classification: 'unchanged',
            prominenceBefore: 'Incidental background set dressing, 4s',
            prominenceAfter: 'Incidental background set dressing, 4s',
            shiftDetails: 'Bit-for-bit identical usage. Locked baseline parity.',
            status: DecisionState.CARRIED_FORWARD,
          },
        ],
      },
      {
        id: 'v7_04_3',
        lineNumber: 50,
        type: 'character',
        text: 'JACK',
        classification: 'unchanged',
      },
      {
        id: 'v7_04_4',
        lineNumber: 51,
        type: 'dialogue',
        text: 'Marlowe here. Make it quick.',
        classification: 'unchanged',
      },
    ],
    v8Lines: [
      {
        id: 'v8_04_1',
        lineNumber: 48,
        type: 'action',
        text: 'Slanted morning sunlight cuts through dusty venetian blinds, striping the dark mahogany desk.',
        classification: 'unchanged',
      },
      {
        id: 'v8_04_2',
        lineNumber: 49,
        type: 'action',
        text: 'On the desk corner sits a 1950s Western Electric Rotary Phone (Model 500) in pristine black bakelite.',
        classification: 'unchanged',
        mentions: [
          {
            id: 'm_v8_phone',
            text: '1950s Western Electric Rotary Phone',
            assetType: 'prop',
            lineageKey: 'prop_vintage_telephone',
            classification: 'unchanged',
            prominenceBefore: 'Incidental background set dressing, 4s',
            prominenceAfter: 'Incidental background set dressing, 4s',
            shiftDetails: 'Deterministic lineage parity verified ($0.00 review expense).',
            status: DecisionState.CARRIED_FORWARD,
          },
        ],
      },
      {
        id: 'v8_04_3',
        lineNumber: 50,
        type: 'character',
        text: 'JACK',
        classification: 'unchanged',
      },
      {
        id: 'v8_04_4',
        lineNumber: 51,
        type: 'dialogue',
        text: 'Marlowe here. Make it quick.',
        classification: 'unchanged',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // SCENE 45: Added Screenplay Element (New Trademark Mention)
  // --------------------------------------------------------------------------
  {
    sceneId: 'sc_45',
    sceneNumber: 'SCENE 45',
    timecode: '00:48:30',
    classification: 'added',
    shiftType: 'added',
    shiftExplanation:
      'Added Scene & Rights Mention: Revision v8 introduces a new exterior sequence in Times Square featuring an illuminated commercial billboard trademark for Apex Film Laboratories.',
    headingV7: '[SCENE NOT PRESENT IN SCRIPT CUT V7 LOCKED]',
    headingV8: 'EXT. TIMES SQUARE - DAWN (SCENE 45)',
    v7Lines: [
      {
        id: 'v7_45_0',
        lineNumber: 0,
        type: 'action',
        text: '— Empty (Scene 45 is a newly drafted revision in Cut v8) —',
        classification: 'deleted',
      },
    ],
    v8Lines: [
      {
        id: 'v8_45_1',
        lineNumber: 445,
        type: 'action',
        text: 'Cold pre-dawn mist coats the asphalt of 42nd Street. Steam belches in rhythmic plumes from sewer grates.',
        classification: 'added',
      },
      {
        id: 'v8_45_2',
        lineNumber: 446,
        type: 'action',
        text: 'High above the theater marquee, a towering illuminated neon sign blazes for "Apex Film Laboratories — Precision Negative Processing".',
        classification: 'added',
        mentions: [
          {
            id: 'm_v8_apex',
            text: 'Apex Film Laboratories neon trademark',
            assetType: 'trademark',
            lineageKey: 'trademark_apex_laboratories',
            classification: 'added',
            prominenceAfter: 'Establishing exterior billboard, 5s',
            shiftDetails: 'Newly introduced brand mark. Requires trademark clearance review or fictional company verification.',
            status: DecisionState.NEW,
          },
        ],
      },
      {
        id: 'v8_45_3',
        lineNumber: 447,
        type: 'character',
        text: 'JACK',
        classification: 'added',
      },
      {
        id: 'v8_45_4',
        lineNumber: 448,
        type: 'dialogue',
        text: 'New dawn. New rules. Nothing stays buried in this town.',
        classification: 'added',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // SCENE 10: Deleted Screenplay Element (Removed Prop Asset)
  // --------------------------------------------------------------------------
  {
    sceneId: 'sc_10',
    sceneNumber: 'SCENE 10',
    timecode: '00:11:15',
    classification: 'deleted',
    shiftType: 'deleted',
    shiftExplanation:
      'Removed Set Dressing Asset: The antique bronze bust of "Athena" featured in Cut v7 was removed from the set dressing in Revision v8.',
    headingV7: 'INT. HOTEL LOBBY - EVENING (SCENE 10)',
    headingV8: 'INT. HOTEL LOBBY - EVENING (SCENE 10)',
    v7Lines: [
      {
        id: 'v7_10_1',
        lineNumber: 110,
        type: 'action',
        text: 'Crystal chandeliers cast faceted prisms across polished Italian marble.',
        classification: 'unchanged',
      },
      {
        id: 'v7_10_2',
        lineNumber: 111,
        type: 'action',
        text: 'Jack passes an ornate antique bronze sculptured bust of "Athena" resting atop a gilded fluted pedestal.',
        classification: 'deleted',
        mentions: [
          {
            id: 'm_v7_bust',
            text: 'Antique bronze sculptured bust of "Athena"',
            assetType: 'artwork',
            lineageKey: 'artwork_bronze_bust_athena',
            classification: 'deleted',
            prominenceBefore: 'Hallway pedestal focal, 4s',
            shiftDetails: 'Asset removed from production revision. Retained in historical audit ledger.',
            status: DecisionState.REMOVED,
          },
        ],
      },
      {
        id: 'v7_10_3',
        lineNumber: 112,
        type: 'action',
        text: 'He strides directly toward the brass elevator bank without breaking pace.',
        classification: 'unchanged',
      },
    ],
    v8Lines: [
      {
        id: 'v8_10_1',
        lineNumber: 110,
        type: 'action',
        text: 'Crystal chandeliers cast faceted prisms across polished Italian marble.',
        classification: 'unchanged',
      },
      {
        id: 'v8_10_2',
        lineNumber: 111,
        type: 'action',
        text: 'He strides directly toward the brass elevator bank without breaking pace.',
        classification: 'unchanged',
      },
    ],
  },
];

// ============================================================================
// Helper Renderers
// ============================================================================

export function renderAssetBadge(assetType: string) {
  const norm = (assetType || '').toLowerCase();
  switch (norm) {
    case 'artwork':
    case 'art':
      return (
        <span className="inline-flex items-center gap-1 rounded bg-purple-950/80 text-purple-300 border border-purple-500/50 px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase">
          <Palette className="h-2.5 w-2.5 text-purple-400" aria-hidden="true" />
          <span>ART</span>
        </span>
      );
    case 'music':
      return (
        <span className="inline-flex items-center gap-1 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-500/50 px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase">
          <Music className="h-2.5 w-2.5 text-indigo-400" aria-hidden="true" />
          <span>MUSIC</span>
        </span>
      );
    case 'prop':
      return (
        <span className="inline-flex items-center gap-1 rounded bg-amber-950/80 text-amber-300 border border-amber-500/50 px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase">
          <Box className="h-2.5 w-2.5 text-amber-400" aria-hidden="true" />
          <span>PROP</span>
        </span>
      );
    case 'trademark':
      return (
        <span className="inline-flex items-center gap-1 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-500/50 px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase">
          <Tag className="h-2.5 w-2.5 text-cyan-400" aria-hidden="true" />
          <span>TRADEMARK</span>
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 text-[9px] font-mono uppercase">
          <Film className="h-2.5 w-2.5 text-slate-400" aria-hidden="true" />
          <span>{assetType}</span>
        </span>
      );
  }
}

export function renderDeltaGlyph(classification: DeltaClassification) {
  switch (classification) {
    case 'added':
      return (
        <span
          className="inline-flex items-center justify-center w-5 h-5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-mono text-xs font-bold"
          title="Added in Target Script Revision"
        >
          +
        </span>
      );
    case 'modified':
      return (
        <span
          className="inline-flex items-center justify-center w-5 h-5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono text-xs font-bold"
          title="Modified across Revisions"
        >
          &Delta;
        </span>
      );
    case 'deleted':
      return (
        <span
          className="inline-flex items-center justify-center w-5 h-5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40 font-mono text-xs font-bold"
          title="Deleted from Target Script Revision"
        >
          &minus;
        </span>
      );
    default:
      return (
        <span
          className="inline-flex items-center justify-center w-5 h-5 rounded bg-slate-800 text-slate-500 font-mono text-xs"
          title="Unchanged Baseline Element"
        >
          =
        </span>
      );
  }
}

// ============================================================================
// Main RevisionDeltaViewer Component
// ============================================================================

export const RevisionDeltaViewer: React.FC<RevisionDeltaViewerProps> = ({
  baseVersionLabel = 'Script Cut v7 Locked',
  targetVersionLabel = 'Cut v8 Revised',
  baseContentHash = 'a1b2c3d4e5f60718293a4b5c6d7e8f90',
  targetContentHash = 'f9e8d7c6b5a43210fedcba9876543210',
  selectedLineageKey,
  onSelectLineageKey,
  userRole = UserRole.REVIEWER,
  className = '',
}) => {
  const [activeChangeFilter, setActiveChangeFilter] = useState<'all' | DeltaClassification>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeMention, setActiveMention] = useState<RightsBearingMention | null>(() => {
    // Default to Hero Item 11 poster
    return (
      DEMO_SCREENPLAY_SCENES[0].v8Lines[2].mentions?.[0] || null
    );
  });
  const [selectedSceneId, setSelectedSceneId] = useState<string>('sc_42');

  const hasAuthority = hasClearanceAuthority(userRole);

  // Filter scenes based on filter and search
  const filteredScenes = useMemo(() => {
    return DEMO_SCREENPLAY_SCENES.filter((scene) => {
      // 1. Classification filter
      if (activeChangeFilter !== 'all' && scene.classification !== activeChangeFilter) {
        return false;
      }

      // 2. Search query filter
      if (searchQuery.trim().length > 0) {
        const q = searchQuery.toLowerCase();
        const matchesHeading =
          scene.headingV7.toLowerCase().includes(q) || scene.headingV8.toLowerCase().includes(q);
        const matchesSceneNum = scene.sceneNumber.toLowerCase().includes(q);
        const matchesText =
          scene.v7Lines.some((l) => l.text.toLowerCase().includes(q)) ||
          scene.v8Lines.some((l) => l.text.toLowerCase().includes(q));
        const matchesMention =
          scene.v7Lines.some((l) =>
            l.mentions?.some((m) => m.text.toLowerCase().includes(q) || m.lineageKey.includes(q))
          ) ||
          scene.v8Lines.some((l) =>
            l.mentions?.some((m) => m.text.toLowerCase().includes(q) || m.lineageKey.includes(q))
          );

        if (!matchesHeading && !matchesSceneNum && !matchesText && !matchesMention) {
          return false;
        }
      }

      return true;
    });
  }, [activeChangeFilter, searchQuery]);

  // Handle mention click
  const handleMentionClick = useCallback(
    (mention: RightsBearingMention) => {
      setActiveMention(mention);
      if (onSelectLineageKey) {
        onSelectLineageKey(mention.lineageKey);
      }
    },
    [onSelectLineageKey]
  );

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-[#0a0f1d] p-5 sm:p-6 shadow-2xl space-y-6 text-slate-100 ${className}`}
      role="region"
      aria-label="Script Revision Delta Viewer"
    >
      {/* ===================================================================== */}
      {/* 1. Header Toolbar: Versions, Hashes, Filters, and Role Status         */}
      {/* ===================================================================== */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30">
                <GitCompare className="h-5 w-5" aria-hidden="true" />
              </div>
              <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight">
                Revision Delta Viewer &middot; Screenplay AST Diff
              </h2>
            </div>

            {/* Version Transition Badge */}
            <div className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/90 px-2.5 py-1 text-xs font-mono text-slate-300">
              <span className="text-slate-400">{baseVersionLabel}</span>
              <span className="text-sky-400 font-bold">&rarr;</span>
              <span className="text-amber-300 font-bold">{targetVersionLabel}</span>
            </div>

            {/* Role Authority Indicator */}
            <div
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-mono ${
                hasAuthority
                  ? 'border-sky-500/40 bg-sky-950/40 text-sky-300'
                  : 'border-slate-700 bg-slate-900/80 text-slate-400'
              }`}
              title={
                hasAuthority
                  ? `Active Role: ${userRole} (Authorized to adjudicate clearance decisions)`
                  : `Active Role: ${userRole} (Read-Only Mode: Adjudication requires Reviewer role)`
              }
            >
              {hasAuthority ? (
                <ShieldCheck className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
              ) : (
                <Lock className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
              )}
              <span>Role: {userRole}</span>
              {!hasAuthority && (
                <span className="rounded bg-amber-950/80 px-1 py-0.2 text-[9px] text-amber-300 border border-amber-500/40 uppercase">
                  Read-Only
                </span>
              )}
            </div>
          </div>

          <p className="text-xs text-slate-400 max-w-3xl">
            Side-by-side screenplay comparison highlighting added, modified, and deleted clearance elements.
            Scene headings, dialogue alterations, and rights-bearing mentions are syntactically parsed and mapped.
          </p>
        </div>

        {/* Quick Jump Buttons for Hero Scenes */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-mono text-slate-500 mr-1">Hero Jump:</span>
          <button
            type="button"
            onClick={() => setSelectedSceneId('sc_42')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
              selectedSceneId === 'sc_42'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            Scene 42 (Poster Drift)
          </button>
          <button
            type="button"
            onClick={() => setSelectedSceneId('sc_18')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
              selectedSceneId === 'sc_18'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 font-bold'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            Scene 18 (Music Dispute)
          </button>
          <button
            type="button"
            onClick={() => setSelectedSceneId('sc_04')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
              selectedSceneId === 'sc_04'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
                : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            Scene 04 (Parity Lock)
          </button>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* 2. Filter Toolbar: Change Type Pills & Search                         */}
      {/* ===================================================================== */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#0d1426] p-2.5 rounded-xl border border-slate-800">
        <div className="flex items-center gap-1.5 overflow-x-auto" role="tablist">
          <span className="text-xs font-mono text-slate-400 px-2 flex items-center gap-1">
            <Filter className="h-3 w-3 text-sky-400" />
            <span>Filter:</span>
          </span>

          <button
            type="button"
            onClick={() => setActiveChangeFilter('all')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
              activeChangeFilter === 'all'
                ? 'bg-slate-700 text-white font-bold shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Scenes (5)
          </button>
          <button
            type="button"
            onClick={() => setActiveChangeFilter('modified')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeChangeFilter === 'modified'
                ? 'bg-amber-950/80 text-amber-200 border border-amber-500/40 font-bold'
                : 'text-amber-400 hover:text-amber-300'
            }`}
          >
            <span>&Delta; Modified (2)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveChangeFilter('added')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeChangeFilter === 'added'
                ? 'bg-emerald-950/80 text-emerald-200 border border-emerald-500/40 font-bold'
                : 'text-emerald-400 hover:text-emerald-300'
            }`}
          >
            <span>+ Added (1)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveChangeFilter('deleted')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeChangeFilter === 'deleted'
                ? 'bg-rose-950/80 text-rose-200 border border-rose-500/40 font-bold'
                : 'text-rose-400 hover:text-rose-300'
            }`}
          >
            <span>&minus; Deleted (1)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveChangeFilter('unchanged')}
            className={`px-2.5 py-1 rounded text-xs font-medium transition-all flex items-center gap-1 ${
              activeChangeFilter === 'unchanged'
                ? 'bg-slate-800 text-slate-200 border border-slate-600 font-bold'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>= Unchanged (1)</span>
          </button>
        </div>

        {/* Search within script text */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search dialogue, slugline, mention..."
            className="rounded-lg border border-slate-700 bg-slate-950 pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:border-sky-500 focus:outline-none w-56 font-mono"
          />
        </div>
      </div>

      {/* ===================================================================== */}
      {/* 3. Main Split View: Script Diff Panes & Rights Mention Inspector      */}
      {/* ===================================================================== */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left/Center Column (xl:col-span-8): Side-by-Side Dual Pane Screenplay */}
        <div className="xl:col-span-8 space-y-6">
          {filteredScenes.map((scene) => {
            const isSelectedScene = scene.sceneId === selectedSceneId;

            return (
              <div
                key={scene.sceneId}
                id={`scene-${scene.sceneId}`}
                className={`rounded-2xl border transition-all overflow-hidden ${
                  isSelectedScene
                    ? 'border-sky-500/60 bg-[#0d152a] shadow-xl ring-1 ring-sky-500/30'
                    : 'border-slate-800 bg-[#0c1222] hover:border-slate-700'
                }`}
              >
                {/* Scene Header Banner */}
                <div
                  onClick={() => setSelectedSceneId(scene.sceneId)}
                  className="p-3.5 bg-[#121b33] border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 cursor-pointer"
                >
                  <div className="flex items-center gap-2.5">
                    {renderDeltaGlyph(scene.classification)}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-white">
                          {scene.sceneNumber}
                        </span>
                        <span className="rounded bg-slate-900 border border-slate-700 px-2 py-0.5 text-[10px] font-mono text-amber-300 flex items-center gap-1">
                          <Clock className="h-2.5 w-2.5 text-amber-400" />
                          {scene.timecode}
                        </span>
                        {scene.shiftType === 'creative' && (
                          <span className="rounded bg-amber-950/80 border border-amber-500/50 px-2 py-0.2 text-[10px] font-mono font-bold text-amber-200 uppercase">
                            Creative Context Drift
                          </span>
                        )}
                        {scene.shiftType === 'evidence' && (
                          <span className="rounded bg-rose-950/80 border border-rose-500/50 px-2 py-0.2 text-[10px] font-mono font-bold text-rose-200 uppercase">
                            External Evidence Drift
                          </span>
                        )}
                        {scene.shiftType === 'none' && (
                          <span className="rounded bg-emerald-950/80 border border-emerald-500/40 px-2 py-0.2 text-[10px] font-mono font-bold text-emerald-300 uppercase">
                            Lineage Parity Locked
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {scene.headingV8}
                      </p>
                    </div>
                  </div>

                  <span className="text-[11px] font-mono text-slate-500">
                    Click to spotlight scene &middot; {scene.v8Lines.length} lines
                  </span>
                </div>

                {/* Shift Explanation Callout if modified or drift */}
                {scene.shiftExplanation && (
                  <div
                    className={`px-4 py-2.5 text-xs flex items-start gap-2 border-b ${
                      scene.shiftType === 'creative'
                        ? 'bg-amber-950/30 border-amber-500/30 text-amber-200'
                        : scene.shiftType === 'evidence'
                        ? 'bg-rose-950/30 border-rose-500/30 text-rose-200'
                        : scene.shiftType === 'added'
                        ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-200'
                        : scene.shiftType === 'deleted'
                        ? 'bg-rose-950/20 border-rose-500/20 text-slate-300'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300'
                    }`}
                  >
                    <Info className="h-4 w-4 shrink-0 mt-0.5 text-sky-400" />
                    <p className="leading-relaxed font-sans">{scene.shiftExplanation}</p>
                  </div>
                )}

                {/* Side-by-Side Screenplay Comparison Panes */}
                <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800">
                  {/* Pane Left: Prior Script Revision (Cut v7 Locked) */}
                  <div className="p-4 space-y-3 bg-[#080d1a]/80">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                      <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400 font-semibold uppercase">
                        <FileText className="h-3.5 w-3.5 text-slate-500" />
                        <span>{baseVersionLabel}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">
                        Hash: {baseContentHash.slice(0, 8)}
                      </span>
                    </div>

                    {/* Scene Slugline Demarcation */}
                    <div className="rounded bg-slate-900/90 border border-slate-800 px-3 py-1 text-xs font-mono font-bold text-slate-300 uppercase tracking-wide">
                      {scene.headingV7}
                    </div>

                    {/* V7 Lines */}
                    <div className="space-y-2 font-mono text-xs text-slate-300">
                      {scene.v7Lines.map((line) => (
                        <div
                          key={line.id}
                          className={`flex items-start gap-2.5 p-1.5 rounded transition-colors ${
                            line.classification === 'modified'
                              ? 'bg-amber-950/30 border-l-2 border-amber-500 text-amber-200'
                              : line.classification === 'deleted'
                              ? 'bg-rose-950/30 border-l-2 border-rose-500 line-through text-slate-400'
                              : 'text-slate-300 hover:bg-slate-900/50'
                          }`}
                        >
                          <span className="text-[10px] text-slate-600 select-none w-7 text-right shrink-0">
                            {line.lineNumber > 0 ? line.lineNumber : '—'}
                          </span>

                          <div className="flex-1 space-y-1">
                            {line.type === 'character' && (
                              <div className="font-bold text-sky-300 text-center tracking-wider">
                                {line.text}
                              </div>
                            )}
                            {line.type === 'parenthetical' && (
                              <div className="italic text-slate-400 text-center">
                                {line.text}
                              </div>
                            )}
                            {line.type === 'dialogue' && (
                              <div className="px-6 text-slate-200 leading-relaxed">
                                {line.text}
                              </div>
                            )}
                            {line.type === 'action' && (
                              <div className="leading-relaxed text-slate-300">
                                {line.text}
                              </div>
                            )}

                            {/* Mentions in V7 Line */}
                            {line.mentions && line.mentions.length > 0 && (
                              <div className="pt-1 flex flex-wrap gap-1.5">
                                {line.mentions.map((m) => (
                                  <button
                                    key={m.id}
                                    type="button"
                                    onClick={() => handleMentionClick(m)}
                                    className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-mono transition-all ${
                                      activeMention?.id === m.id
                                        ? 'bg-sky-500/20 border-sky-400 text-white font-bold ring-1 ring-sky-400'
                                        : 'bg-slate-900/80 border-slate-700 text-slate-300 hover:border-sky-500'
                                    }`}
                                  >
                                    {renderAssetBadge(m.assetType)}
                                    <span>{m.text}</span>
                                    <span className="text-[9px] text-slate-400">
                                      ({m.prominenceBefore || 'v7 baseline'})
                                    </span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Pane Right: Revised Script Revision (Cut v8 Revised) */}
                  <div className="p-4 space-y-3 bg-[#0a1020]/90">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                      <div className="flex items-center gap-1.5 text-xs font-mono text-amber-300 font-semibold uppercase">
                        <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                        <span>{targetVersionLabel}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">
                        Hash: {targetContentHash.slice(0, 8)}
                      </span>
                    </div>

                    {/* Scene Slugline Demarcation */}
                    <div className="rounded bg-amber-950/30 border border-amber-500/40 px-3 py-1 text-xs font-mono font-bold text-amber-200 uppercase tracking-wide flex items-center justify-between">
                      <span>{scene.headingV8}</span>
                      {scene.classification === 'modified' && (
                        <span className="text-[9px] text-amber-400 uppercase font-sans font-semibold">
                          [MODIFIED SCENE BEAT]
                        </span>
                      )}
                    </div>

                    {/* V8 Lines */}
                    <div className="space-y-2 font-mono text-xs text-slate-300">
                      {scene.v8Lines.map((line) => (
                        <div
                          key={line.id}
                          className={`flex items-start gap-2.5 p-1.5 rounded transition-colors ${
                            line.classification === 'modified'
                              ? 'bg-amber-950/40 border-l-2 border-amber-400 text-amber-100 shadow-sm'
                              : line.classification === 'added'
                              ? 'bg-emerald-950/40 border-l-2 border-emerald-400 text-emerald-200'
                              : 'text-slate-300 hover:bg-slate-900/50'
                          }`}
                        >
                          <span className="text-[10px] text-slate-600 select-none w-7 text-right shrink-0">
                            {line.lineNumber}
                          </span>

                          <div className="flex-1 space-y-1">
                            {line.type === 'character' && (
                              <div className="font-bold text-sky-300 text-center tracking-wider">
                                {line.text}
                              </div>
                            )}
                            {line.type === 'parenthetical' && (
                              <div
                                className={`italic text-center ${
                                  line.classification === 'modified'
                                    ? 'text-amber-300 font-semibold'
                                    : 'text-slate-400'
                                }`}
                              >
                                {line.text}
                              </div>
                            )}
                            {line.type === 'dialogue' && (
                              <div
                                className={`px-6 leading-relaxed ${
                                  line.classification === 'modified'
                                    ? 'text-amber-200 font-serif font-medium bg-amber-950/30 p-2 rounded border border-amber-500/30'
                                    : 'text-slate-200'
                                }`}
                              >
                                {line.classification === 'modified' && (
                                  <span className="block text-[10px] font-mono text-amber-400 font-bold uppercase mb-1">
                                    &Delta; Dialogue Alteration Detected:
                                  </span>
                                )}
                                &ldquo;{line.text}&rdquo;
                              </div>
                            )}
                            {line.type === 'action' && (
                              <div
                                className={`leading-relaxed ${
                                  line.classification === 'modified'
                                    ? 'text-amber-100 font-medium'
                                    : line.classification === 'added'
                                    ? 'text-emerald-200'
                                    : 'text-slate-300'
                                }`}
                              >
                                {line.text}
                              </div>
                            )}

                            {/* Mentions in V8 Line */}
                            {line.mentions && line.mentions.length > 0 && (
                              <div className="pt-1.5 flex flex-wrap gap-1.5">
                                {line.mentions.map((m) => (
                                  <button
                                    key={m.id}
                                    type="button"
                                    onClick={() => handleMentionClick(m)}
                                    className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-mono transition-all shadow-sm ${
                                      activeMention?.id === m.id
                                        ? 'bg-sky-500/30 border-sky-400 text-white font-bold ring-2 ring-sky-400'
                                        : m.status === DecisionState.STALE
                                        ? 'bg-amber-950/80 border-amber-500/60 text-amber-200 hover:border-amber-400 animate-pulse'
                                        : m.status === DecisionState.CARRIED_FORWARD
                                        ? 'bg-emerald-950/80 border-emerald-500/60 text-emerald-200 hover:border-emerald-400'
                                        : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-sky-400'
                                    }`}
                                  >
                                    {renderAssetBadge(m.assetType)}
                                    <span className="font-semibold">{m.text}</span>
                                    <span className="text-[10px] opacity-80">
                                      [{m.classification.toUpperCase()}]
                                    </span>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column (xl:col-span-4): Clearance Token & Provenance Inspector */}
        <div className="xl:col-span-4 space-y-4 xl:sticky xl:top-6">
          <div className="rounded-2xl border border-slate-700 bg-gradient-to-b from-[#162038] to-[#101726] p-5 shadow-2xl space-y-4 border-t-2 border-t-sky-400">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Eye className="h-4 w-4 text-sky-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Clearance Mention Inspector
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                AST Token Link
              </span>
            </div>

            {activeMention ? (
              <div className="space-y-4 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    {renderAssetBadge(activeMention.assetType)}
                    <span className="text-[10px] font-mono text-slate-400 uppercase">
                      Asset Type: {activeMention.assetType}
                    </span>
                  </div>
                  <h4 className="text-base font-bold text-white mt-1">
                    {activeMention.text}
                  </h4>
                  <div className="text-[11px] font-mono text-sky-400 mt-0.5">
                    Lineage Key: <code className="text-amber-300">{activeMention.lineageKey}</code>
                  </div>
                </div>

                {/* Status Indicator */}
                <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-slate-400 uppercase">
                      Clearance Invalidation State:
                    </span>
                    {activeMention.status === DecisionState.STALE ? (
                      <span className="rounded-full bg-amber-950 border border-amber-500/60 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300 flex items-center gap-1 animate-pulse">
                        <AlertTriangle className="h-3 w-3 text-amber-400" />
                        <span>[STALE - ACTION REQUIRED]</span>
                      </span>
                    ) : activeMention.status === DecisionState.CARRIED_FORWARD ? (
                      <span className="rounded-full bg-emerald-950 border border-emerald-500/60 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                        <span>[CARRIED FORWARD]</span>
                      </span>
                    ) : (
                      <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-mono text-slate-300">
                        [{activeMention.status.toUpperCase()}]
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                    <div>
                      <span className="text-slate-500 block">V7 Prominence:</span>
                      <span className="text-slate-300 font-mono">
                        {activeMention.prominenceBefore || 'Standard (v7)'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">V8 Prominence:</span>
                      <span className="text-amber-300 font-mono font-semibold">
                        {activeMention.prominenceAfter || 'Unchanged'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Shift Details */}
                {activeMention.shiftDetails && (
                  <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3 space-y-1.5">
                    <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold block">
                      Differential Impact Analysis:
                    </span>
                    <p className="text-slate-200 leading-relaxed text-[11px]">
                      {activeMention.shiftDetails}
                    </p>
                  </div>
                )}

                {/* Citations & Evidence */}
                {activeMention.citations && (
                  <div className="rounded-xl border border-sky-500/30 bg-sky-950/30 p-3 space-y-1 text-[11px]">
                    <span className="text-[10px] font-mono text-sky-400 uppercase font-semibold block">
                      External Registry Corroboration:
                    </span>
                    <p className="text-sky-200 font-mono leading-relaxed">
                      {activeMention.citations}
                    </p>
                  </div>
                )}

                {/* Role-gated adjudication action link */}
                <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-400">
                    Authority: {userRole}
                  </span>
                  {hasAuthority ? (
                    <button
                      type="button"
                      onClick={() => {
                        if (onSelectLineageKey) {
                          onSelectLineageKey(activeMention.lineageKey);
                        }
                      }}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 px-3 py-1.5 text-xs font-bold text-slate-950 transition-colors shadow-sm"
                    >
                      <span>Adjudicate in 4D Gate</span>
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  ) : (
                    <span className="text-[10px] text-amber-300 font-mono italic">
                      Adjudication restricted to Reviewer
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className="py-8 text-center text-slate-500 text-xs">
                <Info className="h-6 w-6 mx-auto mb-2 text-slate-600" />
                <p>Click any highlighted mention token in the screenplay to inspect clearance lineage.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RevisionDeltaViewer;
