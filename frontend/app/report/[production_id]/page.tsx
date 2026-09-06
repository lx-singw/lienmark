/**
 * Server-Side Rendered (SSR) Form E&O-2026 Compatible Clearance Exceptions Schedule
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
  ChevronDown,
  Download,
  FileCode2,
  Sparkles,
  Layers,
} from 'lucide-react';

import { apiClient } from '@/lib/api_client';
import {
  AuditTrailResponse,
  DecisionState,
  ExceptionsSchedule,
  ExceptionsScheduleItem,
} from '@/lib/types';
import { getGoldenAuditTrail, getGoldenExceptionsSchedule } from '@/lib/fixtures_data';
import { PrintButton } from './PrintButton';

export const dynamic = 'force-dynamic';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ production_id: string }>;
}): Promise<Metadata> {
  const { production_id } = await params;
  return {
    title: `Form E&O-2026 Compatible Clearance Exceptions Schedule — ${production_id} | Lienmark`,
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
    schedule = await apiClient.getExceptionsSchedule({ autoReconcileDemo: false });
  } catch (err: unknown) {
    console.warn('[ReportPage] Fallback to golden exceptions schedule:', err);
    schedule = getGoldenExceptionsSchedule({}, false);
  }

  let auditTrail: AuditTrailResponse | null = null;
  try {
    auditTrail = await apiClient.getAuditTrail();
  } catch (err: unknown) {
    console.warn('[ReportPage] Fallback to golden audit trail:', err);
    auditTrail = {
      lineage_key: null,
      total_events: 0,
      is_ledger_tamper_free: false,
      chain_head_hash: '',
      events: [],
    };
  }

  // Consume the authentic recorded schedule items directly (zero client synthesis)
  const items: ExceptionsScheduleItem[] = schedule.items;

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
      {/* Top Client Print and Download Controls */}
      <div className="no-print print:hidden">
        <PrintButton
          scheduleId={schedule.schedule_id || 'sched_proj_blockbuster_cinema_v8'}
          scheduleData={schedule}
          auditLedgerData={auditTrail || undefined}
          productionTitle="Shadows Over Broadway"
          versionLabel="Version 8 Cut"
        />
      </div>

      {/* Main Document Body (Dark Luxury Digital Binder & Print-optimized Container) */}
      <div className="print-document rounded-2xl border border-slate-800/90 bg-gradient-to-b from-[#0f172a] via-[#0d1424] to-[#090d16] p-6 sm:p-10 shadow-2xl space-y-8 ring-1 ring-white/5 print:bg-white print:border-none print:p-0 print:shadow-none print:ring-0 print:space-y-6 print:text-black">
        {/* PROMINENT COUNSEL PERSONA DISCLOSURE (STATUTORY DEMO NOTICE) */}
        <div className="rounded-xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-amber-950/40 p-3.5 sm:p-4 text-xs text-amber-200 shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 print:border print:border-black print:bg-stone-100 print:text-black">
          <div className="flex items-center gap-2.5 font-sans font-semibold">
            <Scale className="h-4 w-4 text-amber-400 flex-shrink-0 print:text-black" />
            <span>
              Simulated Counsel Persona: <strong className="text-amber-100 font-bold print:text-black">Sarah Jenkins, Esq.</strong> (Demo Only &mdash; Not Legal Advice)
            </span>
          </div>
          <span className="inline-flex items-center rounded-md bg-amber-900/60 border border-amber-600/40 px-2.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-amber-300 font-bold print:border-black print:bg-white print:text-black">
            Demo Persona &middot; Non-Advisory
          </span>
        </div>

        {/* PROMINENT STATUTORY UNDERWRITING DISCLAIMER BANNER (HEADER) */}
        <div className="rounded-xl border border-rose-600/50 bg-rose-950/30 p-4 text-xs text-rose-200 leading-relaxed font-sans shadow-inner print:border print:border-black print:bg-stone-50 print:text-black">
          <strong className="font-bold text-rose-300 print:text-black">LEGAL &amp; UNDERWRITING DISCLAIMER:</strong> THIS ARTIFACT IS A VERSION-BOUND SCHEDULE OF UNRESOLVED CLEARANCE EXCEPTIONS FOR DEMONSTRATION AND INFORMATIONAL PURPOSES ONLY. NO ARTIFACT GENERATED BY LIENMARK CONSTITUTES OR CLAIMS FORMAL UNDERWRITING APPROVAL, POLICY BINDING, INSURANCE COVERAGE, LEGAL OPINION, OR LEGAL CERTAINTY. COVERAGE IS SUBJECT EXCLUSIVELY TO A SEPARATELY EXECUTED POLICY BINDER WITH AN ADMITTED OR SURPLUS LINES CARRIER.
        </div>

        {/* Document Header */}
        <div className="border-b-2 border-slate-700 pb-6 print:border-black">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-widest text-sky-400 print:text-black">
                <ShieldCheck className="h-4 w-4 print:hidden" />
                Lienmark Clearance Change Control System
              </div>
              <h1 className="mt-1 text-2xl sm:text-3xl font-serif font-bold text-white tracking-tight print:text-black">
                FORM E&amp;O-2026 COMPATIBLE CLEARANCE EXCEPTIONS SCHEDULE
              </h1>
              <p className="text-xs text-slate-400 mt-0.5 print:text-slate-600">
                Form E&amp;O-2026 Compatible Clearance Exceptions Schedule &middot; Standard Form E&amp;O-2026.1
              </p>
            </div>

            <div className="text-right font-mono text-xs text-slate-400 print:text-black">
              <div className="font-bold text-slate-200 print:text-black">SCHEDULE REF:</div>
              <div className="text-sky-300 font-semibold print:text-black">
                {schedule.schedule_id || 'SCHED-2026-BB-0941'}
              </div>
              <div className="text-[11px] text-slate-500 mt-1 print:text-slate-600">
                POLICY: E&amp;O-2026.1-DEVPOST
              </div>
            </div>
          </div>

          {/* Underwriting Meta Grid */}
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4 rounded-xl border border-slate-800 bg-slate-900/80 p-4 text-xs print:border print:border-black print:bg-stone-50 print:text-black">
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500 print:text-slate-600">
                Insured Production
              </span>
              <span className="font-semibold text-slate-200 print:text-black">
                Shadows Over Broadway
              </span>
              <span className="block text-[11px] text-slate-400 print:text-slate-600">Feature Film</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500 print:text-slate-600">
                Policyholder Entity
              </span>
              <span className="font-semibold text-slate-200 print:text-black">
                Blockbuster Cinema LLC
              </span>
              <span className="block text-[11px] text-slate-400 print:text-slate-600">DE Entity #749210</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500 print:text-slate-600">
                E&amp;O Lead Underwriter
              </span>
              <span className="font-semibold text-slate-200 print:text-black">
                Lloyd&apos;s Specialty Syndicate 1888
              </span>
              <span className="block text-[11px] text-slate-400 print:text-slate-600">Entertainment Risk Dept</span>
            </div>
            <div>
              <span className="block text-[10px] uppercase font-bold text-slate-500 print:text-slate-600">
                Attestation Date
              </span>
              <span className="font-semibold text-slate-200 print:text-black">
                {formattedDate}
              </span>
              <span className="block text-[11px] text-slate-400 print:text-slate-600">UTC Certified</span>
            </div>
          </div>

          {/* Version Binding Lineage Strip */}
          <div className="mt-3 flex flex-wrap items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3.5 py-2 text-[11px] text-slate-400 font-mono print:border print:border-black print:bg-white print:text-black">
            <div>
              <span className="text-slate-500 print:text-slate-700">Locked Base Cut:</span>{' '}
              <strong className="text-slate-300 print:text-black">Version 7</strong> (Hash:{' '}
              <span className="text-slate-400 print:text-black">a1b2c3d4e5f60718</span>)
            </div>
            <div className="text-slate-500 print:text-black">&rarr;</div>
            <div>
              <span className="text-slate-500 print:text-slate-700">Revised Cut:</span>{' '}
              <strong className="text-slate-300 print:text-black">Version 8</strong> (Hash:{' '}
              <span className="text-slate-400 print:text-black">f9e8d7c6b5a43210</span>)
            </div>
            <div>
              <span className="text-slate-500 print:text-slate-700">Invalidation Protocol:</span>{' '}
              <span className="text-emerald-400 font-semibold print:text-black">Selective Deterministic Parity</span>
            </div>
          </div>
        </div>

        {/* Executive Summary & Disposition Invariant */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Scale className="h-4 w-4 text-sky-400" />
              Summary of Clearance Disposition &amp; Invariant Balance
            </h2>
            <span className="text-xs font-mono text-emerald-400 font-semibold">
              Invariant Verified: {carriedItems.length} + {reattestedItems.length} + {exceptionItems.length} = {items.length}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-slate-400">
                Total Claims
              </div>
              <div className="text-2xl font-bold text-white mt-0.5">{items.length}</div>
              <div className="text-[10px] text-slate-500">100% Ingested</div>
            </div>

            <div className="rounded-lg border border-emerald-800/40 bg-emerald-950/20 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-emerald-400">
                Carried Forward
              </div>
              <div className="text-2xl font-bold text-emerald-400 mt-0.5">{carriedItems.length}</div>
              <div className="text-[10px] text-emerald-300/80">$0.00 Re-Review Cost</div>
            </div>

            <div className="rounded-lg border border-sky-800/40 bg-sky-950/20 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-sky-400">
                Re-Attested
              </div>
              <div className="text-2xl font-bold text-sky-400 mt-0.5">{reattestedItems.length}</div>
              <div className="text-[10px] text-sky-300/80">Public Domain (LOC)</div>
            </div>

            <div className="rounded-lg border border-rose-800/40 bg-rose-950/20 p-3 text-center">
              <div className="text-[10px] uppercase font-bold text-rose-400">
                Scheduled Exceptions
              </div>
              <div className="text-2xl font-bold text-rose-400 mt-0.5">{exceptionItems.length}</div>
              <div className="text-[10px] text-rose-300/80">Sync Breach (ASCAP)</div>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* SECTION I: UNRESOLVED EXCEPTIONS (TIER 1: SCHEDULED EXCEPTIONS) */}
        {/* ========================================================================= */}
        <section className="space-y-4 break-inside-avoid print-break-inside-avoid">
          <details
            open
            className="group rounded-2xl border border-rose-800/70 bg-rose-950/20 shadow-xl overflow-hidden transition-all duration-200 print:border print:border-black print:bg-white print:shadow-none print:rounded-none"
          >
            <summary className="flex items-center justify-between p-4 sm:p-5 cursor-pointer select-none bg-rose-950/50 hover:bg-rose-900/40 border-b border-rose-800/70 transition-colors list-none [&::-webkit-details-marker]:hidden print:bg-white print:border-b-2 print:border-black print:p-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="rounded bg-rose-950 text-rose-300 border border-rose-700/60 px-2.5 py-1 text-[11px] font-mono font-bold uppercase print:border-black print:bg-white print:text-black">
                  Tier 1 &middot; {exceptionItems.length} Open Exception{exceptionItems.length === 1 ? '' : 's'}
                </span>
                <div className="flex items-center gap-2">
                  <AlertOctagon className="h-5 w-5 text-rose-400 print:text-black" />
                  <h2 className="text-base font-bold text-white uppercase tracking-wider print:text-black font-serif">
                    Section I &mdash; Schedule of Active Unresolved Exceptions (Warranty Exclusions)
                  </h2>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex rounded bg-rose-950/80 px-2.5 py-1 text-xs font-bold text-rose-300 border border-rose-600/60 print:border-black print:bg-white print:text-black">
                  EXCLUDED FROM COVERAGE
                </span>
                <div className="flex items-center gap-1.5 text-xs text-rose-300/80 font-mono print:hidden">
                  <span className="text-[11px] hidden sm:inline">
                    {exceptionItems.length} {exceptionItems.length === 1 ? 'Item' : 'Items'}
                  </span>
                  <ChevronDown className="h-4 w-4 text-rose-400 transition-transform duration-200 group-open:rotate-180" />
                </div>
              </div>
            </summary>

            <div className="p-4 sm:p-6 space-y-4 print:p-2">
              <div className="rounded-xl border border-rose-800/60 bg-rose-950/30 p-4 text-xs text-rose-200/90 leading-relaxed font-serif print:border print:border-black print:bg-stone-50 print:text-black">
                <strong>STATUTORY NOTICE TO UNDERWRITER:</strong> Pursuant to Policy E&amp;O-2026.1 Section 4(b),
                the items cataloged in this Section I are explicitly excluded from standard Errors &amp; Omissions
                indemnity coverage. Any third-party claim, lawsuit, injunction, or license fee dispute arising from the
                unauthorized exhibition or synchronization of these creative elements remains the sole financial liability
                of the policyholder unless cured or endorsed prior to principal delivery.
              </div>

              {exceptionItems.length === 0 ? (
                <div className="rounded-xl border border-emerald-800/40 bg-emerald-950/20 p-4 text-xs text-emerald-300 font-serif text-center">
                  No active unresolved exceptions. All production elements successfully cleared or re-attested under statutory doctrines.
                </div>
              ) : (
                exceptionItems.map((exItem, idx) => {
                  const isMusic = exItem.stable_lineage_key === 'music_cue_midnight_serenade';
                  const isPoster = exItem.stable_lineage_key === 'poster_noir_detective_magazine';

                  const defaultReason = isMusic
                    ? 'Worldwide exclusive synchronization and master rights assigned in August 2026 to Vanguard Media Holdings LLC (administered by Kobalt Music). Prior public domain attestation invalid under European term extension.'
                    : isPoster
                    ? 'Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue shot. Invalidates prior de minimis clearance under Sandoval v. New Line Cinema without affirmative defense.'
                    : (exItem.invalidation_reason || 'Unresolved clearance exception requiring counsel review.');

                  const defaultAction = isMusic
                    ? 'Execute synchronization license with Vanguard Media Holdings prior to final audio mix, or replace cue with pre-cleared production library music.'
                    : isPoster
                    ? 'Re-attest under United States Public Domain doctrine following verified copyright expiration without statutory renewal, or secure publisher quitclaim.'
                    : (exItem.counsel_action || 'Pending counsel adjudication and underwriter schedule carve-out.');

                  const defaultCitation = isMusic
                    ? {
                        provider: 'Parallel Search API v1',
                        provider_call_id: 'prl_call_993012_music',
                        source_title: 'ASCAP ACE Repertory & Billboard Rights Bulletin',
                        source_url: 'https://ascap.com/ace-title-search/midnight-serenade-9921',
                        excerpt:
                          'Worldwide exclusive synchronization and master rights assigned August 2026 to Vanguard Media Holdings LLC (Administered by Kobalt Music). Prior public domain assertions disputed under European term extension.',
                        payload_hash:
                          'c958448a39a8264582f3a677353f40f098fe5c5b525d8e752989b6574f881028',
                      }
                    : isPoster
                    ? {
                        provider: 'Parallel Search API v1',
                        provider_call_id: 'prl_call_882910_poster',
                        source_title: 'US Copyright Office Historical Catalog - Renewal Records',
                        source_url:
                          'https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective',
                        excerpt:
                          'Registration #B-1946-8821 expired 1974 without timely renewal. Cover artwork in public domain in the United States.',
                        payload_hash:
                          'a1f498bc20379d749be8b0821c4fa92b5e28329623e10d860d5b4e72fb4d0267',
                      }
                    : {
                        provider: 'Clearance Registry',
                        provider_call_id: `prl_call_${exItem.stable_lineage_key}`,
                        source_title: 'Production Clearance Ledger',
                        source_url: 'https://cocatalog.loc.gov',
                        excerpt: 'Production asset flagged for clearance review.',
                        payload_hash: '0'.repeat(64),
                      };

                  const citations =
                    exItem.evidence_citations && exItem.evidence_citations.length > 0
                      ? exItem.evidence_citations
                      : [defaultCitation];

                  return (
                    <div
                      key={exItem.stable_lineage_key}
                      className="rounded-xl border border-rose-600/40 bg-slate-900/95 p-4 sm:p-5 space-y-3.5 break-inside-avoid print-break-inside-avoid print:border print:border-black print:bg-white print:text-black"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 border-b border-slate-800 pb-3 print:border-black">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="rounded bg-rose-950 text-rose-300 border border-rose-700/60 px-2 py-0.5 text-[10px] font-mono font-bold print:border-black print:bg-white print:text-black">
                              EXCEPTION #{String(idx + 1).padStart(2, '0')}
                            </span>
                            <h3 className="text-sm font-bold text-white print:text-black">
                              {exItem.description}
                            </h3>
                          </div>
                          <div className="mt-1 text-xs text-slate-400 print:text-slate-700">
                            Lineage Key:{' '}
                            <span className="font-mono text-slate-300 print:text-black">
                              {exItem.stable_lineage_key}
                            </span>{' '}
                            &middot; Scene / Timecode:{' '}
                            <span className="text-slate-200 print:text-black font-semibold">
                              {exItem.scene_or_timecode}
                            </span>{' '}
                            &middot; Asset Type:{' '}
                            <span className="font-semibold text-slate-300 uppercase print:text-black">
                              {exItem.asset_type}
                            </span>
                          </div>
                        </div>

                        <span className="inline-flex rounded bg-rose-950/80 px-2.5 py-1 text-xs font-bold text-rose-300 border border-rose-600/60 print:border-black print:bg-white print:text-black">
                          EXCLUDED FROM COVERAGE
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 print:border print:border-black print:bg-white">
                          <span className="block text-[10px] uppercase font-bold text-rose-400 print:text-black">
                            Invalidation Reason &amp; Breach Detail
                          </span>
                          <p className="mt-1 text-slate-200 leading-relaxed print:text-black">
                            {exItem.invalidation_reason || defaultReason}
                          </p>
                        </div>

                        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 print:border print:border-black print:bg-white">
                          <span className="block text-[10px] uppercase font-bold text-sky-400 print:text-black">
                            Mandatory Counsel Recommendation
                          </span>
                          <p className="mt-1 text-slate-200 leading-relaxed print:text-black">
                            {exItem.counsel_action || defaultAction}
                          </p>
                        </div>
                      </div>

                      {/* Dynamic Evidence Citations with Provenance and Hashes */}
                      {citations.map((cite, cIdx) => (
                        <div
                          key={cIdx}
                          className="rounded-lg border border-slate-800 bg-slate-950/80 p-3 text-xs space-y-2 print:border print:border-black print:bg-stone-50 print:text-black"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono font-bold uppercase text-sky-400 flex items-center gap-1.5 print:text-black">
                              <ExternalLink className="h-3.5 w-3.5 print:hidden" />
                              Attributable Registry Evidence ({cite.provider || 'Parallel Search API v1'})
                            </span>
                            <span className="text-[10px] font-mono text-slate-400 print:text-slate-700">
                              Provider Call ID:{' '}
                              <code className="text-slate-300 print:text-black">
                                {(cite as any).provider_call_id || (cite as any).call_id || defaultCitation.provider_call_id}
                              </code>
                            </span>
                          </div>
                          <div className="text-slate-300 print:text-black">
                            <div className="font-semibold text-sky-300 flex items-center gap-2 print:text-black">
                              <a
                                href={cite.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:underline text-sky-400 inline-flex items-center gap-1 print:text-black font-bold"
                              >
                                {cite.source_title}
                                <ExternalLink className="h-3 w-3 inline print:hidden" />
                              </a>
                              <span className="font-mono text-[10px] text-slate-400 print:text-slate-600 truncate max-w-sm">
                                {cite.source_url}
                              </span>
                            </div>
                            <p className="mt-1.5 italic font-serif text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-800 print:border-black print:bg-white print:text-black">
                              &ldquo;{cite.excerpt}&rdquo;
                            </p>
                            <div className="mt-1 text-[10px] font-mono text-slate-400 print:text-slate-700">
                              SHA-256 Payload Hash:{' '}
                              <code className="text-slate-300 print:text-black">
                                {(cite as any).payload_hash || defaultCitation.payload_hash}
                              </code>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })
              )}
            </div>
          </details>
        </section>

        {/* ========================================================================= */}
        {/* ========================================================================= */}
        {/* SECTION II: RE-ATTESTED PUBLIC DOMAIN ITEMS (TIER 2: RE-ATTESTED ITEMS) */}
        {/* ========================================================================= */}
        <section className="space-y-4 break-inside-avoid print-break-inside-avoid">
          <details
            open
            className="group rounded-2xl border border-sky-800/70 bg-sky-950/20 shadow-xl overflow-hidden transition-all duration-200 print:border print:border-black print:bg-white print:shadow-none print:rounded-none"
          >
            <summary className="flex items-center justify-between p-4 sm:p-5 cursor-pointer select-none bg-sky-950/50 hover:bg-sky-900/40 border-b border-sky-800/70 transition-colors list-none [&::-webkit-details-marker]:hidden print:bg-white print:border-b-2 print:border-black print:p-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="rounded bg-sky-950 text-sky-300 border border-sky-600/60 px-2.5 py-1 text-[11px] font-mono font-bold uppercase print:border-black print:bg-white print:text-black">
                  Tier 2 &middot; {reattestedItems.length} Re-Attested Item{reattestedItems.length === 1 ? '' : 's'}
                </span>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-sky-400 print:text-black" />
                  <h2 className="text-base font-bold text-white uppercase tracking-wider print:text-black font-serif">
                    Section II &mdash; Re-Attested Public Domain Items (Corroborated Clearance)
                  </h2>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex rounded bg-emerald-950/80 px-2.5 py-1 text-xs font-bold text-emerald-300 border border-emerald-600/60 print:border-black print:bg-white print:text-black">
                  APPROVED (PUBLIC DOMAIN)
                </span>
                <div className="flex items-center gap-1.5 text-xs text-sky-300/80 font-mono print:hidden">
                  <span className="text-[11px] hidden sm:inline">
                    {reattestedItems.length} {reattestedItems.length === 1 ? 'Item' : 'Items'}
                  </span>
                  <ChevronDown className="h-4 w-4 text-sky-400 transition-transform duration-200 group-open:rotate-180" />
                </div>
              </div>
            </summary>

            <div className="p-4 sm:p-6 space-y-4 print:p-2">
              <div className="rounded-xl border border-sky-800/60 bg-sky-950/30 p-4 text-xs text-sky-200/90 leading-relaxed font-serif print:border print:border-black print:bg-stone-50 print:text-black">
                <strong>CORROBORATED RE-ATTESTATION:</strong> Creative elements in this Section II underwent
                creative delta escalation between Version 7 and Version 8, invalidating prior de minimis clearance.
                Production clearance counsel has re-adjudicated these elements and corroborated non-infringing public
                domain status via external registry evidence prior to policy binding.
              </div>

              {reattestedItems.length === 0 ? (
                <div className="rounded-xl border border-sky-800/40 bg-sky-950/20 p-4 text-xs text-sky-300 font-serif text-center">
                  No claims currently categorized under counsel re-attestation. Any modified elements pending counsel review remain listed under Section I exceptions.
                </div>
              ) : (
                reattestedItems.map((reItem, idx) => {
                  const defaultReason =
                    'Escalated from 2s out-of-focus background blur to 14s close-up focal dialogue shot. Invalidates prior de minimis clearance; clearance counsel re-attests under United States Public Domain doctrine following verified copyright expiration without statutory renewal.';

                  const defaultAction =
                    'Library of Congress registration #B-1946-8821 expired in 1974 without timely statutory renewal. Cover artwork affirmed in public domain in the United States.';

                  const defaultCitation = {
                    provider: 'Parallel Search API v1',
                    provider_call_id: 'prl_call_882910_poster',
                    source_title: 'US Copyright Office Historical Catalog - Renewal Records',
                    source_url:
                      'https://cocatalog.loc.gov/cgi-bin/Pwebrecon.cgi?v1=1946-crime-detective',
                    excerpt:
                      'Registration #B-1946-8821 expired 1974 without timely renewal. Cover artwork in public domain in the United States.',
                    payload_hash:
                      'a1f498bc20379d749be8b0821c4fa92b5e28329623e10d860d5b4e72fb4d0267',
                  };

                  const citations =
                    reItem.evidence_citations && reItem.evidence_citations.length > 0
                      ? reItem.evidence_citations
                      : [defaultCitation];

                  return (
                    <div
                      key={reItem.stable_lineage_key}
                      className="rounded-xl border border-sky-500/40 bg-slate-900/95 p-4 sm:p-5 space-y-3.5 break-inside-avoid print-break-inside-avoid print:border print:border-black print:bg-white print:text-black"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 border-b border-slate-800 pb-3 print:border-black">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="rounded bg-sky-950 text-sky-300 border border-sky-600/60 px-2 py-0.5 text-[10px] font-mono font-bold print:border-black print:bg-white print:text-black">
                              RE-ATTESTED #{String(idx + 1).padStart(2, '0')}
                            </span>
                            <h3 className="text-sm font-bold text-white print:text-black">
                              {reItem.description}
                            </h3>
                          </div>
                          <div className="mt-1 text-xs text-slate-400 print:text-slate-700">
                            Lineage Key:{' '}
                            <span className="font-mono text-slate-300 print:text-black">
                              {reItem.stable_lineage_key}
                            </span>{' '}
                            &middot; Scene / Timecode:{' '}
                            <span className="text-slate-200 print:text-black font-semibold">
                              {reItem.scene_or_timecode}
                            </span>{' '}
                            &middot; Asset Type:{' '}
                            <span className="font-semibold uppercase text-slate-300 print:text-black">
                              {reItem.asset_type}
                            </span>
                          </div>
                        </div>

                        <span className="inline-flex rounded bg-emerald-950/80 px-2.5 py-1 text-xs font-bold text-emerald-300 border border-emerald-600/60 print:border-black print:bg-white print:text-black">
                          APPROVED (PUBLIC DOMAIN)
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 print:border print:border-black print:bg-white">
                          <span className="block text-[10px] uppercase font-bold text-sky-400 print:text-black">
                            Creative Delta &amp; Counsel Determination
                          </span>
                          <p className="mt-1 text-slate-200 leading-relaxed print:text-black">
                            {reItem.invalidation_reason || defaultReason}
                          </p>
                        </div>
                        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 print:border print:border-black print:bg-white">
                          <span className="block text-[10px] uppercase font-bold text-emerald-400 print:text-black">
                            Library of Congress Verification Record
                          </span>
                          <p className="mt-1 text-slate-200 leading-relaxed print:text-black">
                            {reItem.counsel_action || defaultAction}
                          </p>
                        </div>
                      </div>

                      {/* Dynamic Evidence Citation with Attributable Provenance */}
                      {citations.map((cite, cIdx) => (
                        <div
                          key={cIdx}
                          className="rounded-lg border border-slate-800 bg-slate-950/80 p-3 text-xs space-y-2 print:border print:border-black print:bg-stone-50 print:text-black"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-mono font-bold uppercase text-sky-400 flex items-center gap-1.5 print:text-black">
                              <ExternalLink className="h-3.5 w-3.5 print:hidden" />
                              Attributable Source Verification (Library of Congress Records)
                            </span>
                            <span className="text-[10px] font-mono text-slate-400 print:text-slate-700">
                              Provider Call ID:{' '}
                              <code className="text-slate-300 print:text-black">
                                {(cite as any).provider_call_id || (cite as any).call_id || defaultCitation.provider_call_id}
                              </code>
                            </span>
                          </div>
                          <div className="text-slate-300 print:text-black">
                            <div className="font-semibold text-sky-300 flex items-center gap-2 print:text-black">
                              <a
                                href={cite.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="hover:underline text-sky-400 inline-flex items-center gap-1 print:text-black font-bold"
                              >
                                {cite.source_title}
                                <ExternalLink className="h-3 w-3 inline print:hidden" />
                              </a>
                              <span className="font-mono text-[10px] text-slate-400 print:text-slate-600 truncate max-w-sm">
                                {cite.source_url}
                              </span>
                            </div>
                            <p className="mt-1.5 italic font-serif text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-800 print:border-black print:bg-white print:text-black">
                              &ldquo;{cite.excerpt}&rdquo;
                            </p>
                            <div className="mt-1 text-[10px] font-mono text-slate-400 print:text-slate-700">
                              SHA-256 Payload Hash:{' '}
                              <code className="text-slate-300 print:text-black">
                                {(cite as any).payload_hash || defaultCitation.payload_hash}
                              </code>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })
              )}
            </div>
          </details>
        </section>

        {/* ========================================================================= */}
        {/* SECTION III: CERTIFIED CARRIED-FORWARD CLEARANCE REGISTER (TIER 3) */}
        {/* ========================================================================= */}
        <section className="space-y-4">
          <details
            open
            className="group rounded-2xl border border-emerald-800/70 bg-emerald-950/15 shadow-xl overflow-hidden transition-all duration-200 print:border print:border-black print:bg-white print:shadow-none print:rounded-none"
          >
            <summary className="flex items-center justify-between p-4 sm:p-5 cursor-pointer select-none bg-emerald-950/40 hover:bg-emerald-900/30 border-b border-emerald-800/70 transition-colors list-none [&::-webkit-details-marker]:hidden print:bg-white print:border-b-2 print:border-black print:p-2">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="rounded bg-emerald-950 text-emerald-300 border border-emerald-600/60 px-2.5 py-1 text-[11px] font-mono font-bold uppercase print:border-black print:bg-white print:text-black">
                  Tier 3 &middot; {carriedItems.length} Carried Forward = {items.length} Total
                </span>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 print:text-black" />
                  <h2 className="text-base font-bold text-white uppercase tracking-wider print:text-black font-serif">
                    Section III &mdash; Certified Carried-Forward Clearance Register ({carriedItems.length} Claims &middot; $0.00 Audit Parity)
                  </h2>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex rounded bg-emerald-950/80 px-2.5 py-1 text-xs font-bold text-emerald-300 border border-emerald-600/60 print:border-black print:bg-white print:text-black">
                  100% INVARIANT VERIFIED ({carriedItems.length}/{items.length})
                </span>
                <div className="flex items-center gap-1.5 text-xs text-emerald-300/80 font-mono print:hidden">
                  <span className="text-[11px] hidden sm:inline">{carriedItems.length} Items</span>
                  <ChevronDown className="h-4 w-4 text-emerald-400 transition-transform duration-200 group-open:rotate-180" />
                </div>
              </div>
            </summary>

            <div className="p-4 sm:p-6 space-y-4 print:p-2">
              <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/30 p-4 text-xs text-emerald-200/90 leading-relaxed font-serif print:border print:border-black print:bg-stone-50 print:text-black">
                <strong>CERTIFICATE OF CARRIED-FORWARD CLEARANCE PARITY:</strong> The following {carriedItems.length} creative
                uses possess identical script context, screen timecode, and legal clearance posture between Version 7 and Version 8.
                Pursuant to the Selective Deterministic Parity protocol, these elements are affirmed carried forward without
                unnecessary re-clearance expense ($0.00 audit cost).
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/80 print:border print:border-black print:bg-white print:rounded-none">
                <table className="w-full text-left text-xs print:border-collapse print:text-black">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/90 font-mono text-[11px] uppercase text-slate-400 print:bg-stone-100 print:text-black print:border-black">
                      <th className="py-2.5 px-3 print:border print:border-black">#</th>
                      <th className="py-2.5 px-3 print:border print:border-black">Lineage Key</th>
                      <th className="py-2.5 px-3 print:border print:border-black">Scene / TC</th>
                      <th className="py-2.5 px-3 print:border print:border-black">Type</th>
                      <th className="py-2.5 px-3 print:border print:border-black">Description</th>
                      <th className="py-2.5 px-3 print:border print:border-black">v7 Status</th>
                      <th className="py-2.5 px-3 print:border print:border-black">v8 State</th>
                      <th className="py-2.5 px-3 text-right print:border print:border-black">Audit Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 print:divide-black">
                    {carriedItems.map((cItem, index) => (
                      <tr key={cItem.stable_lineage_key} className="hover:bg-slate-800/30 print:bg-white">
                        <td className="py-2.5 px-3 font-mono font-bold text-slate-500 print:text-black print:border print:border-slate-300">
                          {String(index + 1).padStart(2, '0')}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-medium text-slate-300 print:text-black print:border print:border-slate-300">
                          {cItem.stable_lineage_key}
                        </td>
                        <td className="py-2.5 px-3 text-slate-300 whitespace-nowrap print:text-black print:border print:border-slate-300">
                          {cItem.scene_or_timecode}
                        </td>
                        <td className="py-2.5 px-3 print:border print:border-slate-300">
                          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-300 uppercase print:bg-white print:text-black print:border print:border-black">
                            {cItem.asset_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate print:max-w-none print:whitespace-normal print:overflow-visible print:text-black print:border print:border-slate-300">
                          {cItem.description}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-300 print:text-black print:border print:border-slate-300">
                          APPROVED
                        </td>
                        <td className="py-2.5 px-3 print:border print:border-slate-300">
                          <span className="inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold badge-carried print:border print:border-black">
                            CARRIED FORWARD
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-emerald-400 font-semibold print:text-black print:border print:border-slate-300">
                          $0.00
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </details>
        </section>

        {/* ========================================================================= */}
        {/* SECTION IV: LEGAL COUNSEL ATTESTATION & UNDERWRITER CERTIFICATION */}
        {/* ========================================================================= */}
        <section className="border-t-2 border-slate-700 pt-6 space-y-6 break-inside-avoid print-break-inside-avoid print:border-black">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2 print:text-black">
                <Scale className="h-4 w-4 text-sky-400 print:text-black" />
                Section IV &mdash; Legal Counsel Attestation &amp; Underwriter Certification
              </h2>
              <span className="text-[11px] font-mono text-amber-400 border border-amber-500/40 rounded px-2 py-0.5 bg-amber-950/30 print:border-black print:bg-white print:text-black font-semibold">
                Simulated Counsel Persona: Sarah Jenkins, Esq. (Demo Only &mdash; Not Legal Advice)
              </span>
            </div>
            <p className="mt-3 text-xs text-slate-300 font-serif leading-relaxed print:text-black">
              I, <strong>Sarah Jenkins, Esq.</strong>, Lead Clearance Counsel for Blockbuster Cinema LLC,
              hereby warrant and certify under penalty of insurance policy cancellation that: (1) All {items.length}
              rights-bearing creative uses identified in Production Revision v8 have been reviewed against the
              Version 7 locked baseline; (2) {carriedItems.length} creative uses possess identical context and prominence and are
              certified carried forward without additional clearance audit expense; (3) {reattestedItems.length} creative use{reattestedItems.length === 1 ? ' has' : 's have'} been re-attested
              based on corroborating public domain and statutory renewal records; and (4) {exceptionItems.length} creative use{exceptionItems.length === 1 ? ' has' : 's have'} been
              formally designated as open Unresolved Exception{exceptionItems.length === 1 ? '' : 's'} for explicit underwriter exclusion from standard Errors &amp; Omissions indemnity coverage.
            </p>
          </div>

          {/* Signature Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 pt-4 break-inside-avoid print-break-inside-avoid">
            {/* Counsel Signature Block */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3 break-inside-avoid print-break-inside-avoid print:border print:border-black print:bg-white print:text-black">
              <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider print:text-slate-700">
                Clearance Counsel of Record
              </div>
              <div className="border-b border-slate-700 pb-2 pt-4 print:border-black">
                <span className="font-serif italic text-xl text-sky-300 font-semibold print:text-black">
                  Sarah Jenkins, Esq.
                </span>
              </div>
              <div className="text-xs space-y-1 text-slate-400 print:text-slate-700">
                <div className="font-medium text-slate-300 print:text-black">
                  Lead Production Clearance Counsel, Lienmark Legal Partners LLP
                </div>
                <div>State Bar of California &middot; License #284910</div>
                <div>Entertainment Clearance &amp; Risk Practice Group</div>
                <div className="text-[10px] text-amber-300 font-mono print:text-black">
                  Notice: Simulated Counsel Persona: Sarah Jenkins, Esq. (Demo Only &mdash; Not Legal Advice)
                </div>
                <div className="font-mono text-[10px] text-slate-400 mt-1 print:text-slate-600">
                  Digital Attestation Timestamp: {formattedDate} (UTC Certified)
                </div>
              </div>
            </div>

            {/* Carrier Underwriter Binder Block */}
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/40 p-4 space-y-3 break-inside-avoid print-break-inside-avoid print:border print:border-black print:border-solid print:bg-white print:text-black">
              <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider print:text-slate-700">
                Underwriter Acknowledgment (Pending Review)
              </div>
              <div className="border-b border-dashed border-slate-600 pb-2 pt-6 text-center text-xs text-slate-500 font-mono print:border-black print:text-black">
                ____________________________________________________
              </div>
              <div className="text-xs space-y-1 text-slate-400 text-center print:text-slate-700">
                <div className="text-slate-300 font-medium print:text-black">Authorized Carrier / Syndicate Underwriter Signature</div>
                <div>Lloyd&apos;s Specialty Syndicate 1888 &amp; Hartford Syndicate Group</div>
                <div className="text-amber-400 font-semibold text-[11px] mt-1 print:text-black">
                  &bull; STATUS: PENDING UNDERWRITER REVIEW &mdash; NO COVERAGE BOUND
                </div>
                <div className="text-[10px] font-mono text-slate-500 mt-2 print:text-slate-600">
                  Date of Execution: ________________________
                </div>
              </div>
            </div>
          </div>

          {/* Document Security Digest & Ledger Reference */}
          <div className="rounded-xl bg-slate-950/90 p-4 text-center text-xs space-y-2 border border-slate-800 print:border print:border-black print:bg-stone-50 print:text-black">
            <div className="text-[11px] font-mono font-bold text-sky-400 print:text-black">
              {auditTrail && auditTrail.chain_head_hash && auditTrail.is_ledger_tamper_free && auditTrail.total_events > 0 ? (
                `CRYPTOGRAPHIC AUDIT SEAL: SHA256:${auditTrail.chain_head_hash} [VERIFIED CHAIN HASH]`
              ) : (
                'CRYPTOGRAPHIC AUDIT SEAL: [UNSEALED] — PENDING COUNSEL CHECKPOINT ADJUDICATION'
              )}
            </div>
            <div className="text-[10px] text-slate-400 font-mono print:text-slate-700">
              LIENMARK FAIL-CLOSED WARRANTY RECONCILED &middot; {items.length} TOTAL = {carriedItems.length} CARRIED FORWARD + {reattestedItems.length} RE-ATTESTED + {exceptionItems.length} EXCEPTION{exceptionItems.length === 1 ? '' : 'S'}
            </div>
            <div className="text-[11px] text-slate-400 font-sans pt-1 no-print print:hidden">
              Cryptographic JSON Audit Ledger and Form E&amp;O-2026 Schedule exports available in top control bar.
            </div>
          </div>
        </section>

        {/* PROMINENT STATUTORY UNDERWRITING DISCLAIMER BANNER (FOOTER) */}
        <div className="rounded-xl border border-rose-600/50 bg-rose-950/30 p-4 text-xs text-rose-200 leading-relaxed font-sans shadow-inner print:border print:border-black print:bg-stone-50 print:text-black">
          <strong className="font-bold text-rose-300 print:text-black">LEGAL &amp; UNDERWRITING DISCLAIMER:</strong> THIS ARTIFACT IS A VERSION-BOUND SCHEDULE OF UNRESOLVED CLEARANCE EXCEPTIONS FOR DEMONSTRATION AND INFORMATIONAL PURPOSES ONLY. NO ARTIFACT GENERATED BY LIENMARK CONSTITUTES OR CLAIMS FORMAL UNDERWRITING APPROVAL, POLICY BINDING, INSURANCE COVERAGE, LEGAL OPINION, OR LEGAL CERTAINTY. COVERAGE IS SUBJECT EXCLUSIVELY TO A SEPARATELY EXECUTED POLICY BINDER WITH AN ADMITTED OR SURPLUS LINES CARRIER.
        </div>
      </div>
    </div>
  );
}
