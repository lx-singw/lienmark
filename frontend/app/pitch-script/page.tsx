'use client';

/**
 * Lienmark — Clearance Change Control for E&O
 * Master Pitch Script & Presenter Teleprompter Guide
 * Route: /pitch-script
 *
 * Authored for the Agentic Cinema Hackathon (Parallel Track & Core Cinema).
 * Implements full 165-second, 7-beat pitch script in cinema-dark (#0a0f1d) palette
 * with gold/cyan/emerald accents, teleprompter mode, copy-to-clipboard actions,
 * interactive beat filtering, second-by-second breakdown table, and statutory disclosures.
 */

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Download,
  FileText,
  ExternalLink,
  Copy,
  Check,
  Clock,
  Mic,
  Sparkles,
  ShieldCheck,
  Play,
  Film,
  Lock,
  Layers,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Compass,
  Zap,
  Info,
  ChevronRight,
  BookOpen,
} from 'lucide-react';
import { PITCH_BEATS, PitchBeatData } from '../components/DirectorsPresentationHud';

export default function PitchScriptPage() {
  const [selectedBeatId, setSelectedBeatId] = useState<number | 'all'>('all');
  const [copiedBeatId, setCopiedBeatId] = useState<number | null>(null);
  const [copiedFullScript, setCopiedFullScript] = useState<boolean>(false);
  const [largeText, setLargeText] = useState<boolean>(false);

  // Filtered beats based on selection
  const displayedBeats = useMemo(() => {
    if (selectedBeatId === 'all') {
      return PITCH_BEATS;
    }
    return PITCH_BEATS.filter((b) => b.id === selectedBeatId);
  }, [selectedBeatId]);

  // Copy individual beat narration
  const handleCopyBeat = async (beat: PitchBeatData) => {
    try {
      await navigator.clipboard.writeText(beat.teleprompterScript);
      setCopiedBeatId(beat.id);
      setTimeout(() => setCopiedBeatId(null), 2500);
    } catch {
      // Fallback
    }
  };

  // Copy entire pitch narration
  const handleCopyFullScript = async () => {
    try {
      const fullText = PITCH_BEATS.map(
        (b) => `--- Beat ${b.id}: ${b.title} (${b.timecode}) ---\nAction: ${b.actionCue}\n\n${b.teleprompterScript}\n`
      ).join('\n\n');
      await navigator.clipboard.writeText(fullText);
      setCopiedFullScript(true);
      setTimeout(() => setCopiedFullScript(false), 2500);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0f1d] text-slate-100 py-8 px-4 sm:px-6 lg:px-8 max-w-[1720px] mx-auto space-y-8">
      {/* Top Navigation & Action Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 px-3.5 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4 text-sky-400" />
            <span>Back to Clearance Dashboard</span>
          </Link>

          <Link
            href="/report/proj_blockbuster_cinema"
            className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 px-3.5 py-2 text-sm font-medium text-amber-300 hover:text-amber-200 transition-colors"
          >
            <FileText className="h-4 w-4 text-amber-400" />
            <span>View Form E&O-2026 Schedule</span>
          </Link>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Teleprompter Font Size Toggle */}
          <button
            type="button"
            onClick={() => setLargeText(!largeText)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
              largeText
                ? 'border-sky-500/50 bg-sky-500/20 text-sky-300'
                : 'border-slate-800 bg-slate-900/80 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle Large Presenter Typography"
          >
            <span className="font-mono font-bold text-sm">Aa</span>
            <span className="hidden md:inline">{largeText ? 'Normal Font' : 'Large Prompter'}</span>
          </button>

          {/* Copy Full Script Button */}
          <button
            type="button"
            onClick={handleCopyFullScript}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 hover:bg-slate-800 px-3 py-2 text-xs font-medium text-slate-300 hover:text-white transition-colors"
            title="Copy entire spoken pitch script to clipboard"
          >
            {copiedFullScript ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied Full Pitch!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5 text-slate-400" />
                <span>Copy Script</span>
              </>
            )}
          </button>

          {/* Download Raw Markdown Button */}
          <a
            href="/docs/pitch_script.md"
            download="pitch_script.md"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg border border-amber-500/40 bg-gradient-to-r from-amber-500/10 to-amber-600/20 hover:from-amber-500/20 hover:to-amber-600/30 px-3.5 py-2 text-xs font-semibold text-amber-300 transition-colors shadow-sm"
          >
            <Download className="h-3.5 w-3.5 text-amber-400" />
            <span>Download Raw Markdown</span>
            <ExternalLink className="h-3 w-3 opacity-60" />
          </a>
        </div>
      </div>

      {/* Hero Header & Teleprompter Specs */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br from-[#12182c] via-[#0d1326] to-[#0a0f1d] p-6 lg:p-8 shadow-2xl">
        <div className="relative z-10 space-y-4">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-500/40 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-300">
              <Film className="h-3.5 w-3.5 text-sky-400" />
              Agentic Cinema Track &middot; $15,000 Parallel Prize Pool
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300">
              <Clock className="h-3.5 w-3.5 text-amber-400" />
              Runtime: Exactly 165 Seconds (2:45)
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-300">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              Policy E&O-2026.1-DEVPOST
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/40 bg-purple-500/10 px-3 py-1 text-xs font-semibold text-purple-300">
              <Lock className="h-3.5 w-3.5 text-purple-400" />
              Conservation: 12 = 10 + 1 + 1 (12 &rarr; 10/2 &rarr; 1/1)
            </span>
          </div>

          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white">
              Master Pitch Script & Presenter Teleprompter Guide
            </h1>
            <p className="mt-2 text-sm sm:text-base text-slate-300 max-w-4xl leading-relaxed">
              Official word-for-word voiceover script, second-by-second technical invariant breakdown, and camera cues for the{' '}
              <strong className="text-white">Lienmark E&O Clearance Change Control</strong> demonstration video.
            </p>
          </div>

          {/* Teleprompter Pacing Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-3">
              <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Video Runtime</span>
              <span className="text-lg font-bold text-amber-400 font-mono">165s (2:45)</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">15s buffer to 3:00 hard limit</span>
            </div>
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-3">
              <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Total Word Count</span>
              <span className="text-lg font-bold text-sky-400 font-mono">348 Words</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Pacing: ~126 WPM</span>
            </div>
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-3">
              <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Lead Presenter</span>
              <span className="text-lg font-bold text-slate-200">Sarah Jenkins, Esq.</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Lead Production Counsel</span>
            </div>
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-3">
              <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Production Case</span>
              <span className="text-lg font-bold text-purple-400 truncate block">Shadows Over Broadway</span>
              <span className="text-[10px] font-mono text-slate-400 block mt-0.5">proj_blockbuster_cinema</span>
            </div>
          </div>
        </div>
      </div>

      {/* Presenter Directives Quick Callout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
          <div className="flex items-center gap-2 text-sky-400 text-sm font-bold">
            <Mic className="h-4 w-4" />
            <span>Vocal Tone & Cadence</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Speak crisply and authoritatively as senior entertainment clearance counsel. Respect all{' '}
            <code className="text-amber-400 bg-amber-950/40 px-1 py-0.5 rounded font-mono">[PAUSE 1.0s]</code> markers to let technical metrics land.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
          <div className="flex items-center gap-2 text-amber-400 text-sm font-bold">
            <Play className="h-4 w-4" />
            <span>Display & Recording Setup</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Record at 1080p 60fps with browser zoom at 110%. Enable yellow cursor highlight. Pre-seed baseline state via{' '}
            <code className="text-amber-300 bg-slate-800 px-1 py-0.5 rounded font-mono">python scripts/seed_demo_data.py</code>.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
          <div className="flex items-center gap-2 text-emerald-400 text-sm font-bold">
            <Layers className="h-4 w-4" />
            <span>Conservation Invariant</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Every scene reinforces the <strong className="text-emerald-300">$12 = 10 + 1 + 1$</strong> conservation law under the{' '}
            <strong className="text-emerald-300">12 &rarr; 10/2 &rarr; 1/1</strong> pipeline with 83.3% search query reduction.
          </p>
        </div>
      </div>

      {/* Beat Filter Navigation Pills */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Film className="h-4 w-4 text-sky-400" />
            <span>Select Pitch Beat</span>
          </h2>
          <span className="text-xs text-slate-400">
            Showing {selectedBeatId === 'all' ? 'All 7 Beats' : `Beat ${selectedBeatId}`}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setSelectedBeatId('all')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
              selectedBeatId === 'all'
                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/20'
                : 'border border-slate-800 bg-slate-900/80 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            All 7 Beats (165s)
          </button>

          {PITCH_BEATS.map((beat) => (
            <button
              type="button"
              key={beat.id}
              onClick={() => setSelectedBeatId(beat.id)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all flex items-center gap-1.5 ${
                selectedBeatId === beat.id
                  ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20 font-bold'
                  : 'border border-slate-800 bg-slate-900/80 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              <span className="font-mono text-[11px] opacity-75">{beat.timecode}</span>
              <span>Beat {beat.id}: {beat.shortTitle}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Pitch Beats Presentation Cards */}
      <div className="space-y-6">
        {displayedBeats.map((beat) => (
          <article
            key={beat.id}
            id={`beat-${beat.id}`}
            className={`rounded-2xl border transition-all duration-200 overflow-hidden bg-gradient-to-b from-[#10172a] to-[#0b1020] ${beat.accentColor.border} shadow-lg`}
          >
            {/* Beat Card Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 px-6 py-4 bg-slate-950/40">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-sm font-bold text-white">
                  {beat.id}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-white">{beat.title}</h2>
                    <span className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${beat.accentColor.badge}`}>
                      {beat.badgeText}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{beat.subtitle}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs font-mono text-amber-300">
                  <Clock className="h-3.5 w-3.5 text-amber-400" />
                  {beat.timecode} ({beat.durationSeconds}s)
                </span>

                <button
                  type="button"
                  onClick={() => handleCopyBeat(beat)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900 hover:bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:text-white transition-colors"
                  title="Copy this beat's spoken voiceover to clipboard"
                >
                  {copiedBeatId === beat.id ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400 font-semibold">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 text-slate-400" />
                      <span>Copy Beat</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Beat Content Grid */}
            <div className="p-6 space-y-6">
              {/* On-Screen Action Cue Banner */}
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3.5 flex items-start gap-3">
                <Film className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <div className="text-xs">
                  <span className="font-bold text-amber-400 uppercase tracking-wider mr-2">On-Screen Action:</span>
                  <span className="font-mono text-slate-300">{beat.actionCue}</span>
                </div>
              </div>

              {/* Spoken Teleprompter Narration */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-sky-400 flex items-center gap-1.5">
                    <Mic className="h-3.5 w-3.5 text-sky-400" />
                    <span>Spoken Voiceover Narration</span>
                  </span>
                  <span className="text-[11px] text-slate-400 italic">
                    Vocal Tone: {beat.vocalTone}
                  </span>
                </div>

                <div
                  className={`rounded-xl border border-slate-800/80 bg-[#070b16] p-5 shadow-inner leading-relaxed ${
                    largeText ? 'text-lg sm:text-xl font-medium' : 'text-sm sm:text-base font-normal'
                  } text-slate-100`}
                >
                  {beat.teleprompterScript.split('\n\n').map((paragraph, idx) => (
                    <p key={idx} className={idx > 0 ? 'mt-4' : ''}>
                      {paragraph.split(/(\*\*.*?\*\*|\[PAUSE 1\.0s\])/g).map((chunk, cIdx) => {
                        if (chunk.startsWith('**') && chunk.endsWith('**')) {
                          const text = chunk.slice(2, -2);
                          return (
                            <strong key={cIdx} className="text-amber-300 font-bold bg-amber-500/10 px-1 py-0.5 rounded">
                              {text}
                            </strong>
                          );
                        }
                        if (chunk === '[PAUSE 1.0s]') {
                          return (
                            <span
                              key={cIdx}
                              className="inline-flex items-center mx-1.5 rounded border border-amber-500/40 bg-amber-950/60 px-2 py-0.5 text-xs font-mono font-bold text-amber-300"
                            >
                              ⏸ PAUSE 1.0s
                            </span>
                          );
                        }
                        return chunk;
                      })}
                    </p>
                  ))}
                </div>
              </div>

              {/* Stress Words & Key Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Vocal Stress Words */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                    Vocal Emphasis Words
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {beat.stressWords.map((word, wIdx) => (
                      <span
                        key={wIdx}
                        className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-300"
                      >
                        &ldquo;{word}&rdquo;
                      </span>
                    ))}
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                    Telemetry & Metric Targets
                  </span>
                  <div className="grid grid-cols-2 gap-2">
                    {beat.keyMetrics.map((metric, mIdx) => (
                      <div key={mIdx} className="rounded-lg bg-slate-950/60 p-2 border border-slate-800/60">
                        <span className="text-[10px] text-slate-400 block">{metric.label}</span>
                        <span className="text-xs font-bold text-white font-mono">{metric.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Invariant Guarantee & Code Pointers */}
              <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-bold text-emerald-300">
                    {beat.invariantGuarantee}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/60">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <FileCode className="h-3.5 w-3.5 text-sky-400" />
                    <span>Backing Code Pointers:</span>
                  </span>
                  {beat.codePointers.map((ptr, pIdx) => (
                    <span
                      key={pIdx}
                      className="inline-flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-300"
                    >
                      <span className="text-sky-400">{ptr.file}</span>
                      {ptr.lineRef && <span className="text-amber-400">({ptr.lineRef})</span>}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>

      {/* Master Second-by-Second Breakdown Table Section */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-sky-400" />
              <span>Master Second-by-Second Timing & Invariant Matrix</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Synchronized mapping of timecode duration, visual UI action, voiceover narration, and backing technical invariants.
            </p>
          </div>
          <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-mono text-sky-300">
            Total: 165s / 2:45
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-3 w-28">Timecode</th>
                <th className="py-3 px-3 w-20">Dur.</th>
                <th className="py-3 px-3 w-48">Beat</th>
                <th className="py-3 px-3 min-w-[240px]">On-Screen Action & UI State</th>
                <th className="py-3 px-3 min-w-[280px]">Voiceover Narration</th>
                <th className="py-3 px-3 min-w-[200px]">Technical Invariant</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">0:00–0:08</td>
                <td className="py-3 px-3 font-mono">8s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 1: Problem Exposition</td>
                <td className="py-3 px-3 text-slate-300">Title card & 400-page physical binder beside video editor timeline</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;In film production, the hardest problem in rights clearance isn&apos;t finding a copyright record once...&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 1A: Drift exposition</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">0:08–0:15</td>
                <td className="py-3 px-3 font-mono">7s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 1: Clearance Crisis</td>
                <td className="py-3 px-3 text-slate-300">Red banner: $18,000 legal expense & 3-week delivery hold overlay</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;That silent divergence is clearance drift. Rescanning an entire binder wastes $18,000...&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 1B: Economic baseline</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">0:15–0:25</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 2: Version 7 Baseline</td>
                <td className="py-3 px-3 text-slate-300">Dashboard header: Shadows Over Broadway, Cut V7, Policy E&O-2026.1-DEVPOST</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Here is our baseline: Shadows Over Broadway, Script Cut Version 7. Production counsel Sarah Jenkins approved twelve assets...&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 2A: V7 locked baseline</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">0:25–0:35</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 2: 12 Approvals Complete</td>
                <td className="py-3 px-3 text-slate-300">Slow pan over 12 green APPROVED claims rows, Sarah Jenkins reviewer card</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Every decision is bound to its exact scene context, duration, private agreements... 100% complete.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 2B: 12-decision baseline</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">0:35–0:45</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 3: Ingest V8 & Detect Drift</td>
                <td className="py-3 px-3 text-slate-300">Click &apos;Ingest V8 & Detect Drift&apos;. Live progress bar animates. V8 loaded.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Now, production delivers Version 8... Gemini 2.5 Flash isolates two distinct drift modalities.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 3A: Version parent binding</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">0:45–0:55</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 3: Creative Drift (Item 11)</td>
                <td className="py-3 px-3 text-slate-300">Drawer expands on Item 11 poster. Diff shows 2s background blur &rarr; 14s focal shot.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;First: creative drift. In Scene 42, the director zoomed in on this 1946 Crime Detective magazine poster...&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 3B: Prominence shift</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">0:55–1:05</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 3: External Drift (Item 12)</td>
                <td className="py-3 px-3 text-slate-300">Drawer shifts to Item 12 jazz cue. Script text identical; ASCAP dispute card flags conflict.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Second: external evidence drift... the script did not change, but music copyright registries updated...&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 3C: External fact divergence</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">1:05–1:15</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 4: Selective Lineage Parity</td>
                <td className="py-3 px-3 text-slate-300">Metric ribbon snaps: Total 12 | Carried Forward 10 | Reopened 2.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Watch the Deterministic Lineage Parity Guarantee... Ten decisions carried forward automatically.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 4A: 12 &rarr; 10/2 &rarr; 1/1</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">1:15–1:25</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 4: Zero-Query Economics</td>
                <td className="py-3 px-3 text-slate-300">Cursor hovers $0.00 Review Expense and 0 External Queries badge on 10 carried items.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;That is 10 carried forward legal approvals: zero dollars spent on re-review, and zero queries dispatched.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 4B: Zero-query carry forward</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">1:25–1:35</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 5: Parallel Search Dispatched</td>
                <td className="py-3 px-3 text-slate-300">Telemetry tab: Planned 2 | Skipped 10 | Query Reduction: 83.3%. Live API call animation.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Instead of firing twelve expensive searches, our budget governor dispatches the Parallel Search API... 83.3% query reduction.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 5A: 83.3% query reduction</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">1:35–1:45</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 5: Public Domain LOC Proof</td>
                <td className="py-3 px-3 text-slate-300">Item 11 card: Library of Congress catalog citation (142.5ms). Expiration 1974. Stance: SUPPORTING.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;For Item 11, Parallel searches Library of Congress in 142ms, confirming artwork is in public domain.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 5B: LOC public domain citation</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">1:45–1:55</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 5: Fail-Closed Guardrail</td>
                <td className="py-3 px-3 text-slate-300">Item 12 card: ASCAP ACE Vanguard sync dispute. Stance: CONTRADICTORY. Fail-closed indicator.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;For Item 12, Parallel queries ASCAP ACE records... Stance: Contradictory. Lienmark strictly fails closed.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 5C: Fail-closed guardrail</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">1:55–2:05</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 6: Sarah Jenkins Adjudication</td>
                <td className="py-3 px-3 text-slate-300">Counsel Checkpoint drawer opens. Sarah Jenkins reviews 4D breakdown, clicks &apos;Re-Attest&apos;.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Here is the human checkpoint: Lienmark separates AI decision support from legal adjudication...&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 6A: Human-in-the-loop counsel</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">2:05–2:15</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 6: Optimistic UI & SHA-256</td>
                <td className="py-3 px-3 text-slate-300">Server Action updates Item 11 to RE_ATTESTED. SHA-256 audit ledger appends event block.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Via Next.js Server Actions, Item 11 updates to 1 re-attested... chained into tamper-evident SHA-256 ledger.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 6B: SHA-256 audit ledger</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">2:15–2:25</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 6: Exception / Rejection</td>
                <td className="py-3 px-3 text-slate-300">Item 12 rationale entered: &apos;Active Vanguard claim&apos;. Clicks Exception. Badge turns red EXCEPTION.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;For Item 12, counsel will not clear an adverse copyright claim. She designates the cue as 1 exception.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 6C: Exception designation</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">2:25–2:35</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 7: SSR Form E&O-2026 Export</td>
                <td className="py-3 px-3 text-slate-300">Click &apos;Export Form E&O-2026 Exceptions Schedule&apos;. SSR printable report opens at /report/...</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Finally, user exports the Form E&O-2026 Exceptions Schedule... Rendered server-side for underwriter delivery.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-sky-300">Invariant 7A: SSR binder & @media print</td>
              </tr>
              <tr className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-3 font-mono text-amber-300 whitespace-nowrap">2:35–2:45</td>
                <td className="py-3 px-3 font-mono">10s</td>
                <td className="py-3 px-3 font-semibold text-white">Beat 7: 12 = 10 + 1 + 1 Conservation</td>
                <td className="py-3 px-3 text-slate-300">Zoom into 3-tier breakdown: 1 Open Exception | 1 Re-Attested | 10 Carried = 12 Total. Closing logo.</td>
                <td className="py-3 px-3 italic text-slate-200">&ldquo;Notice the mathematical conservation: 10 carried + 1 re-attested + 1 exception = 12 total... That is Lienmark.&rdquo;</td>
                <td className="py-3 px-3 font-mono text-[11px] text-emerald-300">Invariant 7B: 12 = 10 + 1 + 1 Law</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Statutory Disclaimers & Ethics Notice */}
      <footer className="rounded-2xl border border-slate-800/80 bg-slate-950/60 p-6 space-y-4 text-xs text-slate-400">
        <div className="flex items-center gap-2 text-slate-300 font-bold uppercase tracking-wider text-[11px]">
          <Info className="h-4 w-4 text-amber-400" />
          <span>Statutory Underwriting Disclaimers & Ethics Notice</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-slate-400 leading-relaxed">
          <div>
            <p>
              <strong className="text-slate-300">Simulated Clearance Counsel Persona:</strong> Clearance counsel Sarah Jenkins, Esq. (
              <code className="font-mono text-amber-300">counsel_sjenkins_001</code>) is a synthetic demonstrator persona utilized to model entertainment production legal workflows.
            </p>
            <p className="mt-2">
              <strong className="text-slate-300">Fictional Production Scenario:</strong> The motion picture production title (
              <em>Shadows Over Broadway</em>, <code className="font-mono text-amber-300">proj_blockbuster_cinema</code>), script revisions (V7, V8), and referenced entities (
              <em>Vanguard Media Holdings LLC</em>, <em>Apex Film Distributors</em>) are entirely fictional demonstrator fixtures created for the Agentic Cinema Hackathon.
            </p>
          </div>

          <div>
            <p>
              <strong className="text-slate-300">Prohibited Claims Compliance Certification:</strong> This script and presentation have been audited to contain zero prohibited legal certainty claims. The workflow enforces strict non-binding decision support guidelines.
            </p>
            <div className="mt-2 p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] text-slate-300">
              <strong className="text-amber-400">STATUTORY NOTICE:</strong> Lienmark provides version-bound clearance change control and non-binding decision support for entertainment production counsel and E&O insurance underwriters. Lienmark does not provide legal advice, does not practice law, and does not bind insurance policies. All policy binding decisions remain subject to formal independent underwriter evaluation and warranty execution.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
