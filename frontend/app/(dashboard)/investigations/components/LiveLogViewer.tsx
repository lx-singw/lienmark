'use client';

/**
 * LiveLogViewer Component
 * Terminal-styled live SSE log stream listener with filter controls and auto-scroll.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Trash2, ArrowDown, Search, Radio } from 'lucide-react';
import { DashboardEvent, StreamConnectionStatus } from '@/hooks/useDashboardEvents';

interface LiveLogViewerProps {
  readonly events: ReadonlyArray<DashboardEvent>;
  readonly status: StreamConnectionStatus;
  readonly onClear: () => void;
}

export const LiveLogViewer: React.FC<LiveLogViewerProps> = ({ events, status, onClear }) => {
  const [filterQuery, setFilterQuery] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, autoScroll]);

  const filtered = events.filter(
    (e) => !filterQuery || (e.message || '').toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div className="rounded-2xl border border-slate-800 bg-[#050811] shadow-2xl flex flex-col h-[520px] overflow-hidden">
      {/* Terminal Titlebar */}
      <div className="flex items-center justify-between border-b border-slate-800/80 bg-slate-950/80 px-4 py-2.5 text-xs text-slate-300">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-sky-400" />
          <span className="font-mono font-semibold">Live SSE Agent Log Stream</span>
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-mono ${
            status === 'connected'
              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
          }`}>
            <Radio className="h-2.5 w-2.5 animate-pulse" />
            {status}
          </span>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-2 top-2 h-3 w-3 text-slate-500" />
            <input
              type="text"
              placeholder="Filter logs..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="rounded-lg bg-slate-900 border border-slate-800 pl-7 pr-2 py-1 text-[11px] text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500/40"
            />
          </div>
          <button
            type="button"
            onClick={() => setAutoScroll((prev) => !prev)}
            className={`flex items-center gap-1 rounded px-2 py-1 text-[11px] font-mono border transition-colors ${
              autoScroll
                ? 'border-sky-500/40 bg-sky-950/40 text-sky-300'
                : 'border-slate-800 bg-slate-900 text-slate-400'
            }`}
          >
            <ArrowDown className="h-3 w-3" /> Auto-Scroll
          </button>
          <button
            type="button"
            onClick={onClear}
            className="rounded p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Clear Stream"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Log Output Body */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1.5 selection:bg-sky-500/30">
        {filtered.length === 0 ? (
          <div className="text-slate-600 italic text-center pt-24">
            [Stream initialized. Awaiting autonomous agent execution telemetry...]
          </div>
        ) : (
          filtered.map((evt) => (
            <div key={evt.id} className="flex items-start gap-2 leading-relaxed">
              <span className="text-slate-500 select-none text-[11px] flex-shrink-0">
                {new Date(evt.timestamp).toLocaleTimeString()}
              </span>
              <span className="text-sky-400 select-none text-[11px] font-bold flex-shrink-0">
                [{evt.type.toUpperCase()}]
              </span>
              <span className="text-slate-200 break-all">{evt.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default LiveLogViewer;
