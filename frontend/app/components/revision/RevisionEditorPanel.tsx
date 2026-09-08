"use client";
import React, { useState } from 'react';

export interface RevisionEditorPanelProps {
  disabled?: boolean;
  disabledReason?: string;
  onAuditCreated?: (auditId: string) => void;
}

export default function RevisionEditorPanel({
  disabled = false,
  disabledReason = 'An invited session is required to submit revisions.',
  onAuditCreated,
}: RevisionEditorPanelProps = {}) {
  const [formData, setFormData] = useState({
    stable_lineage_key: '',
    titleArtist: '',
    duration: '',
    prominence: '',
    intendedUse: '',
    distributionMedia: '',
    territory: '',
    termDates: '',
    attachments: '',
    shiftSimulator: false,
  });
  const [auditId, setAuditId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({ ...prev, [name]: checked }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (disabled) return;
    setStatus('Submitting...');
    try {
      const res = await fetch('/api/revisions/audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      if (res.ok) {
        const data = await res.json();
        const id = typeof data.audit_id === 'string' ? data.audit_id : '';
        setAuditId(id);
        onAuditCreated?.(id);
        setStatus('Pending');
        pollStatus(id);
      } else {
        setStatus('Error submitting');
      }
    } catch {
      setStatus('Error submitting');
    }
  };

  const pollStatus = (id: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/revisions/audit/${id}`);
        if (res.ok) {
          const data = await res.json();
          const currentStatus = typeof data.status === 'string' ? data.status : 'unknown';
          setStatus(currentStatus);
          if (currentStatus === 'Completed' || currentStatus === 'Failed') {
            clearInterval(interval);
          }
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  };

  return (
    <div className="border p-4 rounded mt-4 text-black bg-white">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">Revision Editor Panel</h2>
        {disabled && (
          <span className="text-xs bg-amber-100 text-amber-900 border border-amber-300 px-2.5 py-1 rounded-full font-semibold">
            Locked (Read-Only)
          </span>
        )}
      </div>

      {disabled && (
        <div className="mb-4 rounded bg-amber-50 border border-amber-300 p-3 text-xs text-amber-900 font-medium flex items-center gap-2">
          <span className="text-base">🔒</span>
          <span>{disabledReason}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
        <label className="text-xs font-semibold">Stable Lineage Key: <input name="stable_lineage_key" disabled={disabled} value={formData.stable_lineage_key} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="text-xs font-semibold">Title/Artist: <input name="titleArtist" disabled={disabled} value={formData.titleArtist} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="text-xs font-semibold">Duration: <input name="duration" disabled={disabled} value={formData.duration} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="text-xs font-semibold">Prominence: <input name="prominence" disabled={disabled} value={formData.prominence} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="text-xs font-semibold">Intended Use: <input name="intendedUse" disabled={disabled} value={formData.intendedUse} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="text-xs font-semibold">Distribution Media: <input name="distributionMedia" disabled={disabled} value={formData.distributionMedia} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="text-xs font-semibold">Territory: <input name="territory" disabled={disabled} value={formData.territory} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="text-xs font-semibold">Term Dates: <input name="termDates" disabled={disabled} value={formData.termDates} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="col-span-2 text-xs font-semibold">Agreement Attachments: <input name="attachments" disabled={disabled} value={formData.attachments} onChange={handleChange} className="border p-1 w-full rounded disabled:bg-gray-100 disabled:cursor-not-allowed" /></label>
        <label className="flex items-center col-span-2 text-xs">
          <input type="checkbox" name="shiftSimulator" disabled={disabled} checked={formData.shiftSimulator} onChange={handleChange} className="mr-2 disabled:cursor-not-allowed" />
          Enable external-evidence shift simulator (challenges prior evidence without changing cut)
        </label>
        <button
          type="submit"
          disabled={disabled}
          title={disabled ? disabledReason : undefined}
          className={`p-2 col-span-2 rounded font-semibold text-sm transition-colors ${
            disabled
              ? 'bg-slate-300 text-slate-500 cursor-not-allowed border border-slate-400'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {disabled ? '🔒 Submit Revision (Invited Session Required)' : 'Submit Revision'}
        </button>
      </form>
      {status && <div className="mt-4 font-semibold text-blue-600">Status: {status} {auditId && `(Audit ID: ${auditId})`}</div>}
    </div>
  );
}
