'use client';

/**
 * DropzoneTarget Component
 * Drag-and-drop file drop target with PDF file selection and removal controls.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useRef } from 'react';
import { UploadCloud, FileText, X } from 'lucide-react';
import type { UploadState } from './useDropzoneUpload';
import { formatFileSize } from './ingestion_utils';

interface DropzoneTargetProps {
  selectedFile: File | null;
  isDragging: boolean;
  uploadState: UploadState;
  selectFile: (file: File | null) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}

export const DropzoneTarget: React.FC<DropzoneTargetProps> = ({
  selectedFile,
  isDragging,
  uploadState,
  selectFile,
  onDragOver,
  onDragLeave,
  onDrop,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (selectedFile) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-900/80 p-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-950/60 border border-sky-500/30 text-sky-400">
            <FileText className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-200">{selectedFile.name}</p>
            <p className="text-[11px] text-slate-400">{formatFileSize(selectedFile.size)}</p>
          </div>
        </div>
        {uploadState === 'idle' && (
          <button
            onClick={() => selectFile(null)}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            aria-label="Remove selected file"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => fileInputRef.current?.click()}
      className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center cursor-pointer transition-colors ${
        isDragging
          ? 'border-sky-400 bg-sky-950/30'
          : 'border-slate-700 bg-slate-900/40 hover:border-slate-600'
      }`}
    >
      <UploadCloud className="h-9 w-9 text-sky-400 mb-2" />
      <p className="text-sm font-medium text-slate-200">
        Drag & drop locked screenplay PDF here
      </p>
      <p className="text-xs text-slate-400 mt-1">
        or click to browse from local workstation
      </p>
      <span className="mt-3 rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
        Max file size: 50 MB • PDF format only
      </span>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0] || null;
          selectFile(file);
        }}
      />
    </div>
  );
};
