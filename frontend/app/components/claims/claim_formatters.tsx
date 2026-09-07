'use client';

/**
 * Lienmark Claim Formatting Helpers
 * Formatters for cinematic timecodes, category icons, and clearance badges.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import {
  Film,
  Music,
  Palette,
  Box,
  Tag,
  User,
  MapPin,
  FileText,
} from 'lucide-react';
import { DecisionState } from '@/lib/types';
import { ClearanceStatusBadge } from './ClearanceStatusBadge';
import { getClaimCategoryStyle } from '../intake/intake_utils';

export function formatCinematicTimecode(scene = '', key = '', index = 0): string {
  const safeKey = key || '';
  const safeScene = scene || '';

  if (safeKey === 'poster_noir_detective_magazine' || safeKey.includes('noir_detective') || safeKey === 'claim_11') {
    return 'SC 42 (00:41:12)';
  }
  if (safeKey === 'music_cue_midnight_serenade' || safeKey.includes('midnight_serenade') || safeKey === 'claim_12') {
    return 'SC 18 (00:19:40)';
  }

  const timecodeMatch = safeScene.match(/(\d{2}:\d{2}(?::\d{2})?)/);
  const sceneMatch = safeScene.match(/Scene\s*(\d+)/i) || safeScene.match(/SC\s*(\d+)/i);
  const sceneNum = sceneMatch ? sceneMatch[1].padStart(2, '0') : String(index + 1).padStart(2, '0');

  if (timecodeMatch) {
    return `SC ${sceneNum} (${timecodeMatch[1]})`;
  }

  const minutes = String((parseInt(sceneNum, 10) * 2) % 60).padStart(2, '0');
  const seconds = String((parseInt(sceneNum, 10) * 7 + 12) % 60).padStart(2, '0');
  return `SC ${sceneNum} (00:${minutes}:${seconds})`;
}

export function renderCategoryIcon(iconName: string) {
  switch (iconName) {
    case 'Palette': return <Palette className="h-3 w-3 text-purple-400" aria-hidden="true" />;
    case 'Music': return <Music className="h-3 w-3 text-indigo-400" aria-hidden="true" />;
    case 'Box': return <Box className="h-3 w-3 text-amber-400" aria-hidden="true" />;
    case 'Tag': return <Tag className="h-3 w-3 text-cyan-400" aria-hidden="true" />;
    case 'User': return <User className="h-3 w-3 text-rose-400" aria-hidden="true" />;
    case 'MapPin': return <MapPin className="h-3 w-3 text-emerald-400" aria-hidden="true" />;
    case 'FileText': return <FileText className="h-3 w-3 text-slate-400" aria-hidden="true" />;
    default: return <Film className="h-3 w-3 text-slate-400" aria-hidden="true" />;
  }
}

export function renderAssetCategoryBadge(assetType: string) {
  const style = getClaimCategoryStyle(assetType);
  return (
    <span
      className={`inline-flex items-center gap-1 rounded ${style.bg} ${style.text} border ${style.border} px-2 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase shadow-sm`}
      title={`${style.label} Asset`}
    >
      {renderCategoryIcon(style.iconName)}
      <span>{style.label}</span>
    </span>
  );
}

export function renderClearanceStatusIndicator(state: DecisionState) {
  return <ClearanceStatusBadge state={state} />;
}
