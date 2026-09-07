'use client';

/**
 * DAGNodeCard.tsx
 * Visual representation of an investigation DAG node with decomposed render helpers.
 * Sprint 3.2: Clearance Research DAG & Multi-Hop Query Visualizer.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  FileSearch,
  Sparkles,
  Search,
  Layers,
  ShieldAlert,
  Scale,
  FileCheck2,
} from 'lucide-react';
import {
  DAGNodeType,
  type PositionedDAGNode,
  type NodeStatusStyle,
} from './dag_types';
import {
  getNodeStatusStyle,
  getSubgoalBadgeStyle,
  getDiscoveredBadgeStyle,
  getHopDepthLabel,
} from './dag_style_utils';

export interface DAGNodeCardProps {
  readonly node: PositionedDAGNode;
  readonly isSelected?: boolean;
  readonly onClick?: () => void;
  readonly className?: string;
}

function getNodeIcon(type: DAGNodeType, isDiscovered?: boolean): React.ReactElement {
  if (isDiscovered) {
    return <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
  }
  switch (type) {
    case DAGNodeType.ROOT_CLAIM:
      return <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0" />;
    case DAGNodeType.SUBGOAL:
      return <Scale className="w-3.5 h-3.5 text-indigo-400 shrink-0" />;
    case DAGNodeType.QUERY_STEP:
      return <Search className="w-3.5 h-3.5 text-sky-400 shrink-0" />;
    case DAGNodeType.DISCOVERED_CLAIM:
      return <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
    case DAGNodeType.CITATION:
      return <FileCheck2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />;
    default:
      return <FileSearch className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
  }
}

function NodeHeader({ node, statusStyle }: { node: PositionedDAGNode; statusStyle: NodeStatusStyle }) {
  return (
    <div className="flex items-start justify-between gap-2 mb-1.5">
      <div className="flex items-center space-x-1.5 min-w-0">
        {getNodeIcon(node.type, node.is_discovered_in_research)}
        <span className="text-xs font-semibold text-slate-200 truncate" title={node.label}>
          {node.label}
        </span>
      </div>
      <span
        className={`w-2.5 h-2.5 rounded-full shrink-0 ${statusStyle.dotBg} ${
          statusStyle.pulsing ? 'animate-ping' : ''
        }`}
        title={statusStyle.label}
      />
    </div>
  );
}

function NodeBadges({ node }: { node: PositionedDAGNode }) {
  const subgoalStyle = getSubgoalBadgeStyle(node.subgoal_type);
  const discoveredStyle = getDiscoveredBadgeStyle();

  return (
    <div className="space-y-1.5 mb-2">
      {node.is_discovered_in_research && (
        <span
          className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${discoveredStyle.bg} ${discoveredStyle.text} ${discoveredStyle.border} ${discoveredStyle.ring}`}
        >
          <Sparkles className="w-2.5 h-2.5 mr-1 text-amber-400 shrink-0" />
          {discoveredStyle.label}
        </span>
      )}
      <div className="flex flex-wrap items-center gap-1.5">
        {node.subgoal_type && (
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${subgoalStyle.bg} ${subgoalStyle.text} ${subgoalStyle.border}`}>
            {subgoalStyle.shortLabel}
          </span>
        )}
        {node.hop_depth !== undefined && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800/80 text-cyan-300 border border-slate-700/60">
            {getHopDepthLabel(node.hop_depth)}
          </span>
        )}
        {node.action_code && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-500/30">
            {node.action_code}
          </span>
        )}
      </div>
    </div>
  );
}

function NodeContent({ node }: { node: PositionedDAGNode }) {
  if (node.query_string) {
    return (
      <div className="text-[11px] font-mono text-slate-400 truncate bg-slate-950/60 px-2 py-1 rounded border border-slate-800/80 mb-2">
        {node.query_string}
      </div>
    );
  }
  if (node.description) {
    return <div className="text-[11px] text-slate-400 line-clamp-2 mb-2">{node.description}</div>;
  }
  return null;
}

function NodeFooter({ node, statusStyle }: { node: PositionedDAGNode; statusStyle: NodeStatusStyle }) {
  const findingCount = node.findings?.length ?? 0;
  return (
    <div className="flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-800/70 pt-1.5 mt-auto">
      <span className={`font-medium ${statusStyle.text}`}>{statusStyle.label}</span>
      {findingCount > 0 && (
        <span className="flex items-center space-x-1 text-slate-300 bg-slate-800/60 px-1.5 py-0.5 rounded">
          <Layers className="w-2.5 h-2.5 text-cyan-400" />
          <span>{findingCount} {findingCount === 1 ? 'citation' : 'citations'}</span>
        </span>
      )}
    </div>
  );
}

export const DAGNodeCard: React.FC<DAGNodeCardProps> = ({
  node,
  isSelected = false,
  onClick,
  className = '',
}) => {
  const statusStyle = getNodeStatusStyle(node.status);
  const cardBorder = node.is_discovered_in_research
    ? 'bg-slate-900/90 border-amber-500/50 shadow-amber-950/20 ring-1 ring-amber-500/30'
    : 'bg-slate-900/85 border-slate-800 shadow-slate-950/40 hover:border-slate-700';
  const selectBorder = isSelected
    ? 'ring-2 ring-cyan-400 border-cyan-400 shadow-cyan-950/50 scale-[1.02]'
    : 'hover:scale-[1.01]';

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      className={`absolute select-none rounded-xl border p-3 transition-all duration-200 cursor-pointer text-left shadow-lg backdrop-blur-md flex flex-col justify-between ${cardBorder} ${selectBorder} ${className}`}
      style={{
        left: `${node.x}px`,
        top: `${node.y}px`,
        width: `${node.width}px`,
        minHeight: `${node.height}px`,
      }}
    >
      <div>
        <NodeHeader node={node} statusStyle={statusStyle} />
        <NodeBadges node={node} />
        <NodeContent node={node} />
      </div>
      <NodeFooter node={node} statusStyle={statusStyle} />
    </div>
  );
};
