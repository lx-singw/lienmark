'use client';

/**
 * QuerySyntaxHighlighter.tsx
 * Real-time syntax highlighting for Parallel Search API queries.
 * Highlights site: filters, negative exclusions, exact quotes, and logical operators.
 * Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useCallback } from 'react';
import { Copy, Check, Terminal } from 'lucide-react';
import { tokenizeQueryString } from './research_utils';
import { QueryTokenType, type QueryToken } from './types';

export interface QuerySyntaxHighlighterProps {
  readonly queryString: string;
  readonly showCopyButton?: boolean;
  readonly className?: string;
}

interface TokenStyleConfig {
  readonly className: string;
  readonly format?: (t: QueryToken) => React.ReactNode;
}

const TOKEN_STYLES: Record<QueryTokenType, TokenStyleConfig> = {
  [QueryTokenType.SITE]: {
    className:
      'px-1.5 py-0.5 rounded bg-cyan-950/70 text-cyan-300 font-semibold border border-cyan-500/30',
  },
  [QueryTokenType.NEGATIVE]: {
    className:
      'px-1.5 py-0.5 rounded bg-rose-950/70 text-rose-300 font-semibold border border-rose-500/30',
  },
  [QueryTokenType.QUOTE]: {
    className:
      'px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-300 font-medium border border-amber-500/30',
    format: (t: QueryToken) => <>"{t.value}"</>,
  },
  [QueryTokenType.OPERATOR]: {
    className: 'px-1 py-0.5 text-purple-400 font-bold uppercase',
  },
  [QueryTokenType.TERM]: {
    className: 'text-slate-200',
  },
};

function renderTokenBadge(token: QueryToken, index: number): React.ReactElement {
  const config = TOKEN_STYLES[token.type] ?? TOKEN_STYLES[QueryTokenType.TERM];
  const content = config.format ? config.format(token) : token.raw;
  return (
    <span key={`token-${index}-${token.type}`} className={config.className}>
      {content}
    </span>
  );
}

interface HeaderProps {
  readonly showCopyButton: boolean;
  readonly copied: boolean;
  readonly onCopy: () => void;
}

const HighlighterHeader: React.FC<HeaderProps> = ({
  showCopyButton,
  copied,
  onCopy,
}) => (
  <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800/80 text-xs text-slate-400">
    <div className="flex items-center space-x-1.5">
      <Terminal className="w-3.5 h-3.5 text-cyan-400" />
      <span className="font-semibold uppercase tracking-wider text-[10px]">
        Targeted Query Syntax
      </span>
    </div>
    {showCopyButton && (
      <button
        type="button"
        onClick={onCopy}
        title="Copy query string"
        className="flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] text-slate-400 hover:text-slate-200 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 transition-colors"
      >
        {copied ? (
          <>
            <Check className="w-3 h-3 text-emerald-400" />
            <span className="text-emerald-400">Copied</span>
          </>
        ) : (
          <>
            <Copy className="w-3 h-3" />
            <span>Copy</span>
          </>
        )}
      </button>
    )}
  </div>
);

export const QuerySyntaxHighlighter: React.FC<QuerySyntaxHighlighterProps> = ({
  queryString,
  showCopyButton = true,
  className = '',
}) => {
  const [copied, setCopied] = useState<boolean>(false);
  const tokens = React.useMemo(
    () => tokenizeQueryString(queryString),
    [queryString]
  );

  const handleCopy = useCallback(() => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(queryString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [queryString]);

  return (
    <div
      className={`relative rounded-lg bg-cinema-black/90 border border-slate-800 p-3 font-mono text-sm shadow-inner ${className}`}
    >
      <HighlighterHeader
        showCopyButton={showCopyButton}
        copied={copied}
        onCopy={handleCopy}
      />
      <div className="flex flex-wrap items-center gap-1.5 select-all leading-relaxed">
        {tokens.length > 0 ? (
          tokens.map((token, idx) => renderTokenBadge(token, idx))
        ) : (
          <span className="text-slate-500 italic">No query provided</span>
        )}
      </div>
    </div>
  );
};

export default QuerySyntaxHighlighter;
