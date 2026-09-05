'use client';

/**
 * Lienmark Export & Form E&O-2026 Exceptions Schedule Component
 * Facilitates SSR printable schedule navigation, client-side JSON schedule generation,
 * and displays mandatory statutory underwriting disclaimers.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState } from 'react';
import Link from 'next/link';
import {
  FileSpreadsheet,
  Download,
  ShieldAlert,
  Printer,
  FileCheck,
  CheckCircle2,
} from 'lucide-react';
import { EvaluatedClaim, ExceptionsSchedule } from '@/lib/types';

export interface ExportActionComponentProps {
  projectId?: string;
  projectName?: string;
  claims: ReadonlyArray<EvaluatedClaim>;
  exceptionsScheduleUrl?: string;
  className?: string;
}

export const ExportActionComponent: React.FC<ExportActionComponentProps> = ({
  projectId = 'proj_blockbuster_cinema',
  projectName = 'Shadows Over Broadway',
  claims,
  exceptionsScheduleUrl = '/report/proj_blockbuster_cinema',
  className = '',
}) => {
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const [downloadSuccess, setDownloadSuccess] = useState<boolean>(false);

  // Client-side JSON Schedule generation with automatic object URL memory cleanup
  const handleDownloadJsonSchedule = () => {
    try {
      setIsDownloading(true);

      const scheduleExport = {
        schedule_id: `sched_${projectId}_${Date.now()}`,
        production_metadata: {
          project_id: projectId,
          production_title: projectName,
          base_version_id: 'v7',
          target_version_id: 'v8',
          exported_at: new Date().toISOString(),
          policy_number: 'E&O-2026.1-DEVPOST',
        },
        carrier_warranty: {
          carrier_name: 'Standard Entertainment & Media Underwriters Syndicate',
          warranty_clause:
            'Warranted clearance schedule of exceptions; uncleared and unlisted rights are excluded from coverage.',
          underwriter_status: 'PENDING_REVIEW',
        },
        claims_inventory: claims.map((c) => ({
          stable_lineage_key: c.stable_lineage_key,
          asset_type: c.asset_type,
          description: c.description,
          scene_or_timecode: c.scene,
          state: c.state,
          reason_code: c.reason_code,
          revalidation_action: c.revalidation_action,
          evidence_citation: c.evidence
            ? {
                provider: c.evidence.provider,
                source_title: c.evidence.source_title,
                source_url: c.evidence.source_url,
                stance: c.evidence.stance,
              }
            : null,
        })),
        disclaimer:
          'Lienmark provides clearance decision support and does not bind insurance coverage or certify legal certainty.',
      };

      const jsonBlob = new Blob([JSON.stringify(scheduleExport, null, 2)], {
        type: 'application/json',
      });
      const downloadUrl = URL.createObjectURL(jsonBlob);
      const downloadAnchor = document.createElement('a');
      downloadAnchor.href = downloadUrl;
      downloadAnchor.download = `Form_EO_2026_Exceptions_Schedule_${projectId}.json`;
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();

      // Clean up DOM and revoke object URL to prevent memory leaks in SPA session
      document.body.removeChild(downloadAnchor);
      setTimeout(() => {
        URL.revokeObjectURL(downloadUrl);
        setIsDownloading(false);
        setDownloadSuccess(true);
        setTimeout(() => setDownloadSuccess(false), 3000);
      }, 150);
    } catch (err) {
      console.error('[ExportActionComponent] Error generating JSON download:', err);
      setIsDownloading(false);
    }
  };

  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-[#131b2e] p-5 sm:p-6 shadow-xl space-y-4 ${className}`}
      role="region"
      aria-label="Underwriting Export Actions & Statutory Legal Notice"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-amber-400" aria-hidden="true" />
            <span>Underwriter Submission &amp; Exceptions Schedule Deliverables</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Prepare Form E&O-2026 Schedule for carrier broker submission or download offline audit payload.
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
          <Link
            href={exceptionsScheduleUrl}
            className="flex items-center gap-2 rounded-lg bg-amber-500 hover:bg-amber-400 px-4 py-2 text-xs font-bold text-slate-950 transition-all shadow-md active:scale-95 focus:outline-none focus:ring-2 focus:ring-amber-300"
            aria-label="Open SSR Printable Form E&O-2026 Schedule"
          >
            <Printer className="h-4 w-4" aria-hidden="true" />
            <span>Open Printable Form E&O-2026</span>
          </Link>

          <button
            type="button"
            onClick={handleDownloadJsonSchedule}
            disabled={isDownloading}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/90 hover:bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-60"
            aria-label="Download Form E&O-2026 JSON Exceptions Schedule"
          >
            {downloadSuccess ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-emerald-400" aria-hidden="true" />
                <span className="text-emerald-300">Downloaded</span>
              </>
            ) : (
              <>
                <Download className="h-4 w-4 text-sky-400" aria-hidden="true" />
                <span>Download JSON Schedule</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Statutory Underwriting Disclaimer */}
      <div
        className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-3.5 text-xs text-slate-400 flex items-start gap-2.5 leading-relaxed"
        role="note"
        aria-label="Statutory Underwriting Disclaimer"
      >
        <ShieldAlert className="h-4 w-4 text-amber-400/80 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-1">
          <p className="font-semibold text-slate-300">
            Statutory Legal Underwriting Disclaimer:
          </p>
          <p className="text-[11px] text-slate-400">
            Lienmark provides clearance decision support and does not bind insurance coverage or certify legal certainty.
            All determinations and risk ratings are subject to carrier policy terms, policy warranty conditions, and formal
            endorsement by authorized clearance legal counsel.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ExportActionComponent;
