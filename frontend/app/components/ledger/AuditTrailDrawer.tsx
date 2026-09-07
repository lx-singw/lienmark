'use client';

/**
 * AuditTrailDrawer Component
 * Slide-over drawer displaying the append-only cryptographic audit trail for a production.
 * Features sequence numbering, action badges, UTC timestamps, truncated hash previews with click-to-copy,
 * parent link verification status, expandable payload JSON viewers, and an Export Audit Manifest button.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  History,
  X,
  FileDown,
  Lock,
  Search,
  CheckCircle2,
  ShieldCheck,
  Hash,
  AlertTriangle,
} from 'lucide-react';
import { SupersessionEvent } from '@/lib/types';
import { AuditTrailItem } from './AuditTrailItem';
import { downloadAuditManifest, verifyParentLink } from './audit_utils';

export interface AuditTrailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  auditTrail: ReadonlyArray<SupersessionEvent>;
  productionId?: string;
  projectName?: string;
  onExportManifest?: () => void;
}

export const AuditTrailDrawer: React.FC<AuditTrailDrawerProps> = ({
  isOpen,
  onClose,
  auditTrail,
  productionId = 'prod_blockbuster_cinema',
  projectName = 'Shadows Over Broadway',
  onExportManifest,
}) => {
  const [copiedHash, setCopiedHash] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Close on ESC key press
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleCopyHash = useCallback((hash: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(hash);
      setCopiedHash(hash);
      setTimeout(() => setCopiedHash(null), 2000);
    }
  }, []);

  const handleExportClick = useCallback(() => {
    if (onExportManifest) {
      onExportManifest();
    } else {
      downloadAuditManifest(auditTrail, productionId);
    }
  }, [onExportManifest, auditTrail, productionId]);

  // Filter events based on search query
  const filteredEvents = useMemo(() => {
    if (!searchQuery.trim()) return auditTrail;
    const q = searchQuery.toLowerCase();
    return auditTrail.filter(
      (evt) =>
        evt.action.toLowerCase().includes(q) ||
        evt.stable_lineage_key.toLowerCase().includes(q) ||
        evt.event_hash.toLowerCase().includes(q) ||
        (evt.counsel_rationale || evt.rationale || '').toLowerCase().includes(q)
    );
  }, [auditTrail, searchQuery]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex justify-end animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-trail-drawer-heading"
    >
      <div className="w-full max-w-2xl bg-[#090e1a] border-l border-slate-700 h-full flex flex-col shadow-2xl overflow-hidden animate-in slide-in-from-right duration-300">
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/95">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/20 text-sky-400 border border-sky-500/30">
              <History className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 id="audit-trail-drawer-heading" className="text-base font-bold text-white tracking-tight">
                Cryptographic Audit Trail
              </h2>
              <p className="text-xs text-slate-400">
                {projectName} &middot; {auditTrail.length} recorded events
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Export Audit Manifest Button */}
            <button
              type="button"
              onClick={handleExportClick}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
              title="Export Full Audit Manifest JSON"
            >
              <FileDown className="h-4 w-4" />
              <span>Export Manifest</span>
            </button>

            {/* Close Button */}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-2 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
              aria-label="Close Audit Trail Drawer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Cryptographic Standards & Integrity Card */}
        <div className="p-4 bg-slate-950/80 border-b border-slate-800/80 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold text-sky-400 uppercase tracking-wider">
              <Lock className="h-3.5 w-3.5" />
              <span>SHA-256 Append-Only Hash Chain</span>
            </div>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-950 text-sky-200 border border-sky-500/40">
              <ShieldCheck className="h-3 w-3 text-emerald-400" />
              <span>E&amp;O WARRANTY COMPLIANT</span>
            </span>
          </div>

          <div className="font-mono text-xs text-amber-200 bg-slate-900/90 px-3 py-1.5 rounded-lg border border-slate-800">
            Formula: <strong className="text-white">event_hash = sha256(parent_hash + payload)</strong>
          </div>

          {/* Search / Filter input */}
          <div className="relative pt-1">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by action, lineage key, or hash..."
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900/80 pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none"
            />
          </div>
        </div>

        {/* Event List */}
        <div
          className="flex-1 overflow-y-auto p-4 space-y-3"
          tabIndex={0}
          role="region"
          aria-label="Chronological Cryptographic Audit Events"
        >
          {filteredEvents.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              No audit events matched your criteria.
            </div>
          ) : (
            filteredEvents.map((event, index) => {
              // Sequence number: total - index (if reverse chronological) or index + 1
              const seqNum = index + 1;
              // Link verification: compare current event's parent with previous chronological event
              const nextInArray = index < filteredEvents.length - 1 ? filteredEvents[index + 1] : undefined;
              const isVerified = verifyParentLink(event, nextInArray);

              return (
                <AuditTrailItem
                  key={event.event_id || `audit_${index}`}
                  event={event}
                  sequenceNumber={seqNum}
                  isLinkVerified={isVerified}
                  copiedHash={copiedHash}
                  onCopyHash={handleCopyHash}
                />
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/95 flex items-center justify-between text-xs text-slate-400">
          <span className="flex items-center gap-1.5 font-mono text-[11px]">
            <Hash className="h-3.5 w-3.5 text-sky-400" />
            <span>Tamper-Evident Title Record &middot; 17 U.S.C. § 504(c)</span>
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuditTrailDrawer;
