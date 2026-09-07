'use client';

/**
 * DropzoneModal Component
 * Modal for Line Producer / Post Supervisor to upload locked script drafts with live GCS path preview.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { X, AlertCircle, Loader2 } from 'lucide-react';
import type { DropzoneModalProps } from './types';
import { useDropzoneUpload } from './useDropzoneUpload';
import { buildGcsUri, validateGcsTargetPath } from './ingestion_utils';
import { DropzoneTarget } from './DropzoneTarget';
import { GcsPathPreview } from './GcsPathPreview';
import { UploadProgressCard } from './UploadProgressCard';

export const DropzoneModal: React.FC<DropzoneModalProps> = ({
  isOpen,
  onClose,
  onUploadComplete,
  defaultOrgId = 'studio-alpha',
  defaultProdId = 'prod-001',
  bucketName = 'lienmark-intake-storage',
}) => {
  const {
    orgId,
    setOrgId,
    prodId,
    setProdId,
    bucket,
    selectedFile,
    isDragging,
    validationError,
    uploadState,
    progress,
    statusMessage,
    runId,
    selectFile,
    onDragOver,
    onDragLeave,
    onDrop,
    triggerUpload,
    reset,
  } = useDropzoneUpload({
    defaultOrgId,
    defaultProdId,
    bucketName,
    onUploadComplete,
  });

  if (!isOpen) return null;

  const currentFilename = selectedFile ? selectedFile.name : '{filename}.pdf';
  const liveGcsUri = buildGcsUri(bucket, orgId, prodId, currentFilename);
  const pathCheck = selectedFile ? validateGcsTargetPath(liveGcsUri) : { isValid: false };

  const handleClose = () => {
    if (uploadState === 'uploading') return;
    reset();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dropzone-modal-title"
    >
      <div className="relative w-full max-w-2xl rounded-xl border border-slate-700/70 bg-[#090e1a] p-6 shadow-2xl text-slate-100">
        <div className="flex items-start justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 id="dropzone-modal-title" className="text-lg font-semibold text-slate-100">
              Locked Script Intake
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Upload locked milestone screenplay to trigger autonomous Google Cloud Eventarc ingestion.
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={uploadState === 'uploading'}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 disabled:opacity-40"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Organization Identifier
            </label>
            <input
              type="text"
              value={orgId}
              onChange={(e) => setOrgId(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ''))}
              disabled={uploadState === 'uploading' || uploadState === 'success'}
              className="w-full rounded-md border border-slate-700 bg-slate-900/90 px-3 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
              placeholder="e.g. studio-alpha"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Production Identifier
            </label>
            <input
              type="text"
              value={prodId}
              onChange={(e) => setProdId(e.target.value.replace(/[^a-zA-Z0-9_-]/g, ''))}
              disabled={uploadState === 'uploading' || uploadState === 'success'}
              className="w-full rounded-md border border-slate-700 bg-slate-900/90 px-3 py-1.5 text-xs text-slate-200 focus:border-sky-500 focus:outline-none"
              placeholder="e.g. prod-001"
            />
          </div>
        </div>

        <div className="mt-4">
          <DropzoneTarget
            selectedFile={selectedFile}
            isDragging={isDragging}
            uploadState={uploadState}
            selectFile={selectFile}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
          />
        </div>

        {validationError && (
          <div className="mt-3 flex items-center gap-2 rounded-md border border-rose-500/40 bg-rose-950/30 px-3 py-2 text-xs text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{validationError}</span>
          </div>
        )}

        <GcsPathPreview uri={liveGcsUri} validation={pathCheck} />

        <UploadProgressCard
          uploadState={uploadState}
          progress={progress}
          statusMessage={statusMessage}
          runId={runId}
        />

        <div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
          <button
            onClick={handleClose}
            className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700"
          >
            {uploadState === 'success' ? 'Dismiss' : 'Cancel'}
          </button>
          {uploadState !== 'success' && (
            <button
              onClick={triggerUpload}
              disabled={!selectedFile || uploadState === 'uploading' || !pathCheck.isValid}
              className="rounded-md bg-sky-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
            >
              {uploadState === 'uploading' && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              <span>Upload & Trigger Ingestion</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default DropzoneModal;
