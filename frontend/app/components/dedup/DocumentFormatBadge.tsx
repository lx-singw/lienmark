/**
 * DocumentFormatBadge.tsx
 * Compact badge displaying screenplay / timeline formats and structural metadata.
 * Supports PDF, Final Draft (FDX), Fountain, CMX 3600 EDL, and plain text.
 * Sprint 2.2: Content Digesting, Deduplication & Rename Invariance.
 */

import React from 'react';
import {
  FileText,
  FileCode,
  PenTool,
  Film,
  AlignLeft,
  FileQuestion,
} from 'lucide-react';
import type { DocumentFormatBadgeProps } from './types';
import { getFormatBadgeStyle } from './dedup_utils';

function renderFormatIcon(iconName: string): React.ReactElement {
  const iconProps = { className: 'h-3.5 w-3.5 shrink-0' };
  switch (iconName) {
    case 'FileText':
      return <FileText {...iconProps} />;
    case 'FileCode':
      return <FileCode {...iconProps} />;
    case 'PenTool':
      return <PenTool {...iconProps} />;
    case 'Film':
      return <Film {...iconProps} />;
    case 'AlignLeft':
      return <AlignLeft {...iconProps} />;
    default:
      return <FileQuestion {...iconProps} />;
  }
}

interface MetadataTagsProps {
  pageCount?: number;
  sceneCount?: number;
  frameRate?: number;
}

const MetadataTags: React.FC<MetadataTagsProps> = ({
  pageCount,
  sceneCount,
  frameRate,
}) => {
  const hasMetadata =
    pageCount !== undefined || sceneCount !== undefined || frameRate !== undefined;

  if (!hasMetadata) return null;

  return (
    <span className="flex items-center gap-1.5 border-l border-current/20 pl-2 text-[11px] opacity-90 font-mono">
      {pageCount !== undefined && (
        <span>{pageCount} {pageCount === 1 ? 'page' : 'pages'}</span>
      )}
      {sceneCount !== undefined && (
        <span>{sceneCount} {sceneCount === 1 ? 'scene' : 'scenes'}</span>
      )}
      {frameRate !== undefined && (
        <span>{frameRate} fps</span>
      )}
    </span>
  );
};

export const DocumentFormatBadge: React.FC<DocumentFormatBadgeProps> = ({
  format,
  pageCount,
  sceneCount,
  frameRate,
  className = '',
}) => {
  const style = getFormatBadgeStyle(format);

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${style.bg} ${style.text} ${style.border} ${className}`}
    >
      <span className="inline-flex items-center gap-1.5">
        {renderFormatIcon(style.iconName)}
        <span className="font-semibold tracking-wide">{style.label}</span>
      </span>
      <MetadataTags
        pageCount={pageCount}
        sceneCount={sceneCount}
        frameRate={frameRate}
      />
    </div>
  );
};
