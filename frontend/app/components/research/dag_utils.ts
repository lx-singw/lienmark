/**
 * dag_utils.ts
 * Hierarchical tree and DAG layout calculation engine for clearance research visualizer.
 * Calculates node coordinates, curved bezier paths, and graph bounding dimensions.
 * Sprint 3.2: Clearance Research DAG & Multi-Hop Query Visualizer.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import {
  type DAGNode,
  type DAGEdge,
  type InvestigationDAG,
  type PositionedDAGNode,
  type PositionedDAGEdge,
  type DAGLayoutOptions,
  type DAGLayoutResult,
  type RightsSubgoalType,
} from './dag_types';

export * from './dag_style_utils';

// ============================================================================
// SVG Curved Edge Path Calculation
// ============================================================================

export function generateCurvedEdgePath(
  x1: number,
  y1: number,
  x2: number,
  y2: number
): string {
  const dy = Math.max(20, Math.abs(y2 - y1));
  const cy1 = y1 + dy * 0.45;
  const cy2 = y2 - dy * 0.45;
  return `M ${x1} ${y1} C ${x1} ${cy1}, ${x2} ${cy2}, ${x2} ${y2}`;
}

// ============================================================================
// Hierarchical Layer & Layout Engine
// ============================================================================

function assignNodeLayers(
  nodes: ReadonlyArray<DAGNode>,
  edges: ReadonlyArray<DAGEdge>
): Map<string, number> {
  const layerMap = new Map<string, number>();
  const incoming = new Set(edges.map((e) => e.target_id));

  for (const node of nodes) {
    if (!incoming.has(node.id) || node.type === 'root_claim') {
      layerMap.set(node.id, 0);
    }
  }

  let changed = true;
  let iterations = 0;
  while (changed && iterations < 20) {
    changed = false;
    iterations += 1;
    for (const edge of edges) {
      const srcLayer = layerMap.get(edge.source_id);
      if (srcLayer !== undefined) {
        const curTgt = layerMap.get(edge.target_id) ?? 0;
        const newLayer = Math.max(curTgt, srcLayer + 1);
        if (newLayer !== curTgt) {
          layerMap.set(edge.target_id, newLayer);
          changed = true;
        }
      }
    }
  }

  for (const node of nodes) {
    if (!layerMap.has(node.id)) {
      layerMap.set(node.id, node.hop_depth !== undefined ? node.hop_depth + 1 : 1);
    }
  }
  return layerMap;
}

function computeLayerGroups(
  nodes: ReadonlyArray<DAGNode>,
  layerMap: Map<string, number>
): { sortedKeys: number[]; layers: Map<number, DAGNode[]> } {
  const layers = new Map<number, DAGNode[]>();
  for (const node of nodes) {
    const layer = layerMap.get(node.id) ?? 0;
    const group = layers.get(layer) ?? [];
    group.push(node);
    layers.set(layer, group);
  }
  const sortedKeys = Array.from(layers.keys()).sort((a, b) => a - b);
  return { sortedKeys, layers };
}

function positionNodesInLayers(
  sortedKeys: number[],
  layers: Map<number, DAGNode[]>,
  canvasWidth: number,
  opts: { nodeW: number; nodeH: number; hSpacing: number; vSpacing: number }
): { positionedNodes: PositionedDAGNode[]; coordMap: Map<string, { x: number; y: number }> } {
  const positionedNodes: PositionedDAGNode[] = [];
  const coordMap = new Map<string, { x: number; y: number }>();

  for (const layer of sortedKeys) {
    const group = layers.get(layer) ?? [];
    const layerW = group.length * opts.nodeW + (group.length - 1) * opts.hSpacing;
    const startX = Math.max(20, (canvasWidth - layerW) / 2);
    const y = 40 + layer * (opts.nodeH + opts.vSpacing);

    group.forEach((node, idx) => {
      const x = startX + idx * (opts.nodeW + opts.hSpacing);
      positionedNodes.push({ ...node, x, y, width: opts.nodeW, height: opts.nodeH, layer });
      coordMap.set(node.id, { x, y });
    });
  }
  return { positionedNodes, coordMap };
}

function computePositionedEdges(
  edges: ReadonlyArray<DAGEdge>,
  coordMap: Map<string, { x: number; y: number }>,
  nodeW: number,
  nodeH: number
): PositionedDAGEdge[] {
  const positioned: PositionedDAGEdge[] = [];
  for (const edge of edges) {
    const src = coordMap.get(edge.source_id);
    const tgt = coordMap.get(edge.target_id);
    if (src && tgt) {
      const sx = src.x + nodeW / 2;
      const sy = src.y + nodeH;
      const tx = tgt.x + nodeW / 2;
      const ty = tgt.y;
      positioned.push({
        id: edge.id,
        source_id: edge.source_id,
        target_id: edge.target_id,
        relationship: edge.relationship,
        path_d: generateCurvedEdgePath(sx, sy, tx, ty),
        source_x: sx,
        source_y: sy,
        target_x: tx,
        target_y: ty,
        animated: edge.animated,
      });
    }
  }
  return positioned;
}

export function computeDAGHierarchicalLayout(
  nodes: ReadonlyArray<DAGNode>,
  edges: ReadonlyArray<DAGEdge>,
  options?: DAGLayoutOptions
): DAGLayoutResult {
  if (nodes.length === 0) {
    return { nodes: [], edges: [], total_width: 0, total_height: 0, min_x: 0, min_y: 0 };
  }

  const hSpacing = options?.horizontal_spacing ?? 36;
  const vSpacing = options?.vertical_spacing ?? 72;
  const nodeW = options?.node_width ?? 240;
  const nodeH = options?.node_height ?? 110;

  const layerMap = assignNodeLayers(nodes, edges);
  const { sortedKeys, layers } = computeLayerGroups(nodes, layerMap);
  const maxInLayer = Math.max(...sortedKeys.map((k) => (layers.get(k) ?? []).length));
  const canvasWidth = Math.max(860, maxInLayer * (nodeW + hSpacing) + 60);

  const { positionedNodes, coordMap } = positionNodesInLayers(
    sortedKeys,
    layers,
    canvasWidth,
    { nodeW, nodeH, hSpacing, vSpacing }
  );

  const positionedEdges = computePositionedEdges(edges, coordMap, nodeW, nodeH);
  const maxY = Math.max(...positionedNodes.map((n) => n.y + n.height));

  return {
    nodes: positionedNodes,
    edges: positionedEdges,
    total_width: canvasWidth,
    total_height: maxY + 50,
    min_x: 0,
    min_y: 0,
  };
}

export function filterDAGBySubgoal(
  dag: InvestigationDAG,
  subgoal?: RightsSubgoalType | 'all'
): InvestigationDAG {
  if (!subgoal || subgoal === 'all') return dag;

  const relevantNodeIds = new Set<string>();
  for (const node of dag.nodes) {
    if (node.type === 'root_claim' || node.subgoal_type === subgoal) {
      relevantNodeIds.add(node.id);
    }
  }

  const filteredNodes = dag.nodes.filter((n) => relevantNodeIds.has(n.id));
  const filteredEdges = dag.edges.filter(
    (e) => relevantNodeIds.has(e.source_id) && relevantNodeIds.has(e.target_id)
  );

  return {
    ...dag,
    nodes: filteredNodes,
    edges: filteredEdges,
  };
}
