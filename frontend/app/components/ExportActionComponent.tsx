"use client";
import React from 'react';

interface Props {
  auditId: string | null;
  resultSnapshotId: string | null;
}

export default function ExportActionComponent({ auditId, resultSnapshotId }: Props) {
  const handleExport = () => {
    if (!auditId || !resultSnapshotId) return;
    window.open(`/api/export?audit_id=${auditId}&result_snapshot_id=${resultSnapshotId}`, '_blank');
  };

  return (
    <div className="border p-4 rounded mt-4 flex items-center justify-between bg-white text-black">
      <div>
        <h3 className="font-semibold text-lg">Export Draft Exceptions Schedule</h3>
        <p className="text-sm text-gray-600">
          Bound to Audit: {auditId || 'None'} | Snapshot: {resultSnapshotId || 'None'}
        </p>
      </div>
      <button 
        onClick={handleExport}
        disabled={!auditId || !resultSnapshotId}
        className="bg-green-600 text-white px-4 py-2 rounded disabled:opacity-50 font-semibold"
      >
        Export Draft Exceptions Schedule (PDF)
      </button>
    </div>
  );
}
