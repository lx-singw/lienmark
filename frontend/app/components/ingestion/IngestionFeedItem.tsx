'use client';

/**
 * IngestionFeedItem Component
 * Renders an individual storage event record in the activity feed.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  FileText,
  ExternalLink,
  Zap,
  Cloud,
  UploadCloud,
  AlertTriangle,
} from 'lucide-react';
import type { IngestionEvent, IngestionSource } from './types';
import { formatFileSize, getStatusBadgeStyle } from './ingestion_utils';

interface IngestionFeedItemProps {
  event: IngestionEvent;
}

function getSourceBadge(source: IngestionSource) {
  switch (source) {
    case 'CloudEvent Eventarc':
      return {
        icon: <Zap className="h-3 w-3 text-purple-400" />,
        className: 'border-purple-500/30 bg-purple-950/40 text-purple-300',
      };
    case 'GCS Poller':
      return {
        icon: <Cloud className="h-3 w-3 text-sky-400" />,
        className: 'border-sky-500/30 bg-sky-950/40 text-sky-300',
      };
    case 'Dropzone':
    default:
      return {
        icon: <UploadCloud className="h-3 w-3 text-emerald-400" />,
        className: 'border-emerald-500/30 bg-emerald-950/40 text-emerald-300',
      };
  }
}

export const IngestionFeedItem: React.FC<IngestionFeedItemProps> = ({ event }) => {
  const badgeStyle = getStatusBadgeStyle(event.status);
  const sourceBadge = getSourceBadge(event.source);

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-3.5 transition-colors hover:border-slate-700 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-700 bg-slate-800/80 text-sky-400">
          <FileText className="h-4 w-4" />
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-xs text-slate-200">{event.fileName}</span>
            <span className="rounded bg-slate-800 px-1.5 py-0.2 text-[10px] font-mono text-slate-400">
              {formatFileSize(event.fileSizeBytes)}
            </span>
            <span
              className={`flex items-center gap-1 rounded border px-1.5 py-0.2 text-[10px] font-medium ${sourceBadge.className}`}
            >
              {sourceBadge.icon}
              {event.source}
            </span>
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
            <span>
              Org: <code className="font-mono text-slate-300">{event.orgId}</code>
            </span>
            <span>•</span>
            <span>
              Prod: <code className="font-mono text-slate-300">{event.prodId}</code>
            </span>
            <span>•</span>
            <time className="font-mono text-slate-500">{event.timestampUtc}</time>
          </div>

          {event.errorMessage && (
            <p className="mt-1 flex items-center gap-1 text-[11px] text-rose-400">
              <AlertTriangle className="h-3 w-3 shrink-0" />
              {event.errorMessage}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 self-end sm:self-center">
        {event.runId && (
          <a
            href={`#${event.runId}`}
            className="flex items-center gap-1 text-[11px] font-mono text-sky-400 hover:text-sky-300 hover:underline"
            title="Inspect Agentic Clearance Run"
          >
            <span>{event.runId}</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        )}

        <span
          className={`rounded border px-2 py-0.5 text-[10px] font-semibold tracking-wide ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
        >
          {badgeStyle.label}
        </span>
      </div>
    </div>
  );
};
