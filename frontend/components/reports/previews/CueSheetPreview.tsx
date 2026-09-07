'use client';

/**
 * CueSheetPreview Component
 * Standardized ASCAP/BMI/SESAC Music Cue Sheet Tabular View.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { Music, Clock, Disc3, ShieldCheck, Radio } from 'lucide-react';
import { CueSheetResponse, CueSheetEntry, CueUsageType } from '../types';

interface CueSheetPreviewProps {
  readonly cueSheet: CueSheetResponse;
}

function formatDuration(totalSeconds: number): string {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}m ${secs.toString().padStart(2, '0')}s`;
}

function getUsageBadgeClass(usage: CueUsageType): string {
  switch (usage) {
    case 'VV':
    case 'VI':
      return 'bg-purple-500/20 border-purple-500/40 text-purple-300';
    case 'MT':
    case 'ET':
      return 'bg-amber-500/20 border-amber-500/40 text-amber-300';
    case 'BV':
      return 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300';
    case 'BI':
    case 'BG':
    default:
      return 'bg-sky-500/20 border-sky-500/40 text-sky-300';
  }
}

function renderCueHeader(cueSheet: CueSheetResponse): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800/80 pb-4">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Music className="h-5 w-5 text-purple-400" />
          <h3 className="text-base font-bold text-white tracking-tight">
            ASCAP / BMI / SESAC MASTER MUSIC CUE SHEET
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Standard RapidCue Specification • Performing Rights Organizations Filing Schedule
        </p>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 text-xs font-mono text-slate-300">
          <Clock className="h-3.5 w-3.5 text-sky-400" />
          <span>Total: {formatDuration(cueSheet.total_duration_seconds)}</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-lg bg-slate-900 border border-slate-800 px-3 py-1.5 text-xs font-mono text-purple-300">
          <Disc3 className="h-3.5 w-3.5 text-purple-400" />
          <span>{cueSheet.total_cues} Cues</span>
        </div>
      </div>
    </div>
  );
}

function renderCredits(entry: CueSheetEntry): React.JSX.Element {
  return (
    <div className="space-y-1 text-[11px] font-mono">
      <div className="text-slate-300">
        <span className="text-slate-500 text-[10px] block">COMPOSER(S):</span>
        {entry.composers.map((c, i) => (
          <span key={i} className="block text-slate-200">
            {c.name} <span className="text-sky-400">({c.pro} {c.split_percentage}%)</span>
          </span>
        ))}
      </div>
      <div className="text-slate-300 pt-0.5">
        <span className="text-slate-500 text-[10px] block">PUBLISHER(S):</span>
        {entry.publishers.map((p, i) => (
          <span key={i} className="block text-slate-400">
            {p.name} <span className="text-purple-400">({p.pro} {p.split_percentage}%)</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function renderCueRow(entry: CueSheetEntry): React.JSX.Element {
  return (
    <tr
      key={entry.cue_number}
      className="border-b border-slate-800/60 hover:bg-slate-900/40 transition-colors text-xs"
    >
      <td className="py-3 px-3 font-mono font-bold text-slate-400 text-center">
        {entry.cue_number}
      </td>
      <td className="py-3 px-3 space-y-1">
        <div className="font-bold text-white tracking-tight">{entry.title}</div>
        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
          {entry.scene && <span className="text-slate-400">Scene: {entry.scene}</span>}
          {entry.record_label && (
            <span className="text-slate-500 truncate">Label: {entry.record_label}</span>
          )}
        </div>
      </td>
      <td className="py-3 px-3">
        <span
          className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getUsageBadgeClass(
            entry.usage
          )}`}
        >
          {entry.usage}
        </span>
      </td>
      <td className="py-3 px-3 font-mono text-[11px] text-slate-300 whitespace-nowrap">
        <div>{entry.timecode_in}</div>
        <div className="text-slate-500">{entry.timecode_out} ({entry.duration_seconds}s)</div>
      </td>
      <td className="py-3 px-3">{renderCredits(entry)}</td>
      <td className="py-3 px-3 font-mono text-[11px] text-slate-400">
        <div>{entry.pro_work_id || 'PENDING'}</div>
        <div className="text-[10px] text-emerald-400 flex items-center gap-1 mt-1">
          <ShieldCheck className="h-3 w-3" />
          <span>{entry.status}</span>
        </div>
      </td>
    </tr>
  );
}

export function CueSheetPreview({ cueSheet }: CueSheetPreviewProps): React.JSX.Element {
  return (
    <div className="space-y-4 text-slate-200">
      <div className="rounded-2xl border border-slate-800 bg-[#0B0F17] p-5 shadow-2xl space-y-4">
        {renderCueHeader(cueSheet)}

        <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] font-mono uppercase text-slate-400 bg-slate-900/80">
                <th className="py-2.5 px-3 text-center">Cue #</th>
                <th className="py-2.5 px-3">Work Title &amp; Scene</th>
                <th className="py-2.5 px-3">Usage</th>
                <th className="py-2.5 px-3">Timecode (In/Out)</th>
                <th className="py-2.5 px-3">Composers &amp; Publishers</th>
                <th className="py-2.5 px-3">PRO Work ID / Clearance</th>
              </tr>
            </thead>
            <tbody>
              {cueSheet.cues.map((c) => renderCueRow(c))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
