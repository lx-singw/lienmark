/**
 * dag_types.ts
 * TypeScript contracts for clearance research investigation DAG, nodes, edges,
 * subgoals, multi-hop depth indicators, and discovered secondary claims.
 * Sprint 3.2: Clearance Research DAG & Multi-Hop Query Visualizer.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript definitions.
 */

import type { SearchFinding } from './types';

// ============================================================================
// Node Classification & Status
// ============================================================================

export const DAGNodeType = {
  ROOT_CLAIM: 'root_claim',
  SUBGOAL: 'subgoal',
  QUERY_STEP: 'query_step',
  CITATION: 'citation',
  DISCOVERED_CLAIM: 'discovered_claim',
} as const;

export type DAGNodeType = (typeof DAGNodeType)[keyof typeof DAGNodeType];

export const DAGNodeStatus = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  STOPPED_THRESHOLD_MET: 'stopped_threshold_met',
  FAILED: 'failed',
} as const;

export type DAGNodeStatus = (typeof DAGNodeStatus)[keyof typeof DAGNodeStatus];

// ============================================================================
// Rights Subgoals & Multi-Hop Indicators
// ============================================================================

export const RightsSubgoalType = {
  COMPOSITION: 'composition',
  MASTER_RECORDING: 'master_recording',
  SYNC_LICENSE: 'sync_license',
  DERIVATIVE: 'derivative',
  TRADEMARK: 'trademark',
  PERFORMER_UNION: 'performer_union',
  OTHER: 'other',
} as const;

export type RightsSubgoalType =
  (typeof RightsSubgoalType)[keyof typeof RightsSubgoalType];

export const DAGEdgeRelationship = {
  DECOMPOSES_TO: 'decomposes_to',
  QUERIES: 'queries',
  YIELDS_FINDING: 'yields_finding',
  DISCOVERS_CLAIM: 'discovers_claim',
  REVALIDATES: 'revalidates',
} as const;

export type DAGEdgeRelationship =
  (typeof DAGEdgeRelationship)[keyof typeof DAGEdgeRelationship];

// ============================================================================
// Core Node & Edge Contracts
// ============================================================================

export interface DAGNode {
  readonly id: string;
  readonly type: DAGNodeType;
  readonly label: string;
  readonly description?: string;
  readonly status: DAGNodeStatus;
  readonly subgoal_type?: RightsSubgoalType;
  readonly hop_depth?: number;
  readonly is_discovered_in_research?: boolean;
  readonly discovery_rationale?: string;
  readonly query_string?: string;
  readonly action_code?: string;
  readonly stopped_reason?: string;
  readonly findings?: ReadonlyArray<SearchFinding>;
  readonly metadata?: Readonly<Record<string, string | number | boolean | null>>;
}

export interface DAGEdge {
  readonly id: string;
  readonly source_id: string;
  readonly target_id: string;
  readonly relationship: DAGEdgeRelationship;
  readonly label?: string;
  readonly animated?: boolean;
}

export interface InvestigationDAG {
  readonly dag_id: string;
  readonly asset_id: string;
  readonly root_claim_label: string;
  readonly nodes: ReadonlyArray<DAGNode>;
  readonly edges: ReadonlyArray<DAGEdge>;
  readonly created_at_utc: string;
  readonly updated_at_utc?: string;
}

// ============================================================================
// Layout Geometry & Coordinate Models
// ============================================================================

export interface PositionedDAGNode extends DAGNode {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
  readonly layer: number;
}

export interface PositionedDAGEdge {
  readonly id: string;
  readonly source_id: string;
  readonly target_id: string;
  readonly relationship: DAGEdgeRelationship;
  readonly path_d: string;
  readonly source_x: number;
  readonly source_y: number;
  readonly target_x: number;
  readonly target_y: number;
  readonly animated?: boolean;
}

export interface DAGLayoutOptions {
  readonly horizontal_spacing?: number;
  readonly vertical_spacing?: number;
  readonly node_width?: number;
  readonly node_height?: number;
}

export interface DAGLayoutResult {
  readonly nodes: ReadonlyArray<PositionedDAGNode>;
  readonly edges: ReadonlyArray<PositionedDAGEdge>;
  readonly total_width: number;
  readonly total_height: number;
  readonly min_x: number;
  readonly min_y: number;
}

// ============================================================================
// Styling & Presentation Models
// ============================================================================

export interface NodeStatusStyle {
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly dotBg: string;
  readonly label: string;
  readonly pulsing: boolean;
}

export interface SubgoalBadgeStyle {
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly label: string;
  readonly shortLabel: string;
}

export interface DiscoveredBadgeStyle {
  readonly bg: string;
  readonly text: string;
  readonly border: string;
  readonly ring: string;
  readonly label: string;
}
