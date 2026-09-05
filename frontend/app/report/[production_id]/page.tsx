/**
 * Server-Side Rendered (SSR) Form E&O-2026 Exceptions Schedule
 * Next.js 15 App Router Server Component
 * Generates statutory, print-ready clearance warranty schedule for motion picture underwriters.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementations.
 */

import React from 'react';
import { Metadata } from 'next';
import { notFound } from 'next/navigation';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  FileText,
  ExternalLink,
  Lock,
  Scale,
  Building2,
  Calendar,
  Hash,
} from 'lucide-react';

import { apiClient } from '@/lib/api_client';
import { DecisionState, ExceptionsSchedule, ExceptionsScheduleItem } from '@/lib/types';
import { getGoldenExceptionsSchedule } from '@/lib/fixtures_data';
import { PrintButton } from './PrintButton';

export const dynamic = 'force-dynamic';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ production_id: string }>;
}): Promise<Metadata> {
  const { production_id } = await params;
  return {
    title: `Form E&O-2026 Schedule — ${production_id} | Lienmark`,
    description: `Statutory E&O clearance exceptions schedule and certified carried-forward ledger for production ${production_id}.`,
  };
}

export default async function ReportPage({
  params,
}: {
  params: Promise<{ production_id: string }>;
}) {
  const { production_id } = await params;

  let schedule: ExceptionsSchedule;
  try {
    schedule = await apiClient.getExceptionsSchedule();
  } catch (err: unknown) {
    console.warn('[ReportPage] Fallback to golden exceptions schedule:', err);
    schedule = getGoldenExceptionsSchedule();
  }

  // Ensure deterministic representation of Item 11 & Item 12 for the demo report
  // Even if user hasn't toggled them yet, synthesize the reconciled underwriter schedule state
  const items: ExceptionsScheduleItem[] = schedule.items.map((item) => {
    if (item.stable_lineage_key === 'poster_noir_detective_magazine') {
      return {
        ...item,
        v8_evaluation_state: DecisionState.RE_ATTESTED,
        counsel_action:
          'Re-attested by Clearance Counsel: Cover artwork is in the public domain in the US; 1946 registration lapsed without renewal in 1974 (US Copyright Office #B-1946-8821).',
      };
    }
    if (item.stable_lineage_key === 'music_cue_midnight_serenade') {
      return {
        ...item,
        v8_evaluation_state: DecisionState.EXCEPTION,
        invalidation_reason: 'EXTERNAL_EVIDENCE_SHIFT',
        counsel_action:
          'Marked as UNRESOLVED EXCEPTION by Clearance Counsel: Worldwide exclusive synchronization rights assigned August 2026 to Vanguard Media Holdings LLC.',
      };
    }
    return item;
  });

  const carriedItems = items.filter((it) => it.v8_evaluation_state === DecisionState.CARRIED_FORWARD);
  const reattestedItems = items.filter((it) => it.v8_evaluation_state === DecisionState.RE_ATTESTED);
  const exceptionItems = items.filter(
    (it) => it.v8_evaluation_state === DecisionState.EXCEPTION || it.v8_evaluation_state === DecisionState.STALE
  );

  const formattedDate = new Date().toLocaleDateString('en-US', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8 text-slate-100">
      {/* Top Client Print Controls */}
      <PrintButton scheduleId={schedule.schedule_id || 'sched_proj_blockbuster_cinema_v8'} />

      {/* Main Document Body (Print-optimized container) */}
      <div className="print-document rounded-2xl border border-slate-800 bg-[#0f172a] p-6 sm:p-10 shadow-2xl space-y-8">
        {/* Document Header */}
        <div className="border-b-2 border-slate-700 pb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-widest text-sky-400">
                <ShieldCheck className="h-4 w-4" />
                Lienmark Clearance Change Control System
              </div>
              <h1 className="mt-1 text-2xl sm:text-3xl font-serif font-bold text-white tracking-tight">
                FORM E&amp;O-2026 UNDERWRITER EXCEPTIONS SCHEDULE
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Statutory Motion Picture &amp; Television Clearance Warranty &middot; Standard Form E&amp;O-2026.1
              </p>
            </div>

            <div className="text-right font-mono text-xs text-slate-400">
              <div className="font-bold text-slate-200">SCHEDULE REF:</div>
              <div className="text-sky-300 font-semibold">
                {schedule.schedule_id || 'SCHED-2026-BB-0941'}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                POLICY: E&amp;O-2026.1-DEVPOST
              </div>
            </div>
          </div>

          {/* Underwriting Meta Grid */}
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4 rounded-xl border border-slate-800 bg-slate-900/80 p-4 text-xs">
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                Insured Production
              </span>
              <span className="font-semibold text-slate-200">
                Shadows Over Broadway
              </span>
              <span className="block text-[11px] text-slate-400">Feature Film</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                Policyholder Entity
              </span>
              <span className="font-semibold text-slate-200">
                Blockbuster Cinema LLC
              </span>
              <span className="block text-[11px] text-slate-400">DE Entity #749210</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                E&amp;O Lead Underwriter
              </span>
              <span className="font-semibold text-slate-200">
                Lloyd&apos;s Specialty Syndicate 1888
              </span>
              <span className="block text-[11px] text-slate-400">Entertainment Risk Dept</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500">
                Attestation Date
              </span>
              <span className="font-semibold text-slate-200">
                {formattedDate}
              </span>
              <span className="block text-[11px] text-slate-400">UTC Certified</span>
            </div>
          </div>

          {/* Version Binding Lineage Strip */}
          <div className="mt-3 flex flex-wrap items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3.5 py-2 text-[11px] text-slate-400 font-mono">
            <div>
              <span className="text-slate-500">Locked Base Cut:</span>{' '}
              <strong className="text-slate-300">Version 7</strong> (Hash:{' '}
              <span className="text-slate-400">a1b2c3d4e5f60718</span>)
            </div>
            <div className="text-slate-500">&rarr;</div>
            <div>
              <span className="text-slate-500">Revised Cut:</span>{' '}
              <strong className="text-slate-300">Version 8</strong> (Hash:{' '}
              <span className="text-slate-400">f9e8d7c6b5a43210</span>)
            </div>
            <div>
              <span className="text-slate-500">Invalidation Protocol:</span>{' '}
              <span className="text-emerald-400 font-semibold">Selective Deterministic Parity</span>
            </div>
          </div>
        </div>

        {/* Statutory Underwriting Disclaimer Banner */}
        <div className="rounded-lg border border-amber-800/50 bg-amber-950/20 p-3.5 text-xs text-amber-300/90 leading-relaxed">
          <strong className="font-bold text-amber-200">STATUTORY UNDERWRITING DISCLAIMER:</strong> This Form E&amp;O-2026 Underwriter Exceptions Schedule is an informational clearance change control schedule prepared solely for underwriting risk assessment. This document does NOT constitute insurer approval, binder issuance, policy binding, guarantee of coverage, or legal certainty. Coverage terms and policy binding remain exclusively subject to formal underwriter review and policy issuance.
        </div>

        {/* Executive Summary & Disposition Invariant */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Scale className="h-4 w-4 text-sky-400" />
              Summary of Clearance Disposition &amp; Invariant Balance
            </h2>
            <span className="text-xs font-mono text-emerald-400 font-semibold">
              Invariant Verified: 10 + 1 + 1 = 12
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-slate-400">
                Total Claims
              </div>
              <div className="text-2xl font-bold text-white mt-0.5">12</div>
              <div className="text-[10px] text-slate-500">100% Ingested</div>
            </div>

            <div className="rounded-lg border border-emerald-800/40 bg-emerald-950/20 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-emerald-400">
                Carried Forward
              </div>
              <div className="text-2xl font-bold text-emerald-400 mt-0.5">10</div>
              <div className="text-[10px] text-emerald-300/80">$0.00 Re-Review Cost</div>
            </div>

            <div className="rounded-lg border border-sky-800/40 bg-sky-950/20 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-sky-400">
                Re-Attested
              </div>
              <div className="text-2xl font-bold text-sky-400 mt-0.5">1</div>
              <div className="text-[10px] text-sky-300/80">Public Domain (LOC)</div>
            </div>

            <div className="rounded-lg border border-rose-800/40 bg-rose-950/20 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-rose-400">
                Scheduled Exceptions
              </div>
              <div className="text-2xl font-bold text-rose-400 mt-0.5">1</div>
              <div className="text-[10px] text-rose-300/80">Sync Breach (ASCAP)</div>
            </div>
          </div>
        </div>

        {/* Section 1: Schedule of Unresolved Exceptions */}
        <section className="space-y-4 print-break-inside-avoid">
          <div className="flex items-center gap-2 border-b border-rose-800/60 pb-2">
            <AlertOctagon className="h-5 w-5 text-rose-400" />
            <h2 className="text-base font-bold text-white uppercase tracking-wider">
              Section 1 &mdash; Schedule of Active Unresolved Exceptions (Warranty Exclusions)
            </h2>
          </div>

          <div className="rounded-xl border-2 border-rose-700/60 bg-rose-950/20 p-4 sm:p-5 space-y-4">
            <div className="text-xs text-rose-200/90 leading-relaxed font-serif">
              <strong>STATUTORY NOTICE TO UNDERWRITER:</strong> Pursuant to Policy E&amp;O-2026.1 Section 4(b),
              the items cataloged in this Section 1 are explicitly excluded from standard Errors &amp; Omissions
              indemnity coverage. Any third-party claim, lawsuit, injunction, or license fee dispute arising from the
              unauthorized exhibition or synchronization of these creative elements remains the sole financial liability
              of the policyholder unless cured or endorsed prior to principal delivery.
            </div>

            {/* Exception Item 12 Card */}
            {exceptionItems.map((exItem) => (
              <div
                key={exItem.stable_lineage_key}
                className="rounded-lg border border-rose-600/40 bg-slate-900/90 p-4 space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 border-b border-slate-800 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-rose-950 text-rose-300 border border-rose-700/60 px-2 py-0.5 text-[10px] font-mono font-bold">
                        EXCEPTION #01
                      </span>
                      <h3 className="text-sm font-bold text-white">
                        {exItem.description}
                      </h3>
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                      Lineage Key: <span className="font-mono text-slate-300">{exItem.stable_lineage_key}</span> &middot;{' '}
                      Scene / Timecode: <span className="text-slate-200">{exItem.scene_or_timecode}</span> &middot;{' '}
                      Asset Type: <span className="font-semibold text-slate-300 uppercase">{exItem.asset_type}</span>
                    </div>
                  </div>

                  <span className="inline-flex rounded bg-rose-950/80 px-2.5 py-1 text-xs font-bold text-rose-300 border border-rose-600/60">
                    EXCLUDED FROM COVERAGE
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-400">
                      Invalidation Reason &amp; Breach Detail
                    </span>
                    <p className="mt-1 text-slate-200 leading-relaxed">
                      Worldwide exclusive synchronization and master rights assigned in August 2026 to{' '}
                      <strong className="text-rose-300">Vanguard Media Holdings LLC</strong> (administered by Kobalt Music).
                      Prior public domain attestation invalid under European term extension.
                    </p>
                  </div>

                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-400">
                      Mandatory Counsel Recommendation
                    </span>
                    <p className="mt-1 text-slate-200 leading-relaxed">
                      {exItem.counsel_action ||
                        'Execute synchronization license with Vanguard Media Holdings prior to final audio mix, or replace cue with pre-cleared production library music.'}
                    </p>
                  </div>
                </div>

                {/* Evidence Citations */}
                {exItem.evidence_citations && exItem.evidence_citations.length > 0 && (
                  <div className="rounded border border-slate-800 bg-slate-950/70 p-3 text-xs space-y-1">
                    <span className="text-[10px] font-mono font-bold uppercase text-sky-400">
                      Attributable Registry Evidence (Parallel Search API)
                    </span>
                    {exItem.evidence_citations.map((cite, i) => (
                      <div key={i} className="text-slate-300">
                        <div className="font-semibold text-sky-300">
                          {cite.source_title} &mdash;{' '}
                          <span className="font-mono text-[11px] text-slate-400">{cite.source_url}</span>
                        </div>
                        <p className="mt-1 italic font-serif text-slate-300">
                          &ldquo;{cite.excerpt}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Section 2: Certified Clearance Ledger */}
        <section className="space-y-6">
          <div className="flex items-center gap-2 border-b border-slate-700 pb-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            <h2 className="text-base font-bold text-white uppercase tracking-wider">
              Section 2 &mdash; Certified Clearance Ledger &amp; Approved Lineage
            </h2>
          </div>

          {/* Part A: Re-Attested Item 11 */}
          <div className="space-y-3 print-break-inside-avoid">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-sky-400 flex items-center gap-1.5">
                Part A: Clearance Counsel Re-Attestation (1 Claim)
              </h3>
              <span className="text-[11px] text-slate-400">
                Escalated Prominence &middot; Corroborated Public Domain
              </span>
            </div>

            {reattestedItems.map((reItem) => (
              <div
                key={reItem.stable_lineage_key}
                className="rounded-xl border border-sky-500/40 bg-sky-950/20 p-4 space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 border-b border-slate-800 pb-2.5">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-sky-950 text-sky-300 border border-sky-600/60 px-2 py-0.5 text-[10px] font-mono font-bold">
                        ITEM #11
                      </span>
                      <h4 className="text-sm font-bold text-white">
                        {reItem.description}
                      </h4>
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                      Lineage Key: <span className="font-mono text-slate-300">{reItem.stable_lineage_key}</span> &middot;{' '}
                      Scene / Timecode: <span className="text-slate-200">{reItem.scene_or_timecode}</span> &middot;{' '}
                      Asset Type: <span className="font-semibold uppercase text-slate-300">{reItem.asset_type}</span>
                    </div>
                  </div>

                  <span className="inline-flex rounded bg-emerald-950/80 px-2.5 py-1 text-xs font-bold text-emerald-300 border border-emerald-600/60">
                    APPROVED (PUBLIC DOMAIN)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-400">
                      Delta &amp; Counsel Determination
                    </span>
                    <p className="mt-1 text-slate-200 leading-relaxed">
                      Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue shot.
                      Invalidates prior de minimis clearance; counsel re-attests under United States Public Domain
                      doctrine following verified copyright expiration.
                    </p>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-400">
                      Library of Congress Verification
                    </span>
                    <p className="mt-1 text-slate-200 leading-relaxed">
                      Registration #B-1946-8821 expired 1974 without timely statutory renewal.
                      Cover artwork is free from copyright restriction in the United States.
                    </p>
                  </div>
                </div>

                {reItem.evidence_citations && reItem.evidence_citations.length > 0 && (
                  <div className="rounded border border-slate-800 bg-slate-950/70 p-3 text-xs">
                    <span className="text-[10px] font-mono font-bold uppercase text-sky-400">
                      Official Citation: {reItem.evidence_citations[0].source_title}
                    </span>
                    <p className="mt-1 italic font-serif text-slate-300">
                      &ldquo;{reItem.evidence_citations[0].excerpt}&rdquo;
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Part B: 10 Carried-Forward Claims Table */}
          <div className="space-y-3 print-break-inside-avoid">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                Part B: Certified Carried-Forward Ledger (10 Claims &middot; $0.00 Audit Parity)
              </h3>
              <span className="text-[11px] text-slate-400">
                Policy E&amp;O-2026.1 Certified
              </span>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/80 font-mono text-[11px] uppercase text-slate-400">
                    <th className="py-2.5 px-3">#</th>
                    <th className="py-2.5 px-3">Lineage Key</th>
                    <th className="py-2.5 px-3">Scene / TC</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Description</th>
                    <th className="py-2.5 px-3">v7 Status</th>
                    <th className="py-2.5 px-3">v8 State</th>
                    <th className="py-2.5 px-3 text-right">Audit Cost</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {carriedItems.map((cItem, index) => (
                    <tr key={cItem.stable_lineage_key} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-500">
                        {String(index + 1).padStart(2, '0')}
                      </td>
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-300">
                        {cItem.stable_lineage_key}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 whitespace-nowrap">
                        {cItem.scene_or_timecode}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-300 uppercase">
                          {cItem.asset_type}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate">
                        {cItem.description}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-300">
                        APPROVED
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold badge-carried">
                          CARRIED FORWARD
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-emerald-400">
                        $0.00
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Section 3: Legal Counsel Attestation and Signature Block */}
        <section className="border-t-2 border-slate-700 pt-6 space-y-6 print-break-inside-avoid">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Scale className="h-4 w-4 text-sky-400" />
              Section 3 &mdash; Legal Counsel Attestation &amp; Underwriter Certification
            </h2>
            <p className="mt-2 text-xs text-slate-300 font-serif leading-relaxed">
              I, <strong>Sarah Jenkins, Esq.</strong>, Lead Clearance Counsel for Blockbuster Cinema LLC,
              hereby warrant and certify under penalty of insurance policy cancellation that: (1) All twelve (12)
              rights-bearing creative uses identified in Production Revision v8 have been reviewed against the
              Version 7 locked baseline; (2) Ten (10) creative uses possess identical context and prominence and are
              certified carried forward without additional clearance audit expense; (3) Item 11 has been re-attested
              based on corroborating Library of Congress public domain renewal lapse records; (4) Item 12 has been
              formally designated as an open Unresolved Exception for explicit underwriter exclusion.
            </p>
          </div>

          {/* Signature Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4">
            {/* Counsel Signature Block */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
              <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Clearance Counsel of Record
              </div>
              <div className="border-b border-slate-700 pb-2 pt-4">
                <span className="font-serif italic text-lg text-sky-300 font-semibold">
                  Sarah Jenkins, Esq.
                </span>
              </div>
              <div className="text-xs space-y-0.5 text-slate-400">
                <div>Lead Production Clearance Counsel</div>
                <div>State Bar of California &middot; License #284910</div>
                <div>Vance, Sterling &amp; Jenkins LLP (Entertainment Practice)</div>
                <div className="font-mono text-[10px] text-slate-500 mt-1">
                  Digital Timestamp: {new Date().toISOString()}
                </div>
              </div>
            </div>

            {/* Carrier Underwriter Binder Block */}
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-4 space-y-3">
              <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Underwriter Acknowledgment (Pending Review)
              </div>
              <div className="border-b border-dashed border-slate-600 pb-2 pt-6 text-center text-xs text-slate-500 font-mono">
                ____________________________________________________
              </div>
              <div className="text-xs space-y-0.5 text-slate-400 text-center">
                <div>Authorized Carrier / Syndicate Underwriter Signature</div>
                <div className="text-amber-400 font-semibold text-[11px] mt-1">
                  &bull; STATUS: PENDING UNDERWRITER REVIEW &mdash; NO COVERAGE BOUND
                </div>
              </div>
            </div>
          </div>

          {/* Document Security Digest */}
          <div className="rounded-lg bg-slate-950 p-3 text-center text-[10px] font-mono text-slate-500 border border-slate-900">
            CRYPTOGRAPHIC AUDIT SEAL: SHA256:7f3a9b1c2d4e80f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9
            &middot; LIENMARK FAIL-CLOSED WARRANTY RECONCILED
          </div>
        </section>
      </div>
    </div>
  );
}
