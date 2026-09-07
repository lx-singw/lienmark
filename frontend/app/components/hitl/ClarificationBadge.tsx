'use client';

/**
 * Lienmark HITL Clearance & Resumption Status Badge
 * Renders high-visibility studio status badges with animated transitions:
 * - [WAITING FOR INFO] (pulsing amber)
 * - [AGREEMENT MATCHED] (glowing emerald)
 * - [READY FOR REVIEW] (glowing teal/cyan)
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { HelpCircle, FileCheck, ShieldCheck } from 'lucide-react';
import { ClaimResumptionStatus } from './resumption_types';
import { getResumptionBadgeTheme } from './resumption_utils';

export interface ClarificationBadgeProps {
  readonly status?: ClaimResumptionStatus;
  readonly onClick?: () => void;
  readonly isInteractive?: boolean;
  readonly className?: string;
}

function renderBadgeIcon(iconName: 'help' | 'match' | 'shield'): React.ReactElement {
  switch (iconName) {
    case 'match':
      return <FileCheck className="h-3 w-3 text-emerald-400 flex-shrink-0 animate-pulse" aria-hidden="true" />;
    case 'shield':
      return <ShieldCheck className="h-3 w-3 text-teal-300 flex-shrink-0" aria-hidden="true" />;
    case 'help':
    default:
      return <HelpCircle className="h-3 w-3 text-amber-400 flex-shrink-0" aria-hidden="true" />;
  }
}

export const ClarificationBadge: React.FC<ClarificationBadgeProps> = ({
  status = ClaimResumptionStatus.WAITING_FOR_INFO,
  onClick,
  isInteractive = false,
  className = '',
}) => {
  const theme = getResumptionBadgeTheme(status);

  const badgeClasses = `inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold font-mono border transition-all duration-300 ${theme.badgeClass} ${
    isInteractive
      ? 'cursor-pointer hover:scale-105 hover:brightness-110 focus:outline-none focus:ring-1 focus:ring-emerald-400'
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
        title={`Status: ${theme.label}. Click to inspect details or take action.`}
        aria-label={`Status: ${theme.label}. Click to inspect.`}
      >
        {renderBadgeIcon(theme.iconName)}
        <span>{theme.label}</span>
      </button>
    );
  }

  return (
    <span
      className={badgeClasses}
      title={`Clearance Status: ${theme.label}`}
      aria-label={`Status: ${theme.label}`}
    >
      {renderBadgeIcon(theme.iconName)}
      <span>{theme.label}</span>
    </span>
  );
};

export default ClarificationBadge;
