'use client';

/**
 * Lienmark HITL Clarification Modal Header
 * Header with asset category icon, scene/timecode badge, assigned role indicator, and close button.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  X,
  Clock,
  Palette,
  Music,
  Film,
  Tag,
  FileCheck,
} from 'lucide-react';
import { QuestionCategory, ClarificationRequestUI } from './hitl_types';
import { getRoleBadgeStyle, getCategoryBadgeStyle } from './hitl_utils';

export interface ClarificationModalHeaderProps {
  readonly request: ClarificationRequestUI;
  readonly onClose: () => void;
  readonly isSubmitting?: boolean;
}

export function renderCategoryHeaderIcon(category: QuestionCategory) {
  switch (category) {
    case QuestionCategory.CHAIN_OF_TITLE:
      return <FileCheck className="h-4 w-4 text-emerald-400" aria-hidden="true" />;
    case QuestionCategory.MUSIC_RIGHTS:
      return <Music className="h-4 w-4 text-indigo-400" aria-hidden="true" />;
    case QuestionCategory.TRADEMARK_BRAND:
      return <Tag className="h-4 w-4 text-cyan-400" aria-hidden="true" />;
    case QuestionCategory.PROPRIETARY_DESIGN:
      return <Palette className="h-4 w-4 text-pink-400" aria-hidden="true" />;
    default:
      return <Film className="h-4 w-4 text-slate-400" aria-hidden="true" />;
  }
}

export const ClarificationModalHeader: React.FC<ClarificationModalHeaderProps> = ({
  request,
  onClose,
  isSubmitting = false,
}) => {
  const roleStyle = getRoleBadgeStyle(request.assignedRole);
  const categoryStyle = getCategoryBadgeStyle(request.category);

  return (
    <div className="flex items-start justify-between border-b border-slate-800 pb-4">
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/90 px-2.5 py-1 text-xs font-mono font-bold text-white shadow-sm">
            {renderCategoryHeaderIcon(request.category)}
            <span>{categoryStyle.label}</span>
          </span>
          <span className="inline-flex items-center gap-1 rounded border border-amber-500/40 bg-amber-950/40 px-2 py-0.5 text-xs font-mono font-bold text-amber-300">
            <Clock className="h-3 w-3 text-amber-400" aria-hidden="true" />
            <span>{request.scene}</span>
          </span>
          <span
            className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-mono font-bold ${roleStyle.bgClass} ${roleStyle.textClass} ${roleStyle.borderClass}`}
          >
            <span>Role: {roleStyle.label}</span>
          </span>
        </div>
        <h2 id="clarification-modal-title" className="text-lg font-bold text-white tracking-tight">
          Clarification Request: {request.assetName}
        </h2>
      </div>
      <button
        type="button"
        onClick={onClose}
        disabled={isSubmitting}
        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-sky-400"
        aria-label="Close clarification modal"
      >
        <X className="h-5 w-5" aria-hidden="true" />
      </button>
    </div>
  );
};

export default ClarificationModalHeader;
