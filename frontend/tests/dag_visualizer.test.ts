/**
 * frontend/tests/dag_visualizer.test.ts
 * Automated unit test suite for Sprint 3.2 clearance research DAG visualizer.
 * Enforces file <= 250 lines and functions <= 40 lines strictly.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DAGNodeType,
  DAGNodeStatus,
  RightsSubgoalType,
  DAGEdgeRelationship,
  type DAGNode,
  type DAGEdge,
  type InvestigationDAG,
} from '../app/components/research/dag_types';
import {
  getNodeStatusStyle,
  getSubgoalBadgeStyle,
  getDiscoveredBadgeStyle,
  getHopDepthLabel,
} from '../app/components/research/dag_style_utils';
import {
  generateCurvedEdgePath,
  computeDAGHierarchicalLayout,
  filterDAGBySubgoal,
} from '../app/components/research/dag_utils';

test('getNodeStatusStyle: validates status colors and pulsing flags', () => {
  const completed = getNodeStatusStyle(DAGNodeStatus.COMPLETED);
  assert.equal(completed.label, 'Completed');
  assert.ok(completed.text.includes('emerald'));
  assert.equal(completed.pulsing, false);

  const inProgress = getNodeStatusStyle(DAGNodeStatus.IN_PROGRESS);
  assert.equal(inProgress.label, 'In Progress');
  assert.ok(inProgress.text.includes('sky'));
  assert.equal(inProgress.pulsing, true);

  const pending = getNodeStatusStyle(DAGNodeStatus.PENDING);
  assert.equal(pending.label, 'Pending');
  assert.ok(pending.text.includes('slate'));
  assert.equal(pending.pulsing, false);

  const thresholdMet = getNodeStatusStyle(DAGNodeStatus.STOPPED_THRESHOLD_MET);
  assert.equal(thresholdMet.label, 'Threshold Met');
  assert.ok(thresholdMet.text.includes('teal'));
  assert.equal(thresholdMet.pulsing, false);
});

test('getSubgoalBadgeStyle: correctly themes rights decomposition subgoals', () => {
  const comp = getSubgoalBadgeStyle(RightsSubgoalType.COMPOSITION);
  assert.equal(comp.shortLabel, 'Composition');
  assert.ok(comp.text.includes('indigo'));

  const master = getSubgoalBadgeStyle(RightsSubgoalType.MASTER_RECORDING);
  assert.equal(master.shortLabel, 'Master');
  assert.ok(master.text.includes('purple'));

  const sync = getSubgoalBadgeStyle(RightsSubgoalType.SYNC_LICENSE);
  assert.equal(sync.shortLabel, 'Sync');
  assert.ok(sync.text.includes('cyan'));
});

test('getDiscoveredBadgeStyle: renders distinctive amber/gold branding', () => {
  const style = getDiscoveredBadgeStyle();
  assert.equal(style.label, 'Discovered in Research');
  assert.ok(style.text.includes('amber'));
  assert.ok(style.ring.includes('amber'));
});

test('getHopDepthLabel: formats multi-hop depth numbers correctly', () => {
  assert.equal(getHopDepthLabel(0), 'Hop 0');
  assert.equal(getHopDepthLabel(1), 'Hop 1');
  assert.equal(getHopDepthLabel(2), 'Hop 2');
  assert.equal(getHopDepthLabel(undefined), 'Hop 0');
  assert.equal(getHopDepthLabel(-1), 'Hop 0');
});

test('generateCurvedEdgePath: produces valid SVG cubic bezier string', () => {
  const path = generateCurvedEdgePath(100, 50, 200, 250);
  assert.ok(path.startsWith('M 100 50 C 100 '));
  assert.ok(path.endsWith(', 200 250'));
});

const SAMPLE_NODES: DAGNode[] = [
  {
    id: 'root-1',
    type: DAGNodeType.ROOT_CLAIM,
    label: 'Clair de Lune (Debussy)',
    status: DAGNodeStatus.COMPLETED,
  },
  {
    id: 'subgoal-comp',
    type: DAGNodeType.SUBGOAL,
    label: 'Composition Rights',
    status: DAGNodeStatus.COMPLETED,
    subgoal_type: RightsSubgoalType.COMPOSITION,
  },
  {
    id: 'subgoal-master',
    type: DAGNodeType.SUBGOAL,
    label: 'Master Sound Recording',
    status: DAGNodeStatus.IN_PROGRESS,
    subgoal_type: RightsSubgoalType.MASTER_RECORDING,
  },
  {
    id: 'query-hop0',
    type: DAGNodeType.QUERY_STEP,
    label: 'ASCAP Work Lookup',
    status: DAGNodeStatus.COMPLETED,
    subgoal_type: RightsSubgoalType.COMPOSITION,
    hop_depth: 0,
    query_string: 'site:ascap.com/ace-title-search "Clair de Lune"',
  },
  {
    id: 'discovered-claim-1',
    type: DAGNodeType.DISCOVERED_CLAIM,
    label: 'Vanguard Media Master Rights',
    status: DAGNodeStatus.STOPPED_THRESHOLD_MET,
    subgoal_type: RightsSubgoalType.MASTER_RECORDING,
    hop_depth: 1,
    is_discovered_in_research: true,
    discovery_rationale: 'Found adverse assignee notation in sound recording database.',
    stopped_reason: 'Supplemental registration Form SR confirmed public domain arrangement.',
  },
];

const SAMPLE_EDGES: DAGEdge[] = [
  {
    id: 'e1',
    source_id: 'root-1',
    target_id: 'subgoal-comp',
    relationship: DAGEdgeRelationship.DECOMPOSES_TO,
  },
  {
    id: 'e2',
    source_id: 'root-1',
    target_id: 'subgoal-master',
    relationship: DAGEdgeRelationship.DECOMPOSES_TO,
  },
  {
    id: 'e3',
    source_id: 'subgoal-comp',
    target_id: 'query-hop0',
    relationship: DAGEdgeRelationship.QUERIES,
  },
  {
    id: 'e4',
    source_id: 'subgoal-master',
    target_id: 'discovered-claim-1',
    relationship: DAGEdgeRelationship.DISCOVERS_CLAIM,
  },
];

function createSampleDAG(): InvestigationDAG {
  return {
    dag_id: 'dag-test-01',
    asset_id: 'asset-cdl-001',
    root_claim_label: 'Clair de Lune',
    nodes: SAMPLE_NODES,
    edges: SAMPLE_EDGES,
    created_at_utc: '2026-09-07T10:00:00Z',
  };
}

test('computeDAGHierarchicalLayout: calculates layers and geometry', () => {
  const dag = createSampleDAG();
  const result = computeDAGHierarchicalLayout(dag.nodes, dag.edges);

  assert.equal(result.nodes.length, 5);
  assert.equal(result.edges.length, 4);
  assert.ok(result.total_width > 0);
  assert.ok(result.total_height > 0);

  const root = result.nodes.find((n) => n.id === 'root-1');
  assert.ok(root);
  assert.equal(root.layer, 0);
  assert.equal(root.y, 40);

  const subgoalComp = result.nodes.find((n) => n.id === 'subgoal-comp');
  assert.ok(subgoalComp);
  assert.equal(subgoalComp.layer, 1);
  assert.ok(subgoalComp.y > root.y);

  const discovered = result.nodes.find((n) => n.id === 'discovered-claim-1');
  assert.ok(discovered);
  assert.equal(discovered.is_discovered_in_research, true);
});

test('filterDAGBySubgoal: filters nodes and edges according to selected subgoal', () => {
  const dag = createSampleDAG();

  const allDAG = filterDAGBySubgoal(dag, 'all');
  assert.equal(allDAG.nodes.length, 5);
  assert.equal(allDAG.edges.length, 4);

  const compDAG = filterDAGBySubgoal(dag, RightsSubgoalType.COMPOSITION);
  assert.equal(compDAG.nodes.length, 3); // root + subgoal-comp + query-hop0
  assert.ok(compDAG.nodes.some((n) => n.id === 'root-1'));
  assert.ok(compDAG.nodes.some((n) => n.id === 'subgoal-comp'));
  assert.ok(compDAG.nodes.some((n) => n.id === 'query-hop0'));
  assert.equal(compDAG.edges.length, 2); // e1 + e3
});
