'use client';

/**
 * GcsPathPreview Component
 * Displays the live canonical GCS target path with copy button and validation badge.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import type { GcsTargetValidation } from './types';

interface GcsPathPreviewProps {
  uri: string;
  validation: GcsTargetValidation;
}

export const GcsPathPreview: React.FC<GcsPathPreviewProps> = ({ uri, validation }) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(uri);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/60 p-3">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
          Cloud Storage Target Path
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-mono border ${
            validation.isValid
              ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-300'
              : 'border-slate-700 bg-slate-800 text-slate-400'
          }`}
        >
          {validation.isValid ? 'Schema Valid' : 'Incomplete Path'}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2">
        <code className="text-xs text-sky-300 font-mono break-all">{uri}</code>
        <button
          onClick={handleCopy}
          className="p-1 text-slate-400 hover:text-slate-200 shrink-0"
          title="Copy GCS URI"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  );
};
