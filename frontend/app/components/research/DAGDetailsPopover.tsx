'use client';

/**
 * DAGDetailsPopover.tsx
 * Expandable finding details popover for selected investigation DAG nodes.
 * Displays finding citations, discovery rationale, multi-hop context, and stopping criteria.
 * Sprint 3.2: Clearance Research DAG & Multi-Hop Query Visualizer.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  X,
  Sparkles,
  ShieldAlert,
  Search,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import type { DAGNode } from './dag_types';
import {
  getNodeStatusStyle,
  getSubgoalBadgeStyle,
  getDiscoveredBadgeStyle,
  getHopDepthLabel,
} from './dag_style_utils';
import { SourceCitation } from './SourceCitation';

export interface DAGDetailsPopoverProps {
  readonly node: DAGNode | null;
  readonly onClose: () => void;
}

function PopoverHeader({ node, onClose }: { node: DAGNode; onClose: () => void }) {
  const statusStyle = getNodeStatusStyle(node.status);
  return (
    <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
      <div className="flex items-center space-x-2 min-w-0 pr-2">
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${statusStyle.dotBg}`} />
        <h3 className="text-sm font-bold text-slate-100 truncate">{node.label}</h3>
        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${statusStyle.bg} ${statusStyle.text} border ${statusStyle.border}`}>
          {statusStyle.label}
        </span>
      </div>
      <button
        onClick={onClose}
        type="button"
        aria-label="Close details"
        className="text-slate-400 hover:text-slate-200 p-1 rounded-md hover:bg-slate-800 transition"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

function DiscoveryBanner({ node }: { node: DAGNode }) {
  if (!node.is_discovered_in_research) return null;
  const discoveredStyle = getDiscoveredBadgeStyle();

  return (
    <div className={`p-3 rounded-lg border mb-3.5 ${discoveredStyle.bg} ${discoveredStyle.border} ${discoveredStyle.ring}`}>
      <div className="flex items-center space-x-1.5 text-xs font-bold text-amber-300 mb-1">
        <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span>Discovered in Research (Secondary Claim)</span>
      </div>
      <p className="text-xs text-amber-200/90 leading-relaxed">
        {node.discovery_rationale ??
          'This adverse rights entity was uncovered dynamically during public registry search.'}
      </p>
    </div>
  );
}

function QueryAndStoppingDetails({ node }: { node: DAGNode }) {
  return (
    <div className="space-y-2 mb-3.5">
      {node.query_string && (
        <div>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
            Executed Search Query
          </span>
          <div className="font-mono text-xs text-slate-200 bg-slate-950 p-2.5 rounded border border-slate-800 break-all select-all">
            {node.query_string}
          </div>
        </div>
      )}
      {node.stopped_reason && (
        <div className="p-2.5 rounded bg-teal-950/40 border border-teal-500/30 text-xs text-teal-300">
          <div className="flex items-center space-x-1.5 font-semibold mb-0.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-teal-400" />
            <span>Stopping Criterion Satisfied</span>
          </div>
          <p className="text-teal-200/90">{node.stopped_reason}</p>
        </div>
      )}
    </div>
  );
}

function CitationsList({ node }: { node: DAGNode }) {
  const findings = node.findings ?? [];
  return (
    <div>
      <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
        <span>Attached Citations ({findings.length})</span>
      </div>
      {findings.length > 0 ? (
        <div className="space-y-2">
          {findings.map((f) => (
            <div key={f.id} className="p-2 rounded bg-slate-950/50 border border-slate-800/80">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-xs font-semibold text-slate-200 truncate">{f.source_title}</span>
                <SourceCitation finding={f} compact />
              </div>
              <p className="text-xs text-slate-400 line-clamp-2 italic">&ldquo;{f.source_snippet}&rdquo;</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-500 italic">No direct search citations attached to this step.</p>
      )}
    </div>
  );
}

export const DAGDetailsPopover: React.FC<DAGDetailsPopoverProps> = ({ node, onClose }) => {
  if (!node) return null;
  const subgoalStyle = getSubgoalBadgeStyle(node.subgoal_type);

  return (
    <div className="absolute right-4 top-16 z-30 w-96 max-h-[calc(100%-5rem)] overflow-y-auto rounded-xl border border-slate-700/80 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-right-4 duration-200">
      <PopoverHeader node={node} onClose={onClose} />
      <div className="flex flex-wrap items-center gap-1.5 mb-3">
        {node.subgoal_type && (
          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${subgoalStyle.bg} ${subgoalStyle.text} ${subgoalStyle.border}`}>
            {subgoalStyle.label}
          </span>
        )}
        {node.hop_depth !== undefined && (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-800 text-cyan-300 border border-slate-700">
            {getHopDepthLabel(node.hop_depth)}
          </span>
        )}
        {node.action_code && (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-950 text-indigo-300 border border-indigo-500/40">
            Action: {node.action_code}
          </span>
        )}
      </div>
      <DiscoveryBanner node={node} />
      {node.description && <p className="text-xs text-slate-300 leading-relaxed mb-3">{node.description}</p>}
      <QueryAndStoppingDetails node={node} />
      <CitationsList node={node} />
    </div>
  );
};
