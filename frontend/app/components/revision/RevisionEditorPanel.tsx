"use client";
import React, { useState } from 'react';

export default function RevisionEditorPanel() {
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
        setStatus('Pending');
        pollStatus(id);
      } else {
        setStatus('Error submitting');
      }
    } catch (err) {
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
      <h2 className="text-xl mb-4 font-bold">Revision Editor Panel</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
        <label>Stable Lineage Key: <input name="stable_lineage_key" value={formData.stable_lineage_key} onChange={handleChange} className="border p-1 w-full" /></label>
        <label>Title/Artist: <input name="titleArtist" value={formData.titleArtist} onChange={handleChange} className="border p-1 w-full" /></label>
        <label>Duration: <input name="duration" value={formData.duration} onChange={handleChange} className="border p-1 w-full" /></label>
        <label>Prominence: <input name="prominence" value={formData.prominence} onChange={handleChange} className="border p-1 w-full" /></label>
        <label>Intended Use: <input name="intendedUse" value={formData.intendedUse} onChange={handleChange} className="border p-1 w-full" /></label>
        <label>Distribution Media: <input name="distributionMedia" value={formData.distributionMedia} onChange={handleChange} className="border p-1 w-full" /></label>
        <label>Territory: <input name="territory" value={formData.territory} onChange={handleChange} className="border p-1 w-full" /></label>
        <label>Term Dates: <input name="termDates" value={formData.termDates} onChange={handleChange} className="border p-1 w-full" /></label>
        <label className="col-span-2">Agreement Attachments: <input name="attachments" value={formData.attachments} onChange={handleChange} className="border p-1 w-full" /></label>
        <label className="flex items-center col-span-2">
          <input type="checkbox" name="shiftSimulator" checked={formData.shiftSimulator} onChange={handleChange} className="mr-2" />
          Enable external-evidence shift simulator (challenges prior evidence without changing cut)
        </label>
        <button type="submit" className="bg-blue-600 text-white p-2 col-span-2 rounded">Submit Revision</button>
      </form>
      {status && <div className="mt-4 font-semibold text-blue-600">Status: {status} {auditId && `(Audit ID: ${auditId})`}</div>}
    </div>
  );
}
