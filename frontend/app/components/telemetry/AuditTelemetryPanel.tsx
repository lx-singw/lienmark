"use client";
import React, { useEffect, useState } from 'react';

interface TelemetryData {
  approvalsPreserved: number;
  claimsReopened: number;
  blockersRemaining: number;
  evidenceDrawer: {
    provider: string;
    query: string;
    latencyMs: number;
    pages: { url: string; title: string }[];
  }[];
  spend: { estimated: number; reserved: number; reconciled: number };
}

export default function AuditTelemetryPanel({ auditId }: { auditId: string | null }) {
  const [data, setData] = useState<TelemetryData | null>(null);

  useEffect(() => {
    if (!auditId) return;
    const fetchTelemetry = async () => {
      try {
        const res = await fetch(`/api/telemetry/${auditId}`);
        if (res.ok) setData(await res.json());
      } catch (e) {
        // ignore
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 3000);
    return () => clearInterval(interval);
  }, [auditId]);

  if (!auditId) return <div className="p-4 border mt-4 text-gray-500 bg-white">No active audit ID.</div>;
  if (!data) return <div className="p-4 border mt-4 text-black bg-white">Loading telemetry for {auditId}...</div>;

  return (
    <div className="border p-4 rounded mt-4 bg-gray-50 text-black">
      <h2 className="text-xl mb-4 font-bold">Audit Telemetry (ID: {auditId})</h2>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="p-2 bg-white rounded shadow-sm border">
          <div className="text-sm text-gray-500">Approvals Preserved</div>
          <div className="font-bold">${data.approvalsPreserved.toFixed(2)}</div>
        </div>
        <div className="p-2 bg-white rounded shadow-sm border">
          <div className="text-sm text-gray-500">Claims Reopened</div>
          <div className="font-bold">{data.claimsReopened}</div>
        </div>
        <div className="p-2 bg-white rounded shadow-sm border">
          <div className="text-sm text-gray-500">Blockers Remaining</div>
          <div className="font-bold">{data.blockersRemaining}</div>
        </div>
      </div>
      
      <div className="mb-4">
        <h3 className="font-semibold mb-2">Spend Analytics</h3>
        <div className="flex gap-4 text-sm bg-white p-2 rounded border">
          <span>Estimated: ${data.spend.estimated.toFixed(2)}</span>
          <span>Reserved: ${data.spend.reserved.toFixed(2)}</span>
          <span>Reconciled: ${data.spend.reconciled.toFixed(2)}</span>
        </div>
      </div>

      <div>
        <h3 className="font-semibold mb-2">Attributable Evidence Drawer</h3>
        {data.evidenceDrawer.map((ev, i) => (
          <div key={i} className="mb-2 p-2 border bg-white text-sm rounded">
            <div className="flex justify-between font-semibold">
              <span>{ev.provider}</span>
              <span>{ev.latencyMs}ms</span>
            </div>
            <div className="text-gray-600 mb-1">Query: {ev.query}</div>
            <ul className="list-disc pl-5">
              {ev.pages.map((p, j) => (
                <li key={j}><a href={p.url} className="text-blue-600 hover:underline">{p.title}</a></li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
