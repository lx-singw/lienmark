'use client';

/**
 * InvestigationDAGVisualizer.tsx
 * Interactive visual graph visualizer for clearance research DAG traversal,
 * rights subgoals, multi-hop query steps, and discovered secondary claims.
 * Sprint 3.2: Clearance Research DAG & Multi-Hop Query Visualizer.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useMemo, useCallback } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Network, Sparkles } from 'lucide-react';
import {
  RightsSubgoalType,
  type InvestigationDAG,
  type DAGNode,
  type PositionedDAGNode,
  type PositionedDAGEdge,
} from './dag_types';
import { computeDAGHierarchicalLayout, filterDAGBySubgoal } from './dag_utils';
import { DAGNodeCard } from './DAGNodeCard';
import { DAGDetailsPopover } from './DAGDetailsPopover';

export interface InvestigationDAGVisualizerProps {
  readonly dag: InvestigationDAG;
  readonly initialSelectedNodeId?: string;
  readonly onNodeSelect?: (node: DAGNode | null) => void;
  readonly className?: string;
}

function ControlsBar({
  zoom,
  onZoomIn,
  onZoomOut,
  onResetZoom,
}: {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetZoom: () => void;
}) {
  return (
    <div className="flex items-center space-x-1 bg-slate-900/90 border border-slate-800 rounded-lg p-1">
      <button type="button" onClick={onZoomOut} className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800" title="Zoom Out">
        <ZoomOut className="w-3.5 h-3.5" />
      </button>
      <span className="text-[11px] font-mono text-slate-300 px-1.5">{Math.round(zoom * 100)}%</span>
      <button type="button" onClick={onZoomIn} className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800" title="Zoom In">
        <ZoomIn className="w-3.5 h-3.5" />
      </button>
      <button type="button" onClick={onResetZoom} className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 ml-1" title="Reset">
        <RotateCcw className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

function SubgoalFilters({ activeFilter, onChange }: { activeFilter: string; onChange: (filter: string) => void }) {
  const filters = [
    { key: 'all', label: 'All Subgoals' },
    { key: RightsSubgoalType.COMPOSITION, label: 'Composition' },
    { key: RightsSubgoalType.MASTER_RECORDING, label: 'Master Recording' },
    { key: RightsSubgoalType.SYNC_LICENSE, label: 'Sync License' },
  ];
  return (
    <div className="flex items-center space-x-1 overflow-x-auto py-1">
      {filters.map((f) => (
        <button
          key={f.key}
          type="button"
          onClick={() => onChange(f.key)}
          className={`px-2.5 py-1 rounded-md text-xs font-medium transition whitespace-nowrap ${
            activeFilter === f.key
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent'
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}

function DAGEdgesLayer({ edges, width, height }: { edges: ReadonlyArray<PositionedDAGEdge>; width: number; height: number }) {
  return (
    <svg className="absolute inset-0 pointer-events-none z-0" width={width} height={height} style={{ width: `${width}px`, height: `${height}px` }}>
      <defs>
        <marker id="dag-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M 0 1 L 8 5 L 0 9 z" fill="#0ea5e9" opacity="0.6" />
        </marker>
      </defs>
      {edges.map((e) => (
        <path
          key={e.id}
          d={e.path_d}
          fill="none"
          stroke="#0284c7"
          strokeWidth={e.animated ? 2.5 : 1.75}
          strokeOpacity={0.6}
          strokeDasharray={e.animated ? '6,4' : undefined}
          markerEnd="url(#dag-arrow)"
        />
      ))}
    </svg>
  );
}

function DAGLegend() {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/80 px-4 py-2 text-[11px] text-slate-400 bg-slate-950/70">
      <div className="flex flex-wrap items-center gap-4">
        <span className="flex items-center space-x-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400" /><span>Completed</span></span>
        <span className="flex items-center space-x-1.5"><span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" /><span>In Progress</span></span>
        <span className="flex items-center space-x-1.5"><span className="w-2 h-2 rounded-full bg-slate-500" /><span>Pending</span></span>
        <span className="flex items-center space-x-1.5"><span className="w-2 h-2 rounded-full bg-teal-400" /><span>Threshold Met</span></span>
      </div>
      <div className="flex items-center space-x-1 text-amber-300 font-medium">
        <Sparkles className="w-3 h-3 text-amber-400" /><span>Amber: Discovered in Research</span>
      </div>
    </div>
  );
}

function DAGCanvas({
  nodes,
  edges,
  width,
  height,
  zoom,
  selectedId,
  selectedNode,
  onNodeClick,
  onClosePopover,
}: {
  nodes: ReadonlyArray<PositionedDAGNode>;
  edges: ReadonlyArray<PositionedDAGEdge>;
  width: number;
  height: number;
  zoom: number;
  selectedId: string | null;
  selectedNode: DAGNode | null;
  onNodeClick: (node: DAGNode) => void;
  onClosePopover: () => void;
}) {
  return (
    <div className="relative h-[560px] w-full overflow-auto bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] p-4">
      <div className="relative transition-transform duration-150 origin-top-left" style={{ transform: `scale(${zoom})`, width: `${width}px`, height: `${height}px` }}>
        <DAGEdgesLayer edges={edges} width={width} height={height} />
        {nodes.map((node) => (
          <DAGNodeCard key={node.id} node={node} isSelected={node.id === selectedId} onClick={() => onNodeClick(node)} />
        ))}
      </div>
      <DAGDetailsPopover node={selectedNode} onClose={onClosePopover} />
    </div>
  );
}

export const InvestigationDAGVisualizer: React.FC<InvestigationDAGVisualizerProps> = ({
  dag,
  initialSelectedNodeId,
  onNodeSelect,
  className = '',
}) => {
  const [selectedId, setSelectedId] = useState<string | null>(initialSelectedNodeId ?? null);
  const [filter, setFilter] = useState<string>('all');
  const [zoom, setZoom] = useState<number>(1.0);

  const filteredDAG = useMemo(() => filterDAGBySubgoal(dag, filter as RightsSubgoalType | 'all'), [dag, filter]);
  const layout = useMemo(() => computeDAGHierarchicalLayout(filteredDAG.nodes, filteredDAG.edges), [filteredDAG]);
  const selectedNode = useMemo(() => dag.nodes.find((n) => n.id === selectedId) ?? null, [dag.nodes, selectedId]);

  const handleNodeClick = useCallback((node: DAGNode) => {
    const nextId = selectedId === node.id ? null : node.id;
    setSelectedId(nextId);
    onNodeSelect?.(nextId ? node : null);
  }, [selectedId, onNodeSelect]);

  return (
    <div className={`relative flex flex-col rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl overflow-hidden ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 px-4 py-3 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
            <Network className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100">{dag.root_claim_label}</h2>
            <p className="text-[11px] text-slate-400">Research DAG & Multi-Hop Traversal</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <SubgoalFilters activeFilter={filter} onChange={setFilter} />
          <ControlsBar zoom={zoom} onZoomIn={() => setZoom((z) => Math.min(1.8, z + 0.15))} onZoomOut={() => setZoom((z) => Math.max(0.6, z - 0.15))} onResetZoom={() => setZoom(1.0)} />
        </div>
      </div>
      <DAGCanvas nodes={layout.nodes} edges={layout.edges} width={layout.total_width} height={layout.total_height} zoom={zoom} selectedId={selectedId} selectedNode={selectedNode} onNodeClick={handleNodeClick} onClosePopover={() => setSelectedId(null)} />
      <DAGLegend />
    </div>
  );
};
