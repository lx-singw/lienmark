'use client';

/**
 * Lienmark Investigations Page
 * Live investigation run monitor and real-time SSE log stream listener.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState } from 'react';
import { Compass, Play, RotateCcw, AlertOctagon } from 'lucide-react';
import { InvestigationRun } from './types';
import { RunSummaryCard } from './components/RunSummaryCard';
import { LiveLogViewer } from './components/LiveLogViewer';
import { useDashboardEvents, DashboardEvent } from '@/hooks/useDashboardEvents';

const RUNS: ReadonlyArray<InvestigationRun> = [
  {
    id: 'run_v8_drift_eval_001',
    name: 'Script Cut v8 Semantic Drift Evaluation',
    targetAsset: 'Locked Script Cut v7 &rarr; Revised Cut v8',
    status: 'running',
    startedAt: '2026-09-07T14:45:00.000Z',
    elapsedMs: 45000,
    modelUsed: 'Gemini 2.5 Flash',
    searchProvider: 'Parallel Search API v1',
    apiCallsCount: 8,
    spendUsd: 0.18,
  },
  {
    id: 'run_rights_poster_noir',
    name: 'Targeted LOC Copyright Verification',
    targetAsset: 'Poster: Noir Detective Magazine (Scene 42)',
    status: 'completed',
    startedAt: '2026-09-07T14:30:00.000Z',
    elapsedMs: 1240,
    modelUsed: 'Gemini 2.5 Flash',
    searchProvider: 'Parallel Search API v1',
    apiCallsCount: 2,
    spendUsd: 0.04,
  },
  {
    id: 'run_sync_midnight_serenade',
    name: 'Sync Rights Chain-of-Title Traversal',
    targetAsset: 'Music Cue: Midnight Serenade (Scene 18)',
    status: 'suspended',
    startedAt: '2026-09-07T14:15:00.000Z',
    elapsedMs: 2410,
    modelUsed: 'Gemini 2.5 Flash',
    searchProvider: 'Parallel Search API v1',
    apiCallsCount: 5,
    spendUsd: 0.12,
  },
];

export default function InvestigationsPage() {
  const [selectedRunId, setSelectedRunId] = useState<string>(RUNS[0].id);
  const { events, status, clearEvents } = useDashboardEvents();

  const selectedRun = RUNS.find((r) => r.id === selectedRunId) || RUNS[0];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-white">Live Investigation Monitor</h1>
            <span className="rounded-full bg-sky-500/20 border border-sky-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-sky-300">
              Active Stream
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time telemetry and SSE log streams for autonomous clearance research agents and DAG traversal.
          </p>
        </div>

        {/* Run Selector Buttons */}
        <div className="flex items-center gap-2">
          {RUNS.map((run) => (
            <button
              key={run.id}
              onClick={() => setSelectedRunId(run.id)}
              className={`rounded-xl px-3 py-1.5 text-xs font-mono transition-colors border ${
                selectedRunId === run.id
                  ? 'border-sky-500/50 bg-sky-950/40 text-sky-300'
                  : 'border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200'
              }`}
            >
              {run.id.slice(0, 14)}...
            </button>
          ))}
        </div>
      </div>

      {/* Selected Run Telemetry */}
      <RunSummaryCard run={selectedRun} />

      {/* Live SSE Stream Viewer */}
      <LiveLogViewer events={events} status={status} onClear={clearEvents} />
    </div>
  );
}
