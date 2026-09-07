'use client';

/**
 * Lienmark Evidence & Provenance Page
 * Rights corroboration repository: LOC catalog, public domain registries, and contract shields.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import Link from 'next/link';
import { FileCheck2, ExternalLink, ShieldCheck, Database, Layers } from 'lucide-react';

const EVIDENCE_RECORDS = [
  {
    id: 'ev_loc_1946_noir',
    title: 'US Copyright Office Catalog (1946 Registration)',
    claimKey: 'poster_noir_detective_magazine',
    doctrine: 'Public Domain (Expired / Non-Renewed)',
    citation: 'Catalog of Copyright Entries, 3d Ser., Vol. 1, Pt. 2 (1946); LOC Search Report #PD-2026-09.',
    status: 'Corroborated',
    url: 'https://cocatalog.loc.gov',
  },
  {
    id: 'ev_sync_vanguard_2026',
    title: 'ASCAP ACE Index & Vanguard Assignment Notice',
    claimKey: 'music_cue_midnight_serenade',
    doctrine: 'Adverse Rights Dispute',
    citation: 'ASCAP Work ID #44021981; Global sync assignment to Vanguard Media Corp recorded Aug 14, 2026.',
    status: 'Adverse Exception',
    url: 'https://www.ascap.com/repertory',
  },
  {
    id: 'ev_contract_shield_s205',
    title: 'Paramount Production Agreement Release #882',
    claimKey: 'vintage_prop_radio_phonograph',
    doctrine: '17 U.S.C. § 205(e) Nonexclusive License Shield',
    citation: 'Executed written instrument dated 2026-08-01 signed by authorized licensor.',
    status: 'Protected',
    url: 'https://cocatalog.loc.gov',
  },
];

export default function EvidencePage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="border-b border-slate-800/80 pb-5">
        <div className="flex items-center gap-2.5">
          <h1 className="text-xl font-bold tracking-tight text-white">Evidence &amp; Provenance Explorer</h1>
          <span className="rounded-full bg-sky-500/20 border border-sky-500/40 px-2.5 py-0.5 text-xs font-mono font-bold text-sky-300">
            {EVIDENCE_RECORDS.length} Corroborated Citations
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Statutory chain-of-title records, LOC catalog verifications, and private contract release shields.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="rounded-xl border border-slate-800 bg-[#0e1424]/70 p-4 space-y-1">
          <span className="text-[11px] text-slate-400 font-medium">Public Records Verified</span>
          <p className="text-xl font-bold font-mono text-emerald-400">10 Claims</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-[#0e1424]/70 p-4 space-y-1">
          <span className="text-[11px] text-slate-400 font-medium">Contract Shields (§ 205e)</span>
          <p className="text-xl font-bold font-mono text-sky-400">1 Active</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-[#0e1424]/70 p-4 space-y-1">
          <span className="text-[11px] text-slate-400 font-medium">Adverse Conflicts</span>
          <p className="text-xl font-bold font-mono text-rose-400">1 Exception</p>
        </div>
      </div>

      <div className="space-y-3">
        {EVIDENCE_RECORDS.map((rec) => (
          <div
            key={rec.id}
            className="rounded-xl border border-slate-800 bg-[#0e1424]/80 p-4 space-y-2 hover:border-slate-700/80 transition-all"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="text-[10px] font-mono text-sky-400 font-semibold">{rec.doctrine}</span>
                <h3 className="text-sm font-bold text-white mt-0.5">{rec.title}</h3>
                <p className="text-xs text-slate-400 font-mono">Bound Claim: {rec.claimKey}</p>
              </div>
              <a
                href={rec.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:text-white transition-colors"
              >
                <span>View Source</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <p className="text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 font-mono leading-relaxed">
              {rec.citation}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
