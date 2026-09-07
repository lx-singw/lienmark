'use client';

/**
 * Crypto Verification Modal Component
 * Deep cryptographic inspection modal showing SHA-256 block hash, back-pointers, and dual signatures.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useEffect, useState } from 'react';
import { X, Lock, CheckCircle2, ShieldAlert, Key, Hash, FileCode } from 'lucide-react';
import { LedgerVerificationResponse } from '../types';

interface CryptoVerificationModalProps {
  readonly eventId: string;
  readonly onClose: () => void;
}

export function CryptoVerificationModal({
  eventId,
  onClose,
}: CryptoVerificationModalProps): React.JSX.Element {
  const [data, setData] = useState<LedgerVerificationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function verifyBlock() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/v1/ledger/verify/${encodeURIComponent(eventId)}`);
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const payload = (await res.json()) as LedgerVerificationResponse;
        if (isMounted) setData(payload);
      } catch (err) {
        if (isMounted) setError(err instanceof Error ? err.message : 'Verification failed');
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    verifyBlock();
    return () => {
      isMounted = false;
    };
  }, [eventId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl border border-slate-800 bg-[#0e1424] shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <Lock className="h-5 w-5 text-emerald-400" />
            <div>
              <h2 className="text-base font-bold text-white">Cryptographic Block Proof</h2>
              <p className="text-xs font-mono text-slate-400">Event ID: {eventId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {loading && (
            <div className="py-12 text-center text-xs font-mono text-slate-400">
              Verifying cryptographic hash chain and digital signatures...
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-4 text-xs text-rose-300">
              {error}
            </div>
          )}

          {data && (
            <>
              <div
                className={`flex items-start gap-3 rounded-xl border p-4 ${
                  data.is_valid
                    ? 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300'
                    : 'border-rose-500/40 bg-rose-950/20 text-rose-300'
                }`}
              >
                {data.is_valid ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <ShieldAlert className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider">
                    {data.is_valid ? 'Cryptographic Proof Verified' : 'Integrity Check Failed'}
                  </h4>
                  <p className="text-xs mt-1 text-slate-300 leading-relaxed">
                    {data.verification_message}
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-3 font-mono text-xs">
                <h4 className="text-[11px] font-bold text-slate-400 uppercase flex items-center gap-1.5">
                  <Hash className="h-3.5 w-3.5 text-sky-400" />
                  <span>Hash Continuity &amp; Back-Pointers</span>
                </h4>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500">BLOCK SEQUENCE:</span>
                  <p className="text-white font-bold">#{data.sequence_number}</p>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500">CURRENT BLOCK ENTRY HASH:</span>
                  <p className="text-sky-300 break-all bg-slate-900/80 p-2 rounded border border-slate-800">
                    {data.entry_hash}
                  </p>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500">PREVIOUS BLOCK PARENT HASH:</span>
                  <p className="text-slate-300 break-all bg-slate-900/80 p-2 rounded border border-slate-800">
                    {data.previous_event_hash}
                  </p>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] text-slate-500">PAYLOAD CANONICAL DIGEST:</span>
                  <p className="text-emerald-300 break-all bg-slate-900/80 p-2 rounded border border-slate-800">
                    {data.payload_digest}
                  </p>
                </div>
              </div>

              {data.dual_signatures.length > 0 && (
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-3">
                  <h4 className="text-[11px] font-mono font-bold text-slate-400 uppercase flex items-center gap-1.5">
                    <Key className="h-3.5 w-3.5 text-amber-400" />
                    <span>Cryptographic Digital Signatures</span>
                  </h4>
                  {data.dual_signatures.map((sig, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1 font-mono text-xs"
                    >
                      <div className="flex items-center justify-between text-slate-400 text-[11px]">
                        <span>Signer: <span className="text-white font-bold">{sig.role}</span> ({sig.actor_id})</span>
                        <span>Key ID: {sig.key_id}</span>
                      </div>
                      <p className="text-[10px] text-slate-500 break-all pt-1">
                        Sig: {sig.signature_hex}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 space-y-2">
                <h4 className="text-[11px] font-mono font-bold text-slate-400 uppercase flex items-center gap-1.5">
                  <FileCode className="h-3.5 w-3.5 text-purple-400" />
                  <span>Canonical Block Payload</span>
                </h4>
                <pre className="max-h-48 overflow-y-auto rounded-lg bg-slate-900/90 border border-slate-800 p-3 text-[11px] font-mono text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {JSON.stringify(data.canonical_payload, null, 2)}
                </pre>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
