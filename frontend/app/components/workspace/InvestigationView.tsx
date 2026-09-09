'use client';
import Link from 'next/link';
import { Activity, ArrowRight, RefreshCw, FileSearch } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { record } from './model';
import { revisionLabel, savedDate, statusLabel } from './labels';
import { PageHeading, PanelTitle, EmptyState, SampleNotice, ReferenceNotice } from './Primitives';
import { ClaimTable } from './ClaimTable';
import { MissionTimeline, SourceInbox, Clarifications } from './AutomationView';

export function AuditResult() {
  const { audit, setAudit, mission } = useWorkspace();
  if (!audit) return <EmptyState title="No audit selected" description="Submit a revision to see its audit reference, returned results, and available telemetry."><Link className="ws-button primary" href="/revisions">Create a revision <ArrowRight size={14} /></Link></EmptyState>;
  const telemetry = record(audit.result?.telemetry);
  const calls = Object.entries(record(mission.calls || audit.progress || telemetry.calls));
  return <><PanelTitle title="Current audit" description={audit.result ? revisionLabel(audit.result) : 'Investigating the submitted revision'}><span className="ws-count-pill">{audit.result ? 'Results available' : statusLabel(audit.status)}</span></PanelTitle>
    <div className="ws-panel-body"><dl className="ws-definition"><dt>Review record</dt><dd>{audit.snapshotId ? 'Saved' : 'Awaiting result'}</dd><dt>Saved at</dt><dd>{audit.result ? savedDate(audit.result.created_at) : 'Awaiting result'}</dd></dl>
      {audit.error && <div className="ws-error ws-section-gap" role="alert">{audit.error}<button className="ws-text-button" onClick={() => setAudit({ ...audit, status: 'accepted', error: undefined })}><RefreshCw size={14} />Check again</button></div>}
      {!audit.result && !audit.error && <p className="ws-progress-label ws-section-gap" role="status"><Activity size={16} />Waiting for the server to return a result snapshot…</p>}
      {calls.length > 0 && <div className="ws-section-gap"><h3>Provider activity</h3><ul className="ws-timeline">{calls.map(([key, value]) => { const call = record(value), trace = record(call.trace); return <li key={key}><div><strong>{String(trace.provider || (key.includes('search') ? 'Parallel Search' : 'Gemini'))} · {statusLabel(call.status)}</strong>{typeof trace.query === 'string' && <p>{trace.query}</p>}<small>{typeof trace.latency_ms === 'number' ? `${(trace.latency_ms / 1000).toFixed(1)} seconds` : String(call.error || 'Awaiting provider response')}</small>{typeof trace.request_id === 'string' && <details className="ws-disclosure"><summary>Request details</summary><p>{trace.request_id}</p>{Boolean(record(trace.orchestration).framework) && <><p>{String(record(trace.orchestration).framework)} · {String(record(trace.orchestration).agent)}</p><pre className="ws-json">{JSON.stringify({ correlation: trace.correlation, orchestration: trace.orchestration }, null, 2)}</pre></>}</details>}</div></li>; })}</ul></div>}
      {Boolean(mission.audit_id && mission.audit_id !== audit.result?.audit_id && mission.status === 'COMPLETED') && <p className="ws-muted">This source check retained the existing production snapshot. Provider activity above belongs to the source check.</p>}
      {audit.result && <><div className="ws-stat-list ws-section-gap">{[
        ['Carried forward', 'carried_forward_count'], ['Reopened', 'reopened_count'], ['Total claims', 'total_claims'],
        ['Budget reserved', 'reserved_spend'], ['Billed cost', 'reconciled_spend'],
      ].map(([label, key]) => <div key={key}><span>{label}</span><strong>{key === 'reserved_spend' && typeof mission.reserved_usd === 'number' ? `$${mission.reserved_usd.toFixed(2)}` : typeof telemetry[key] === 'number' && key.endsWith('_spend') ? `$${Number(telemetry[key]).toFixed(2)}` : typeof telemetry[key] === 'string' || typeof telemetry[key] === 'number' ? String(telemetry[key]) : 'Not reported'}</strong></div>)}</div>
        <p className="ws-muted" style={{ fontSize: 11, marginTop: 18 }}>A budget reservation does not establish that a provider call ran. Returned telemetry is shown as reported by the service.</p>
        <details className="ws-disclosure ws-section-gap"><summary>Inspect returned audit record</summary><pre className="ws-json">{JSON.stringify(audit.result, null, 2)}</pre></details></>}
    </div></>;
}
export default function InvestigationView() {
  const { claims, sample, setAccessOpen } = useWorkspace();
  const affected = claims.filter(claim => ['reopened', 'new', 'exception'].includes(claim.status));
  return <><PageHeading eyebrow="INVESTIGATIONS" title="Focus the work where it matters." description="Inspect affected claims, follow the audit, and review the evidence it returns."><Link className="ws-button primary" href="/revisions"><FileSearch size={15} />New revision audit</Link></PageHeading>
    {sample ? <SampleNotice onRequest={() => setAccessOpen(true)} /> : <ReferenceNotice />}
    <MissionTimeline /><Clarifications /><SourceInbox />
    <div className="ws-form-layout"><ClaimTable claims={affected} title="Claims requiring attention" description="Reopened claims and exceptions from the displayed records." /><section className="ws-panel"><AuditResult /></section></div></>;
}
