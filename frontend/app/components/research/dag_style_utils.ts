/**
 * dag_style_utils.ts
 * Styling helpers, status indicators, and badge themes for clearance research
 * investigation DAG nodes and subgoals.
 * Sprint 3.2: Clearance Research DAG & Multi-Hop Query Visualizer.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import {
  DAGNodeStatus,
  RightsSubgoalType,
  type NodeStatusStyle,
  type SubgoalBadgeStyle,
  type DiscoveredBadgeStyle,
} from './dag_types';

// ============================================================================
// Node Status Indicators
// ============================================================================

const NODE_STATUS_STYLES: Record<DAGNodeStatus, NodeStatusStyle> = {
  [DAGNodeStatus.COMPLETED]: {
    bg: 'bg-emerald-950/40',
    text: 'text-emerald-400',
    border: 'border-emerald-500/40',
    dotBg: 'bg-emerald-400',
    label: 'Completed',
    pulsing: false,
  },
  [DAGNodeStatus.IN_PROGRESS]: {
    bg: 'bg-sky-950/40',
    text: 'text-sky-400',
    border: 'border-sky-500/40',
    dotBg: 'bg-sky-400',
    label: 'In Progress',
    pulsing: true,
  },
  [DAGNodeStatus.STOPPED_THRESHOLD_MET]: {
    bg: 'bg-teal-950/40',
    text: 'text-teal-300',
    border: 'border-teal-500/40',
    dotBg: 'bg-teal-400',
    label: 'Threshold Met',
    pulsing: false,
  },
  [DAGNodeStatus.FAILED]: {
    bg: 'bg-rose-950/40',
    text: 'text-rose-400',
    border: 'border-rose-500/40',
    dotBg: 'bg-rose-400',
    label: 'Failed',
    pulsing: false,
  },
  [DAGNodeStatus.PENDING]: {
    bg: 'bg-slate-900/60',
    text: 'text-slate-400',
    border: 'border-slate-700/50',
    dotBg: 'bg-slate-500',
    label: 'Pending',
    pulsing: false,
  },
};

export function getNodeStatusStyle(status: DAGNodeStatus | string): NodeStatusStyle {
  return (
    NODE_STATUS_STYLES[status as DAGNodeStatus] ??
    NODE_STATUS_STYLES[DAGNodeStatus.PENDING]
  );
}

// ============================================================================
// Subgoal & Discovery Badges
// ============================================================================

const DEFAULT_SUBGOAL_STYLE: SubgoalBadgeStyle = {
  bg: 'bg-slate-800/60',
  text: 'text-slate-300',
  border: 'border-slate-700/40',
  label: 'Clearance Subgoal',
  shortLabel: 'Subgoal',
};

const SUBGOAL_BADGE_STYLES: Record<RightsSubgoalType, SubgoalBadgeStyle> = {
  [RightsSubgoalType.COMPOSITION]: {
    bg: 'bg-indigo-950/50',
    text: 'text-indigo-300',
    border: 'border-indigo-500/30',
    label: 'Musical Composition',
    shortLabel: 'Composition',
  },
  [RightsSubgoalType.MASTER_RECORDING]: {
    bg: 'bg-purple-950/50',
    text: 'text-purple-300',
    border: 'border-purple-500/30',
    label: 'Master Sound Recording',
    shortLabel: 'Master',
  },
  [RightsSubgoalType.SYNC_LICENSE]: {
    bg: 'bg-cyan-950/50',
    text: 'text-cyan-300',
    border: 'border-cyan-500/30',
    label: 'Synchronization Rights',
    shortLabel: 'Sync',
  },
  [RightsSubgoalType.DERIVATIVE]: {
    bg: 'bg-amber-950/50',
    text: 'text-amber-300',
    border: 'border-amber-500/30',
    label: 'Derivative Right',
    shortLabel: 'Derivative',
  },
  [RightsSubgoalType.TRADEMARK]: {
    bg: 'bg-blue-950/50',
    text: 'text-blue-300',
    border: 'border-blue-500/30',
    label: 'Registered Trademark',
    shortLabel: 'Trademark',
  },
  [RightsSubgoalType.PERFORMER_UNION]: {
    bg: 'bg-emerald-950/50',
    text: 'text-emerald-300',
    border: 'border-emerald-500/30',
    label: 'Union & Performer',
    shortLabel: 'Performer',
  },
  [RightsSubgoalType.OTHER]: {
    bg: 'bg-slate-800/60',
    text: 'text-slate-300',
    border: 'border-slate-700/40',
    label: 'Clearance Subgoal',
    shortLabel: 'Subgoal',
  },
};

export function getSubgoalBadgeStyle(
  subgoal?: RightsSubgoalType | string
): SubgoalBadgeStyle {
  if (!subgoal) return DEFAULT_SUBGOAL_STYLE;
  return (
    SUBGOAL_BADGE_STYLES[subgoal as RightsSubgoalType] ??
    DEFAULT_SUBGOAL_STYLE
  );
}

export function getDiscoveredBadgeStyle(): DiscoveredBadgeStyle {
  return {
    bg: 'bg-amber-500/15',
    text: 'text-amber-300',
    border: 'border-amber-500/40',
    ring: 'ring-1 ring-amber-500/30',
    label: 'Discovered in Research',
  };
}

export function getHopDepthLabel(depth?: number): string {
  if (depth === undefined || depth === null || !Number.isFinite(depth) || depth < 0) {
    return 'Hop 0';
  }
  return `Hop ${Math.floor(depth)}`;
}
