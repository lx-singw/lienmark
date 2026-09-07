'use client';

/**
 * SourceCitation.tsx
 * Interactive citation chip for grounded clearance research evidence.
 * Displays domain favicon, title, excerpt tooltip, authority tier badge, and safe external link.
 * Sprint 3.1: Parallel Search Integration & Query Optimization Engine.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useId, useRef, useEffect, useCallback } from 'react';
import {
  ExternalLink,
  ShieldCheck,
  Building2,
  Globe,
  Quote,
  Clock,
} from 'lucide-react';
import {
  DomainAuthorityTier,
  type SearchFinding,
} from './types';
import {
  extractDomain,
  sanitizeUrl,
  getAuthorityBadgeStyle,
} from './research_utils';

export interface SourceCitationProps {
  readonly finding?: SearchFinding;
  readonly url?: string;
  readonly title?: string;
  readonly snippet?: string;
  readonly tier?: DomainAuthorityTier;
  readonly timestampUtc?: string;
  readonly compact?: boolean;
  readonly className?: string;
}

function renderTierIcon(iconName: string): React.ReactElement {
  switch (iconName) {
    case 'ShieldCheck':
      return <ShieldCheck className="w-3.5 h-3.5 text-amber-400 shrink-0" />;
    case 'Building2':
      return <Building2 className="w-3.5 h-3.5 text-sky-400 shrink-0" />;
    case 'Globe':
    default:
      return <Globe className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
  }
}

export const SourceCitation: React.FC<SourceCitationProps> = ({
  finding,
  url: propUrl,
  title: propTitle,
  snippet: propSnippet,
  tier: propTier,
  timestampUtc: propTimestamp,
  compact = false,
  className = '',
}) => {
  const url = finding?.source_url ?? propUrl ?? '';
  const title = finding?.source_title ?? propTitle ?? 'Clearance Citation';
  const snippet = finding?.source_snippet ?? propSnippet ?? '';
  const tier = finding?.domain_authority_tier ?? propTier ?? DomainAuthorityTier.TIER_3_WEB;
  const timestamp = finding?.retrieval_timestamp_utc ?? propTimestamp ?? '';

  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [imgError, setImgError] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipId = useId();

  const domain = extractDomain(url);
  const safeHref = sanitizeUrl(url);
  const badgeStyle = getAuthorityBadgeStyle(tier);
  const faviconUrl = domain && !imgError
    ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=32`
    : null;

  const handleClose = useCallback(() => setIsOpen(false), []);
  const handleToggle = useCallback(() => setIsOpen((prev) => !prev), []);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [isOpen]);

  return (
    <div
      ref={containerRef}
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={handleClose}
    >
      <div
        role="button"
        tabIndex={0}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-describedby={isOpen ? tooltipId : undefined}
        onClick={handleToggle}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleToggle();
          }
          if (e.key === 'Escape') handleClose();
        }}
        className={`group inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium cursor-pointer transition-all duration-200 border ${badgeStyle.bg} ${badgeStyle.border} ${badgeStyle.text} hover:scale-[1.02] hover:shadow-md focus:outline-none focus:ring-2 focus:ring-cyan-500/50`}
      >
        {faviconUrl ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={faviconUrl}
            alt=""
            width={14}
            height={14}
            onError={() => setImgError(true)}
            className="w-3.5 h-3.5 rounded-full object-contain shrink-0"
          />
        ) : (
          renderTierIcon(badgeStyle.iconName)
        )}
        <span className="truncate max-w-[140px] md:max-w-[180px] font-semibold">
          {domain || title}
        </span>
        {!compact && (
          <span className="text-[10px] uppercase font-bold tracking-wider opacity-80 pl-1">
            {badgeStyle.shortLabel}
          </span>
        )}
        {safeHref && (
          <ExternalLink className="w-3 h-3 opacity-60 group-hover:opacity-100 shrink-0 ml-0.5" />
        )}
      </div>

      {isOpen && (
        <div
          id={tooltipId}
          role="dialog"
          aria-label="Citation Details"
          className="absolute z-50 bottom-full left-0 mb-2 w-80 max-w-[90vw] p-3 rounded-xl bg-cinema-navy/95 border border-slate-700/80 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
            <span
              className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${badgeStyle.bg} ${badgeStyle.border} ${badgeStyle.text}`}
            >
              {renderTierIcon(badgeStyle.iconName)}
              <span>{badgeStyle.label}</span>
            </span>
            {timestamp && (
              <span className="flex items-center text-[10px] text-slate-400 space-x-1">
                <Clock className="w-3 h-3 text-slate-500" />
                <span>{timestamp.slice(0, 16).replace('T', ' ')} UTC</span>
              </span>
            )}
          </div>

          <h4 className="text-xs font-bold text-slate-100 mb-1.5 leading-snug line-clamp-2">
            {title}
          </h4>

          {snippet && (
            <div className="relative pl-3 py-1.5 mb-2 bg-cinema-black/70 rounded-md border-l-2 border-cyan-500/80 text-[11px] text-slate-300 italic leading-relaxed">
              <Quote className="w-3 h-3 text-cyan-400/50 absolute top-1 left-0.5 -translate-x-1/2" />
              <p className="line-clamp-4">{snippet}</p>
            </div>
          )}

          <div className="flex items-center justify-between pt-1 text-[11px]">
            <span className="text-slate-400 truncate max-w-[170px]" title={domain}>
              {domain}
            </span>
            {safeHref ? (
              <a
                href={safeHref}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-1 text-cyan-400 hover:text-cyan-300 font-medium hover:underline focus:outline-none"
              >
                <span>Verify Source</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            ) : (
              <span className="text-slate-500 italic">No external link</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SourceCitation;
