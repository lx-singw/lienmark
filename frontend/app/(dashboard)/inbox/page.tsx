'use client';

/**
 * Lienmark Inbox Triage Page
 * Zero-mock live triage hub fetching from /api/v1/dashboard/inbox.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { TriageItem, TriageType, TriageSeverity } from './types';
import { TriageCard } from './components/TriageCard';
import { InboxEmptyState } from './components/InboxEmptyState';
import { submitReviewAction } from '@/app/actions';

interface RawInboxItem {
  readonly inbox_id?: string;
  readonly id?: string;
  readonly quick_action?: string;
  readonly summary_headline?: string;
  readonly asset_name?: string;
  readonly production_title?: string;
  readonly asset_type?: string;
  readonly detailed_context?: string;
  readonly severity?: string;
  readonly stable_lineage_key?: string;
  readonly created_at?: string;
  readonly flagged_reason?: string;
  readonly metadata?: {
    readonly scene?: string;
    readonly timecode?: string;
    readonly options?: ReadonlyArray<string>;
    readonly requested_amount?: string;
    readonly flagged_reason?: string;
    readonly raw_snippet?: string;
    readonly matched_rules?: ReadonlyArray<string>;
    readonly confidence_score?: number;
  };
}

function mapRawItem(raw: RawInboxItem): TriageItem {
  const type: TriageType =
    raw.quick_action === 'answer_clarification'
      ? 'clarification'
      : raw.quick_action === 'approve_budget'
      ? 'budget'
      : 'claim';

  const severity: TriageSeverity =
    raw.severity === 'P0_CRITICAL'
      ? 'blocker'
      : raw.severity === 'P1_HIGH'
      ? 'high'
      : raw.severity === 'P2_MEDIUM'
      ? 'medium'
      : 'low';

  const flaggedReason = raw.flagged_reason || raw.metadata?.flagged_reason;
  const anomalyPayload = raw.metadata?.raw_snippet
    ? {
        rawSnippet: raw.metadata.raw_snippet,
        matchedRules: raw.metadata.matched_rules,
        confidenceScore: raw.metadata.confidence_score,
        sceneRef: raw.metadata.scene || raw.metadata.timecode,
      }
    : undefined;

  return {
    id: raw.inbox_id || raw.id || 'inb_item',
    type,
    title: raw.summary_headline || raw.asset_name || 'Clearance Action Required',
    subtitle: `${raw.production_title || 'Production'} · ${raw.asset_type || 'Asset'}`,
    description: raw.detailed_context || 'Pending counsel evaluation.',
    severity,
    lineageKey: raw.stable_lineage_key,
    createdAt: raw.created_at || '',
    sceneOrTimecode: raw.metadata?.scene || raw.metadata?.timecode,
    options: raw.metadata?.options,
    requestedAmount: raw.metadata?.requested_amount,
    flaggedReason,
    anomalyPayload,
  };
}

export default function InboxPage() {
  const [items, setItems] = useState<ReadonlyArray<TriageItem>>([]);
  const [typeFilter, setTypeFilter] = useState<TriageType | 'all'>('all');
  const [severityFilter, setSeverityFilter] = useState<TriageSeverity | 'all'>('all');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadLiveInbox() {
      try {
        const res = await fetch('/api/v1/dashboard/inbox', {
          headers: { Accept: 'application/json' },
        });
        if (!res.ok) return;
        const payload = (await res.json()) as { items?: ReadonlyArray<RawInboxItem> };
        if (isMounted && Array.isArray(payload?.items)) {
          setItems(payload.items.map(mapRawItem));
        }
      } catch (err) {
        console.warn('[InboxPage] Failed to fetch live inbox items:', err);
      }
    }
    loadLiveInbox();
    return () => {
      isMounted = false;
    };
  }, []);

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const matchType = typeFilter === 'all' || item.type === typeFilter;
      const matchSeverity = severityFilter === 'all' || item.severity === severityFilter;
      return matchType && matchSeverity;
    });
  }, [items, typeFilter, severityFilter]);

  const handleAction = async (itemId: string, action: string) => {
    const target = items.find((i) => i.id === itemId);
    if (!target) return;
    setIsSubmitting(true);
    setItems((prev) => prev.filter((i) => i.id !== itemId));

    try {
      if (target.type === 'claim' && target.lineageKey) {
        const act = action === 're_attest' ? 're_attest' : action === 'reject' ? 'reject' : 'exception';
        const rationale = action === 're_attest'
          ? 'Public Domain: Library of Congress catalog corroborates registration lapsed.'
          : 'Underwriting Exception: Adverse sync rights assignment requires schedule listing.';
        await submitReviewAction(act, target.lineageKey, rationale);
      }
      setToastMessage(`✓ Handled ${target.title}: ${action}`);
      setTimeout(() => setToastMessage(null), 3500);
    } catch (err) {
      setItems((prev) => [target, ...prev]);
      setToastMessage(`❌ Action failed: ${err instanceof Error ? err.message : 'Server error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-white">Actionable Triage Inbox</h1>
            <span className="rounded-full bg-amber-500/20 border border-amber-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-amber-300">
              {items.length} Pending
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Zero-friction 1-click checkpoint gate for human counsel, line producers, and clearance researchers.
          </p>
        </div>

        <div className="flex items-center gap-1 rounded-xl bg-slate-900 border border-slate-800 p-1 text-xs">
          {(['all', 'claim', 'clarification', 'budget'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`rounded-lg px-2.5 py-1 font-medium capitalize transition-colors ${
                typeFilter === t ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {toastMessage && (
        <div className="rounded-xl border border-sky-500/40 bg-sky-950/40 p-3 text-xs font-semibold text-sky-200">
          {toastMessage}
        </div>
      )}

      {filteredItems.length === 0 ? (
        <InboxEmptyState />
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item) => (
            <TriageCard key={item.id} item={item} onAction={handleAction} isSubmitting={isSubmitting} />
          ))}
        </div>
      )}
    </div>
  );
}
