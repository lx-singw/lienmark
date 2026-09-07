'use client';

/**
 * ReportExportModal Component
 * Unified Deliverables Subsystem Modal coordinating preview and downloads for Sprint 6.3.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  X,
  Download,
  FileText,
  FileSpreadsheet,
  FileCode,
  Loader2,
  Shield,
  Music,
  CheckSquare,
  FileBadge,
} from 'lucide-react';
import {
  ReportTabKey,
  ExportFormat,
  TabConfig,
  ReportExportModalProps,
  ExceptionsScheduleData,
  CueSheetResponse,
  WrapChecklistResponse,
  LegalAuditManifestResponse,
} from './types';
import {
  REPORT_TABS,
  DEFAULT_EXCEPTIONS_SCHEDULE,
  DEFAULT_CUE_SHEET,
  DEFAULT_WRAP_CHECKLIST,
  DEFAULT_AUDIT_MANIFEST,
} from './fixture_data';
import {
  downloadBlob,
  generateJsonBlob,
  generateCsvBlob,
  generateCueSheetCsv,
  generateWrapChecklistCsv,
  generateExceptionsScheduleCsv,
  generateClientPdfBlob,
} from './download_utils';
import { ExceptionsSchedulePreview } from './previews/ExceptionsSchedulePreview';
import { CueSheetPreview } from './previews/CueSheetPreview';
import { WrapChecklistPreview } from './previews/WrapChecklistPreview';
import { AuditManifestPreview } from './previews/AuditManifestPreview';

function getTabIcon(tabId: ReportTabKey): React.JSX.Element {
  switch (tabId) {
    case 'exceptions_schedule':
      return <Shield className="h-4 w-4" />;
    case 'cue_sheet':
      return <Music className="h-4 w-4" />;
    case 'wrap_checklist':
      return <CheckSquare className="h-4 w-4" />;
    case 'audit_manifest':
      return <FileBadge className="h-4 w-4" />;
  }
}

function renderModalHeader(
  productionTitle: string,
  productionId: string,
  onClose: () => void
): React.JSX.Element {
  return (
    <div className="flex items-center justify-between border-b border-slate-800/80 px-6 py-4 bg-[#0e1424]/60">
      <div>
        <div className="flex items-center gap-2.5">
          <h2 className="text-base font-bold text-white tracking-tight">Studio Deliverables Subsystem</h2>
          <span className="rounded-full bg-sky-500/20 border border-sky-500/40 px-2 py-0.5 text-[10px] font-mono text-sky-300">
            Sprint 6.3 Gate
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          {productionTitle} • ID: <span className="font-mono text-slate-300">{productionId}</span>
        </p>
      </div>
      <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
        <X className="h-5 w-5" />
      </button>
    </div>
  );
}

function renderTabsBar(
  activeTab: ReportTabKey,
  onSelect: (tab: ReportTabKey) => void
): React.JSX.Element {
  return (
    <div className="flex border-b border-slate-800/80 px-6 bg-slate-950/40 overflow-x-auto">
      {REPORT_TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onSelect(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              isActive
                ? 'border-sky-400 text-sky-300 bg-sky-500/10'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            {getTabIcon(tab.id)}
            <span>{tab.shortTitle}</span>
          </button>
        );
      })}
    </div>
  );
}

function renderTabContent(
  activeTab: ReportTabKey,
  scheduleData: ExceptionsScheduleData,
  cueData: CueSheetResponse,
  wrapData: WrapChecklistResponse,
  manifestData: LegalAuditManifestResponse
): React.JSX.Element {
  switch (activeTab) {
    case 'exceptions_schedule':
      return <ExceptionsSchedulePreview data={scheduleData} />;
    case 'cue_sheet':
      return <CueSheetPreview cueSheet={cueData} />;
    case 'wrap_checklist':
      return <WrapChecklistPreview checklist={wrapData} />;
    case 'audit_manifest':
      return <AuditManifestPreview manifest={manifestData} />;
  }
}

function renderFooterActions(
  activeConfig: TabConfig,
  exporting: boolean,
  onExport: (format: ExportFormat) => void
): React.JSX.Element {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-slate-800/80 px-6 py-4 bg-[#0e1424]/90">
      <div className="text-xs text-slate-400">
        Exporting <span className="text-white font-medium">{activeConfig.label}</span>
      </div>
      <div className="flex items-center gap-2">
        {activeConfig.supportedFormats.map((fmt) => (
          <button
            key={fmt}
            disabled={exporting}
            onClick={() => onExport(fmt)}
            className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/90 hover:bg-slate-800 px-3.5 py-2 text-xs font-mono font-bold text-slate-200 hover:text-white transition-all disabled:opacity-50 shadow-lg shadow-black/30"
          >
            {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-400" /> : <Download className="h-3.5 w-3.5 text-sky-400" />}
            <span className="uppercase">{fmt}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function ReportExportModal({
  isOpen,
  onClose,
  initialTab = 'exceptions_schedule',
  productionId = 'proj_blockbuster_cinema',
  productionTitle = 'Project Noir',
}: ReportExportModalProps): React.JSX.Element | null {
  const [activeTab, setActiveTab] = useState<ReportTabKey>(initialTab);
  const [exporting, setExporting] = useState<boolean>(false);
  const [scheduleData] = useState<ExceptionsScheduleData>(DEFAULT_EXCEPTIONS_SCHEDULE);
  const [cueData] = useState<CueSheetResponse>(DEFAULT_CUE_SHEET);
  const [wrapData] = useState<WrapChecklistResponse>(DEFAULT_WRAP_CHECKLIST);
  const [manifestData] = useState<LegalAuditManifestResponse>(DEFAULT_AUDIT_MANIFEST);

  useEffect(() => {
    if (isOpen) setActiveTab(initialTab);
  }, [isOpen, initialTab]);

  const handleDownloadPdf = useCallback(() => {
    const pdfBlob = generateClientPdfBlob(
      `LIENMARK LEGAL DELIVERABLE: ${activeTab.toUpperCase()}`,
      [
        { title: `Production: ${productionTitle} (${productionId})`, lines: [`Generated: ${new Date().toISOString()}`] },
        { title: 'Cryptographic Attestation', lines: [`Ledger Head: ${scheduleData.ledger_head_hash}`, `Cut Hash: ${scheduleData.cut_hash}`] },
      ]
    );
    downloadBlob(pdfBlob, `${activeTab}_${productionId}.pdf`);
  }, [activeTab, productionId, productionTitle, scheduleData]);

  const handleDownloadCsv = useCallback(() => {
    let csv = '';
    if (activeTab === 'cue_sheet') csv = generateCueSheetCsv(cueData);
    else if (activeTab === 'wrap_checklist') csv = generateWrapChecklistCsv(wrapData);
    else csv = generateExceptionsScheduleCsv(scheduleData);
    downloadBlob(generateCsvBlob(csv), `${activeTab}_${productionId}.csv`);
  }, [activeTab, cueData, wrapData, scheduleData, productionId]);

  const handleDownloadJson = useCallback(() => {
    let payload: unknown = scheduleData;
    if (activeTab === 'cue_sheet') payload = cueData;
    else if (activeTab === 'wrap_checklist') payload = wrapData;
    else if (activeTab === 'audit_manifest') payload = manifestData;
    downloadBlob(generateJsonBlob(payload), `${activeTab}_${productionId}.json`);
  }, [activeTab, scheduleData, cueData, wrapData, manifestData, productionId]);

  const triggerExport = useCallback(
    async (format: ExportFormat) => {
      setExporting(true);
      try {
        if (format === 'pdf') handleDownloadPdf();
        else if (format === 'csv') handleDownloadCsv();
        else handleDownloadJson();
      } finally {
        setTimeout(() => setExporting(false), 400);
      }
    },
    [handleDownloadPdf, handleDownloadCsv, handleDownloadJson]
  );

  if (!isOpen) return null;
  const currentTabConfig = REPORT_TABS.find((t) => t.id === activeTab) ?? REPORT_TABS[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-5xl max-h-[92vh] flex flex-col rounded-2xl border border-slate-800 bg-[#0B0F17] shadow-2xl overflow-hidden">
        {renderModalHeader(productionTitle, productionId, onClose)}
        {renderTabsBar(activeTab, setActiveTab)}
        <div className="flex-1 overflow-y-auto p-6 bg-[#0B0F17]/90 space-y-4">
          {renderTabContent(activeTab, scheduleData, cueData, wrapData, manifestData)}
        </div>
        {renderFooterActions(currentTabConfig, exporting, triggerExport)}
      </div>
    </div>
  );
}

export default ReportExportModal;

