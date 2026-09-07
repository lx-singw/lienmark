'use client';

/**
 * UploadProgressCard Component
 * Displays the upload progress bar and Eventarc success feedback banner.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';
import type { UploadState } from './useDropzoneUpload';

interface UploadProgressCardProps {
  uploadState: UploadState;
  progress: number;
  statusMessage: string;
  runId: string | null;
}

export const UploadProgressCard: React.FC<UploadProgressCardProps> = ({
  uploadState,
  progress,
  statusMessage,
  runId,
}) => {
  if (uploadState === 'idle' || uploadState === 'error') return null;

  if (uploadState === 'uploading') {
    return (
      <div className="mt-4 space-y-2">
        <div className="flex justify-between text-xs text-slate-300">
          <span className="flex items-center gap-1.5">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-400" />
            {statusMessage}
          </span>
          <span className="font-mono">{progress}%</span>
        </div>
        <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-sky-500 to-emerald-400 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-emerald-500/40 bg-emerald-950/30 p-3 text-xs text-emerald-200">
      <div className="flex items-center gap-2 font-medium">
        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        <span>Eventarc Ingestion Dispatched</span>
      </div>
      <p className="mt-1 text-[11px] text-emerald-300/80 font-mono">
        Triggered Run ID: {runId}
      </p>
    </div>
  );
};
