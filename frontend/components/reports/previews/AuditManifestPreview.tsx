'use client';

/**
 * AuditManifestPreview Component
 * Forensic ISO 27001 / SOC 2 Type II Legal Audit Manifest & JSON Syntax Viewer.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState, useCallback } from 'react';
import {
  ShieldCheck,
  Copy,
  Check,
  FileCode,
  KeyRound,
  Hash,
  Fingerprint,
} from 'lucide-react';
import { LegalAuditManifestResponse } from '../types';

interface AuditManifestPreviewProps {
  readonly manifest: LegalAuditManifestResponse;
}

function renderManifestHeader(manifest: LegalAuditManifestResponse): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800/80 pb-4">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Fingerprint className="h-5 w-5 text-emerald-400" />
          <h3 className="text-base font-bold text-white tracking-tight">
            ISO 27001 / SOC 2 TYPE II AUDIT MANIFEST
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Forensic Cryptographic Manifest • Conforming to {manifest.iso_standard}
        </p>
      </div>
      <div className="flex items-center gap-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 text-xs text-emerald-300 font-mono">
        <ShieldCheck className="h-4 w-4 text-emerald-400" />
        <span>Chain Verified ({manifest.total_ledger_events} Blocks)</span>
      </div>
    </div>
  );
}

function renderHashDigestRow(manifest: LegalAuditManifestResponse): React.JSX.Element {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 space-y-1">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-400 uppercase">
          <Hash className="h-3 w-3 text-sky-400" />
          <span>Ledger Head Hash</span>
        </div>
        <p className="text-sky-300 break-all bg-black/40 p-1.5 rounded text-[11px]">
          {manifest.head_hash}
        </p>
      </div>
      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 space-y-1">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-400 uppercase">
          <KeyRound className="h-3 w-3 text-purple-400" />
          <span>Audit Trail Digest</span>
        </div>
        <p className="text-purple-300 break-all bg-black/40 p-1.5 rounded text-[11px]">
          {manifest.audit_trail_digest}
        </p>
      </div>
    </div>
  );
}

function renderSignatories(manifest: LegalAuditManifestResponse): React.JSX.Element {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 space-y-2">
      <span className="text-[10px] uppercase font-mono font-semibold text-slate-400 block">
        Accountable Signatories
      </span>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {manifest.signatories.map((sig, i) => (
          <div
            key={i}
            className="rounded-lg bg-[#0B0F17] border border-slate-800/80 p-2 text-xs font-mono"
          >
            <span className="text-slate-500 text-[10px] block">{sig.role}</span>
            <span className="text-white font-bold block truncate">{sig.name}</span>
            {sig.key_id && (
              <span className="text-slate-400 text-[9px] block truncate">
                Key: {sig.key_id}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export function AuditManifestPreview({ manifest }: AuditManifestPreviewProps): React.JSX.Element {
  const [copied, setCopied] = useState<boolean>(false);
  const jsonContent = JSON.stringify(manifest, null, 2);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(jsonContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [jsonContent]);

  return (
    <div className="space-y-4 text-slate-200">
      <div className="rounded-2xl border border-slate-800 bg-[#0B0F17] p-5 shadow-2xl space-y-4">
        {renderManifestHeader(manifest)}
        {renderHashDigestRow(manifest)}
        {renderSignatories(manifest)}

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400">
              <FileCode className="h-4 w-4 text-sky-400" />
              <span>Canonical Manifest JSON Payload</span>
            </div>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs font-mono text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 text-slate-400" />
                  <span>Copy JSON</span>
                </>
              )}
            </button>
          </div>

          <pre className="max-h-72 overflow-y-auto rounded-xl bg-slate-950 p-4 border border-slate-800/80 font-mono text-xs text-emerald-300 leading-relaxed whitespace-pre select-all">
            {jsonContent}
          </pre>
        </div>
      </div>
    </div>
  );
}
