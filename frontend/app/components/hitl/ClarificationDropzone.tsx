'use client';

/**
 * Lienmark HITL Clarification Document Dropzone
 * Drag-and-drop file uploader for supporting agreements and licenses (.pdf, .docx).
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, X, AlertCircle } from 'lucide-react';
import { AttachedDocument } from './hitl_types';
import { validateAttachedDocument, formatFileSize } from './hitl_utils';

export interface ClarificationDropzoneProps {
  readonly attachments: ReadonlyArray<AttachedDocument>;
  readonly onAddAttachment: (doc: AttachedDocument) => void;
  readonly onRemoveAttachment: (id: string) => void;
  readonly disabled?: boolean;
  readonly className?: string;
}

export const ClarificationDropzone: React.FC<ClarificationDropzoneProps> = ({
  attachments,
  onAddAttachment,
  onRemoveAttachment,
  disabled = false,
  className = '',
}) => {
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setUploadError(null);

    Array.from(fileList).forEach((file) => {
      const validation = validateAttachedDocument(file);
      if (!validation.isValid) {
        setUploadError(validation.error);
        return;
      }

      const newDoc: AttachedDocument = {
        id: `att_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        name: file.name,
        sizeBytes: file.size,
        mimeType: file.type || 'application/octet-stream',
        uploadedAt: new Date().toISOString(),
      };
      onAddAttachment(newDoc);
    });
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    processFiles(e.dataTransfer.files);
  };

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
        <span className="flex items-center gap-1.5">
          <UploadCloud className="h-3.5 w-3.5 text-sky-400" aria-hidden="true" />
          <span>Supporting Agreements &amp; Licenses (.pdf, .docx):</span>
        </span>
        <span>Max 15MB per file</span>
      </div>

      {/* Interactive Dropzone Box */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragOver(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragOver(false);
        }}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`group relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-4 text-center transition-all ${
          isDragOver
            ? 'border-sky-400 bg-sky-500/10 scale-[0.99]'
            : 'border-slate-700/80 bg-slate-900/40 hover:border-slate-500 hover:bg-slate-900/70'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          multiple
          disabled={disabled}
          onChange={(e) => {
            processFiles(e.target.files);
            e.target.value = '';
          }}
          className="hidden"
          aria-label="Upload supporting agreement or license documents"
        />

        <div className="flex flex-col items-center gap-1">
          <UploadCloud
            className={`h-6 w-6 transition-transform group-hover:-translate-y-0.5 ${
              isDragOver ? 'text-sky-400' : 'text-slate-400'
            }`}
            aria-hidden="true"
          />
          <p className="text-xs text-slate-300">
            <span className="font-semibold text-sky-400 underline decoration-sky-400/40">
              Browse files
            </span>{' '}
            or drag and drop supporting executed agreements
          </p>
          <p className="text-[10px] font-mono text-slate-500">
            Chain of Title, Sync Licenses, Releases (.pdf, .docx up to 15MB)
          </p>
        </div>
      </div>

      {/* Validation Error Banner */}
      {uploadError && (
        <div className="flex items-center gap-1.5 rounded-lg border border-rose-500/40 bg-rose-950/40 px-3 py-1.5 text-xs text-rose-300 animate-in fade-in">
          <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 text-rose-400" aria-hidden="true" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Attached Files List */}
      {attachments.length > 0 && (
        <div className="space-y-1.5 pt-1">
          <div className="text-[10px] font-mono uppercase text-slate-400 font-semibold">
            Attached Documents ({attachments.length}):
          </div>
          <div className="flex flex-wrap gap-2">
            {attachments.map((doc) => (
              <div
                key={doc.id}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/90 px-2.5 py-1 text-xs text-slate-200 shadow-sm"
              >
                <FileText className="h-3.5 w-3.5 text-sky-400 flex-shrink-0" aria-hidden="true" />
                <span className="max-w-[180px] truncate font-mono text-[11px]" title={doc.name}>
                  {doc.name}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  ({formatFileSize(doc.sizeBytes)})
                </span>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveAttachment(doc.id);
                  }}
                  className="rounded p-0.5 text-slate-400 hover:bg-slate-800 hover:text-rose-300 focus:outline-none focus:ring-1 focus:ring-rose-400"
                  aria-label={`Remove attached document ${doc.name}`}
                >
                  <X className="h-3 w-3" aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ClarificationDropzone;
