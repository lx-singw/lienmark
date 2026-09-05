'use client';

/**
 * Client Print and Navigation Button for Form E&O-2026
 * Handles window.print() trigger in a client component boundary.
 */

import React from 'react';
import Link from 'next/link';
import { Printer, ArrowLeft, Download, ShieldCheck } from 'lucide-react';

interface PrintButtonProps {
  scheduleId: string;
}

export function PrintButton({ scheduleId }: PrintButtonProps) {
  const handlePrint = () => {
    if (typeof window !== 'undefined') {
      window.print();
    }
  };

  return (
    <div className="no-print mb-8 rounded-xl border border-slate-800 bg-[#131b2e] p-4 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
      <div className="flex items-center gap-3">
        <Link
          href="/"
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
        <div className="hidden sm:block">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
            <ShieldCheck className="h-4 w-4" />
            <span>Audit Trail Reconciled &middot; Ready for Binder</span>
          </div>
          <p className="text-[11px] text-slate-400">
            Schedule ID: <span className="font-mono">{scheduleId}</span>
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <a
          href="/api/reports/export?format=json"
          download={`form_eo_2026_${scheduleId}.json`}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 hover:bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:text-white transition-colors"
        >
          <Download className="h-4 w-4 text-emerald-400" />
          Download JSON Schedule
        </a>
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 rounded-lg bg-sky-500 hover:bg-sky-400 px-4 py-2 text-xs font-bold text-slate-950 transition-all shadow-md shadow-sky-500/20 active:scale-95"
        >
          <Printer className="h-4 w-4" />
          Print Form E&amp;O-2026 (PDF)
        </button>
      </div>
    </div>
  );
}

export default PrintButton;
