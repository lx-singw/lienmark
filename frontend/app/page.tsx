"use client";
import React, { useEffect, useState } from 'react';
import SessionBadge from './components/auth/SessionBadge';
import RevisionEditorPanel from './components/revision/RevisionEditorPanel';
import AuditTelemetryPanel from './components/telemetry/AuditTelemetryPanel';
import ExportActionComponent from './components/ExportActionComponent';

export default function HomePage() {
  const [role, setRole] = useState<string>('');
  const [auditId] = useState<string | null>("mock-audit-123");
  const [snapshotId, setSnapshotId] = useState<string | null>(null);
  const [evidenceComplete, setEvidenceComplete] = useState<boolean>(false);
  const [counselDirective, setCounselDirective] = useState<string>('');

  useEffect(() => {
    fetch('/api/auth/session')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.user) {
          const userRole = typeof data.user.role === 'string' ? data.user.role : '';
          setRole(userRole);
        }
      })
      .catch(() => {});
  }, []);

  const handleDecision = async (claimId: string, decision: 'approve' | 'reject') => {
    try {
      const res = await fetch(`/api/v1/claims/${claimId}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, counselDirective: decision === 'reject' ? counselDirective : undefined })
      });
      if (res.ok) {
        const data = await res.json();
        const newSnapshotId = typeof data.result_snapshot_id === 'string' ? data.result_snapshot_id : '';
        setSnapshotId(newSnapshotId);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <main className="p-8 max-w-5xl mx-auto flex flex-col gap-6 text-black bg-gray-100 min-h-screen">
      <header className="flex justify-between items-center mb-4">
        <h1 className="text-3xl font-bold">Lienmark Command Center</h1>
        <SessionBadge />
      </header>

      <RevisionEditorPanel />
      <AuditTelemetryPanel auditId={auditId} />
      <ExportActionComponent auditId={auditId} resultSnapshotId={snapshotId} />

      <section className="border p-4 rounded bg-white">
        <h2 className="text-xl mb-4 font-bold">Adjudication (Gavel)</h2>
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-4 border p-4 bg-gray-50 rounded">
            <span className="font-semibold text-lg">Claim #8892</span>
            
            {role === 'Producer' && (
              <span className="text-sm text-red-600 ml-4 font-semibold">Gavel buttons disabled: Producers cannot adjudicate claims.</span>
            )}
            
            {role === 'Reviewer' && (
              <div className="flex items-center gap-4 ml-4">
                <label className="text-sm flex items-center gap-1 font-semibold">
                  <input type="checkbox" checked={evidenceComplete} onChange={e => setEvidenceComplete(e.target.checked)} className="w-4 h-4" />
                  Evidence Complete
                </label>
                <input 
                  type="text" 
                  placeholder="Counsel Directive (required for rejection)" 
                  value={counselDirective}
                  onChange={e => setCounselDirective(e.target.value)}
                  className="border p-2 text-sm w-64 rounded"
                />
              </div>
            )}

            <div className="ml-auto flex gap-2">
              <button 
                onClick={() => handleDecision('8892', 'approve')}
                disabled={role === 'Producer' || (role === 'Reviewer' && !evidenceComplete)}
                className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50 font-bold"
              >
                Approve
              </button>
              <button 
                onClick={() => handleDecision('8892', 'reject')}
                disabled={role === 'Producer'}
                className="bg-red-600 text-white px-4 py-2 rounded disabled:opacity-50 font-bold"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
