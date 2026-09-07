'use client';

/**
 * Lienmark HITL Waiting For Information Badge
 * Pulsing amber status indicator for claims with active human-in-the-loop clarifications.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { HelpCircle } from 'lucide-react';

export interface ClarificationBadgeProps {
  readonly onClick?: () => void;
  readonly isInteractive?: boolean;
  readonly className?: string;
}

export const ClarificationBadge: React.FC<ClarificationBadgeProps> = ({
  onClick,
  isInteractive = false,
  className = '',
}) => {
  const badgeClasses = `inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold font-mono text-amber-200 bg-amber-950/90 border border-amber-500/80 shadow-md animate-pulse ${
    isInteractive
      ? 'cursor-pointer hover:bg-amber-900 hover:border-amber-400 focus:outline-none focus:ring-1 focus:ring-amber-400 transition-colors'
      : ''
  } ${className}`;

  if (isInteractive && onClick) {
    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        className={badgeClasses}
        title="Active HITL Clarification Pending: Click to inspect or submit response"
        aria-label="Active HITL Clarification: Waiting For Info. Click to open modal."
      >
        <HelpCircle className="h-3 w-3 text-amber-400 flex-shrink-0" aria-hidden="true" />
        <span>[WAITING FOR INFO]</span>
      </button>
    );
  }

  return (
    <span
      className={badgeClasses}
      title="Clearance Gated: Waiting for human-in-the-loop clarification"
      aria-label="Status: Waiting For Information"
    >
      <HelpCircle className="h-3 w-3 text-amber-400 flex-shrink-0" aria-hidden="true" />
      <span>[WAITING FOR INFO]</span>
    </span>
  );
};

export default ClarificationBadge;
