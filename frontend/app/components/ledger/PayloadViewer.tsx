'use client';

/**
 * PayloadViewer Component
 * Collapsible raw JSON payload viewer for cryptographic audit events with click-to-copy.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Code, Copy, Check } from 'lucide-react';

export interface PayloadViewerProps {
  payload: string;
  copiedHash: string | null;
  onCopy: (content: string) => void;
  className?: string;
}

export const PayloadViewer: React.FC<PayloadViewerProps> = ({
  payload,
  copiedHash,
  onCopy,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const isCopied = copiedHash === payload;

  return (
    <div className={`border-t border-slate-800/80 pt-2 ${className}`}>
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="inline-flex items-center gap-1.5 text-[11px] font-mono text-slate-400 hover:text-sky-400 transition-colors focus:outline-none"
        aria-expanded={isExpanded}
      >
        <Code className="h-3.5 w-3.5" />
        {isExpanded ? (
          <>
            <ChevronDown className="h-3.5 w-3.5" />
            <span>Hide Payload JSON</span>
          </>
        ) : (
          <>
            <ChevronRight className="h-3.5 w-3.5" />
            <span>View Raw Payload JSON</span>
          </>
        )}
      </button>

      {isExpanded && (
        <div className="mt-2 relative rounded-lg bg-slate-950 p-3 border border-slate-800 max-h-56 overflow-y-auto">
          <button
            type="button"
            onClick={() => onCopy(payload)}
            className="absolute top-2 right-2 p-1.5 rounded bg-slate-900 text-slate-400 hover:text-white border border-slate-800 text-[10px] font-mono flex items-center gap-1"
            title="Copy Raw JSON"
            aria-label="Copy JSON payload"
          >
            {isCopied ? (
              <>
                <Check className="h-3 w-3 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copy JSON</span>
              </>
            )}
          </button>
          <pre className="text-[10px] font-mono text-emerald-300/90 whitespace-pre-wrap leading-relaxed pr-16">
            {payload}
          </pre>
        </div>
      )}
    </div>
  );
};

export default PayloadViewer;
