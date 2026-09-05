'use client';

/**
 * Lienmark Clearance Decision Lifecycle Component
 * Sprint 4C Usability Fix 3: Unfamiliar Tester Comprehension
 * Visual guide articulating the 4-step clearance lifecycle and how an underwriter reviews it:
 *  'Step 1: Baseline Review -> Step 2: Automated Drift Invalidation -> Step 3: Counsel Checkpoint Adjudication -> Step 4: Version-Bound Form E&O-2026 Exceptions Schedule for Carrier Underwriting.'
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import {
  FileSpreadsheet,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Gavel,
  FileCheck,
  HelpCircle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

export interface ClearanceLifecycleGuideProps {
  currentStep?: 1 | 2 | 3 | 4;
  className?: string;
}

interface LifecycleStepData {
  stepNumber: number;
  stepName: string;
  title: string;
  shortDesc: string;
  underwriterMeaning: string;
  icon: React.ComponentType<{ className?: string }>;
  accentColor: string;
}

const LIFECYCLE_STEPS: LifecycleStepData[] = [
  {
    stepNumber: 1,
    stepName: 'Step 1: Baseline Review',
    title: 'Baseline Review',
    shortDesc: 'Script Cut v7 locked clearance baseline established with 12 claims cataloged and archived.',
    underwriterMeaning: 'Establishes the insured production rights baseline and immutable content hash.',
    icon: FileCheck,
    accentColor: 'text-slate-300 border-slate-700 bg-slate-800/80',
  },
  {
    stepNumber: 2,
    stepName: 'Step 2: Automated Drift Invalidation',
    title: 'Automated Drift Invalidation',
    shortDesc: 'Semantic AI & rights graph check re-evaluates 12 claims: 10 achieve Lineage Parity ($0 review); 2 flagged for material drift.',
    underwriterMeaning: 'Guarantees $0 re-review waste for identical assets while catching hidden infringement exposure.',
    icon: AlertTriangle,
    accentColor: 'text-amber-400 border-amber-500/40 bg-amber-950/40',
  },
  {
    stepNumber: 3,
    stepName: 'Step 3: Counsel Checkpoint Adjudication',
    title: 'Counsel Checkpoint Adjudication',
    shortDesc: 'Legal counsel inspects 4-dimensional audit trail (Creative, Evidence, Agreement, Policy) and issues affirmative determinations.',
    underwriterMeaning: 'Ensures human legal accountability: AI never approves stale decisions autonomously.',
    icon: Gavel,
    accentColor: 'text-sky-400 border-sky-500/40 bg-sky-950/40',
  },
  {
    stepNumber: 4,
    stepName: 'Step 4: Version-Bound Form E&O-2026 Exceptions Schedule for Carrier Underwriting',
    title: 'Version-Bound Form E&O-2026 Exceptions Schedule for Carrier Underwriting',
    shortDesc: 'Immutable Form E&O-2026 schedule published for carrier underwriting, clearly delineating covered assets from excluded exceptions.',
    underwriterMeaning: 'Carrier binds policy with exact knowledge of covered assets vs excluded risks (Item 12).',
    icon: ShieldCheck,
    accentColor: 'text-emerald-400 border-emerald-500/40 bg-emerald-950/40',
  },
];

export const ClearanceLifecycleGuide: React.FC<ClearanceLifecycleGuideProps> = ({
  currentStep = 3,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  return (
    <section
      aria-label="Clearance Decision Lifecycle Guide"
      role="region"
      className={`rounded-2xl border border-sky-500/30 bg-[#10182b] p-4 sm:p-5 shadow-xl space-y-4 ${className}`}
    >
      {/* Component Title & Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/30 flex-shrink-0">
            <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight">
              Clearance Decision Lifecycle Guide
            </h3>
            <p className="text-[11px] text-slate-400">
              How clearance decisions evolve from automated drift detection to final underwriter policy binding.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300 font-mono transition-colors focus:outline-none focus:underline"
            aria-expanded={isExpanded}
            aria-label={isExpanded ? 'Collapse Lifecycle Guide' : 'Expand Lifecycle Guide'}
          >
            <span>{isExpanded ? 'Hide Details' : 'Show Details'}</span>
            {isExpanded ? (
              <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {/* Canonical Workflow Flow Ribbon */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 space-y-2">
        <div className="text-[10px] font-mono uppercase tracking-widest text-sky-400 font-semibold flex items-center justify-between">
          <span>Canonical Decision Pipeline</span>
          <span className="text-slate-400">Policy E&amp;O-2026.1 Standard</span>
        </div>
        <p className="font-mono text-xs text-slate-200 leading-relaxed font-medium bg-slate-900/90 p-2.5 rounded-lg border border-slate-800 break-words">
          <strong className="text-white">Clearance Decision Lifecycle:</strong>{' '}
          <span className="text-sky-300">Step 1: Baseline Review</span>{' '}
          <span className="text-slate-500">&rarr;</span>{' '}
          <span className="text-amber-300">Step 2: Automated Drift Invalidation</span>{' '}
          <span className="text-slate-500">&rarr;</span>{' '}
          <span className="text-indigo-300">Step 3: Counsel Checkpoint Adjudication</span>{' '}
          <span className="text-slate-500">&rarr;</span>{' '}
          <span className="text-emerald-300">
            Step 4: Version-Bound Form E&amp;O-2026 Exceptions Schedule for Carrier Underwriting
          </span>
        </p>
      </div>

      {/* Expanded 4-Step Cards */}
      {isExpanded && (
        <div className="space-y-3 pt-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {LIFECYCLE_STEPS.map((step) => {
              const Icon = step.icon;
              const isActive = step.stepNumber === currentStep;
              const isPast = step.stepNumber < currentStep;

              return (
                <div
                  key={step.stepNumber}
                  className={`rounded-xl border p-3.5 transition-all flex flex-col justify-between space-y-2.5 ${
                    isActive
                      ? 'border-sky-400 bg-sky-950/30 ring-1 ring-sky-500/30 shadow-lg shadow-sky-950/40'
                      : isPast
                      ? 'border-emerald-800/40 bg-emerald-950/15'
                      : 'border-slate-800 bg-slate-900/50'
                  }`}
                  role="article"
                  aria-label={step.stepName}
                >
                  <div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
                        Phase {step.stepNumber} of 4
                      </span>
                      {isPast ? (
                        <span className="inline-flex items-center gap-1 rounded bg-emerald-950/80 px-1.5 py-0.2 text-[10px] font-mono text-emerald-300 border border-emerald-500/30">
                          <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                          Complete
                        </span>
                      ) : isActive ? (
                        <span className="rounded bg-sky-500/20 px-1.5 py-0.2 text-[10px] font-mono text-sky-300 border border-sky-500/40 font-bold animate-pulse">
                          Current Focus
                        </span>
                      ) : (
                        <span className="rounded bg-slate-800 px-1.5 py-0.2 text-[10px] font-mono text-slate-400">
                          Pending
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mt-2">
                      <div className={`p-1.5 rounded-lg border ${step.accentColor}`}>
                        <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                      </div>
                      <h4 className="text-xs font-bold text-white leading-tight">
                        {step.title}
                      </h4>
                    </div>

                    <p className="mt-2 text-[11px] text-slate-300 leading-normal">
                      {step.shortDesc}
                    </p>
                  </div>

                  <div className="rounded-lg bg-slate-950/70 p-2 border border-slate-800 text-[10px] space-y-0.5">
                    <span className="font-mono uppercase text-slate-400 font-semibold block">
                      Underwriter Significance:
                    </span>
                    <span className="text-slate-300 leading-snug block">
                      {step.underwriterMeaning}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Underwriter Outcome Summary Callout */}
          <div className="rounded-xl border border-emerald-500/40 bg-gradient-to-r from-emerald-950/50 via-slate-900 to-sky-950/50 p-3.5 text-xs text-slate-300 space-y-1">
            <div className="flex items-center gap-2 font-bold text-emerald-300">
              <ShieldCheck className="h-4 w-4 text-emerald-400 flex-shrink-0" aria-hidden="true" />
              <span>How an Underwriter Reviews the Final Outcome:</span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-200">
              Insurance syndicate underwriters inspect the version-bound <strong>Form E&amp;O-2026 Exceptions Schedule</strong>.
              Underwriters require mathematical certainty: the 10 carried claims are verified bit-for-bit identical ($0 re-review expense),
              Item 11 is formally attested by legal counsel with Library of Congress catalog citations, and Item 12 is scheduled as an excluded exception.
              Because uncleared rights are formally scheduled as exclusions, carrier liability is strictly quarantined, allowing immediate policy binding.
            </p>
            <div className="pt-2 border-t border-emerald-500/20 flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] font-mono text-emerald-400 font-semibold">
                Underwriter Warranty Export Path:
              </span>
              <Link
                href="/report/proj_blockbuster_cinema"
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 px-3 py-1 text-xs font-bold text-slate-950 transition-colors shadow-sm"
                aria-label="Open Underwriter Warranty Form E&O-2026 Exceptions Schedule"
              >
                <FileSpreadsheet className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Open Form E&amp;O-2026 Underwriter Exceptions Schedule (/report/proj_blockbuster_cinema)</span>
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

export default ClearanceLifecycleGuide;
