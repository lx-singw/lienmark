'use client';

/**
 * SearchExecutionModal.tsx
 * Real-time modal for clearance attorneys and researchers displaying:
 * - Active query string with syntax highlighting (site:, -negative, "quotes")
 * - Response latency meter, HTTP status badge, and result count
 * - Inverse steering indicator badge when fallback mode is triggered
 * Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useEffect, useCallback } from 'react';
import { X, Search, Sparkles, Zap, Info } from 'lucide-react';
import type {
  SearchExecutionTelemetry,
  SearchFinding,
} from './types';
import { TelemetryRibbon } from './TelemetryRibbon';
import { QuerySyntaxHighlighter } from './QuerySyntaxHighlighter';
import { SourceCitation } from './SourceCitation';

export interface SearchExecutionModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly telemetry: SearchExecutionTelemetry | null;
  readonly findings?: ReadonlyArray<SearchFinding>;
  readonly title?: string;
  readonly assetLabel?: string;
}

function ModalFindings({
  findings,
}: {
  readonly findings: ReadonlyArray<SearchFinding>;
}): React.ReactElement {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
          <Info className="w-3.5 h-3.5 text-cyan-400" />
          <span>Grounded Evidence & Source Citations</span>
        </h4>
        <span className="text-[11px] text-slate-400">
          {findings.length} citations
        </span>
      </div>
      {findings.length > 0 ? (
        <div className="flex flex-wrap gap-2 p-3.5 rounded-xl bg-cinema-black/50 border border-slate-800/80">
          {findings.map((f) => (
            <SourceCitation key={f.id} finding={f} />
          ))}
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-cinema-black/40 border border-slate-800/60 text-center text-slate-500 text-xs italic">
          No grounded findings returned for this query execution.
        </div>
      )}
    </div>
  );
}

function useEscapeKey(isOpen: boolean, onClose: () => void): void {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    },
    [isOpen, onClose]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

interface ModalHeaderProps {
  readonly title: string;
  readonly assetLabel?: string;
  readonly onClose: () => void;
}

const ModalHeader: React.FC<ModalHeaderProps> = ({
  title,
  assetLabel,
  onClose,
}) => (
  <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-cinema-slate/50">
    <div className="flex items-center space-x-3">
      <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
        <Search className="w-5 h-5" />
      </div>
      <div>
        <div className="flex items-center space-x-2">
          <h3 id="modal-title" className="text-base font-bold text-slate-100">
            {title}
          </h3>
          <span className="flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
            <Sparkles className="w-3 h-3" />
            <span>Sprint 3.1</span>
          </span>
        </div>
        <p className="text-xs text-slate-400">
          {assetLabel ? `Asset: ${assetLabel} • ` : ''}Real-time query optimization & clearance grounding
        </p>
      </div>
    </div>
    <button
      type="button"
      onClick={onClose}
      aria-label="Close modal"
      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
    >
      <X className="w-5 h-5" />
    </button>
  </div>
);

interface TelemetrySectionProps {
  readonly telemetry: SearchExecutionTelemetry | null;
}

const ModalTelemetrySection: React.FC<TelemetrySectionProps> = ({
  telemetry,
}) => {
  if (!telemetry) {
    return (
      <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center text-slate-400 text-xs">
        Waiting for search execution telemetry...
      </div>
    );
  }
  return (
    <>
      <TelemetryRibbon telemetry={telemetry} />
      <div>
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span>Active Query String</span>
        </h4>
        <QuerySyntaxHighlighter queryString={telemetry.query_string} />
      </div>
    </>
  );
};

interface ModalFooterProps {
  readonly timestampUtc?: string;
  readonly onClose: () => void;
}

const ModalFooter: React.FC<ModalFooterProps> = ({
  timestampUtc,
  onClose,
}) => (
  <div className="flex items-center justify-between px-6 py-3 border-t border-slate-800 bg-cinema-slate/30 text-xs text-slate-400">
    <div>
      {timestampUtc && (
        <span>Logged at {timestampUtc.slice(0, 19).replace('T', ' ')} UTC</span>
      )}
    </div>
    <button
      type="button"
      onClick={onClose}
      className="px-4 py-1.5 rounded-lg text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 transition-colors"
    >
      Dismiss
    </button>
  </div>
);

export const SearchExecutionModal: React.FC<SearchExecutionModalProps> = ({
  isOpen,
  onClose,
  telemetry,
  findings = [],
  title = 'Parallel Search Execution',
  assetLabel,
}) => {
  useEscapeKey(isOpen, onClose);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-cinema-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl bg-cinema-navy border border-slate-700/80 shadow-2xl overflow-hidden"
      >
        <ModalHeader title={title} assetLabel={assetLabel} onClose={onClose} />
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <ModalTelemetrySection telemetry={telemetry} />
          <ModalFindings findings={findings} />
        </div>
        <ModalFooter
          timestampUtc={telemetry?.timestamp_utc}
          onClose={onClose}
        />
      </div>
    </div>
  );
};

export default SearchExecutionModal;
