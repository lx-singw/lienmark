'use client';

/**
 * Crypto Verification Badge Component
 * Renders an interactive cryptographic integrity badge for ledger blocks.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import { Lock, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface CryptoVerificationBadgeProps {
  readonly eventId: string;
  readonly sequenceNumber: number;
  readonly isValid?: boolean;
  readonly onVerify: (eventId: string) => void;
}

export function CryptoVerificationBadge({
  eventId,
  sequenceNumber,
  isValid = true,
  onVerify,
}: CryptoVerificationBadgeProps): React.JSX.Element {
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onVerify(eventId);
  };

  return (
    <button
      onClick={handleClick}
      title="Click to view deep cryptographic block proof"
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-mono font-bold transition-all border ${
        isValid
          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/20'
          : 'bg-rose-500/10 text-rose-300 border-rose-500/30 hover:bg-rose-500/20'
      }`}
    >
      {isValid ? (
        <Lock className="h-3 w-3 text-emerald-400" />
      ) : (
        <ShieldAlert className="h-3 w-3 text-rose-400" />
      )}
      <span>Block #{sequenceNumber}</span>
      <span className="text-slate-500">·</span>
      <span>{isValid ? 'Verified' : 'Invalid'}</span>
    </button>
  );
}
