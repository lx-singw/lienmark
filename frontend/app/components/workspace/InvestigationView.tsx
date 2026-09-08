'use client';
import Link from 'next/link';
import { Activity, ArrowRight, RefreshCw, FileSearch } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { record } from './model';
import { PageHeading, PanelTitle, EmptyState, SampleNotice, ReferenceNotice } from './Primitives';
import { ClaimTable } from './ClaimTable';

export function AuditResult() {
  const { audit, setAudit } = useWorkspace();
  if (!audit) return <EmptyState title="No audit selected" description="Submit a revision to see its audit reference, returned results, and available telemetry."><Link className="ws-button primary" href="/revisions">Create a revision <ArrowRight size={14} /></Link></EmptyState>;
  const telemetry = record(audit.result?.telemetry);
  return <><PanelTitle title="Current audit" description={audit.id}><span className="ws-count-pill">{audit.result ? 'Results returned' : audit.status.replace(/_/g, ' ')}</span></PanelTitle>
    <div className="ws-panel-body"><dl className="ws-definition"><dt>Revision</dt><dd>{audit.revisionId}</dd><dt>Snapshot</dt><dd>{audit.snapshotId || 'Awaiting result'}</dd></dl>
      {audit.error && <div className="ws-error ws-section-gap" role="alert">{audit.error}<button className="ws-text-button" onClick={() => setAudit({ ...audit, status: 'accepted', error: undefined })}><RefreshCw size={14} />Check again</button></div>}
      {!audit.result && !audit.error && <p className="ws-progress-label ws-section-gap" role="status"><Activity size={16} />Waiting for the server to return a result snapshot…</p>}
      {audit.result && <><div className="ws-stat-list ws-section-gap">{[
        ['Carried forward', 'carried_forward_count'], ['Reopened', 'reopened_count'], ['Total claims', 'total_claims'],
        ['Reserved budget', 'reserved_spend'], ['Reconciled spend', 'reconciled_spend'],
      ].map(([label, key]) => <div key={key}><span>{label}</span><strong>{typeof telemetry[key] === 'string' || typeof telemetry[key] === 'number' ? String(telemetry[key]) : 'Not reported'}</strong></div>)}</div>
        <p className="ws-muted" style={{ fontSize: 11, marginTop: 18 }}>A budget reservation does not establish that a provider call ran. Returned telemetry is shown as reported by the service.</p>
        <details className="ws-disclosure ws-section-gap"><summary>Inspect returned audit record</summary><pre className="ws-json">{JSON.stringify(audit.result, null, 2)}</pre></details></>}
    </div></>;
}
export default function InvestigationView() {
  const { claims, sample, setAccessOpen } = useWorkspace();
  const affected = claims.filter(claim => ['reopened', 'new', 'exception'].includes(claim.status));
  return <><PageHeading eyebrow="INVESTIGATIONS" title="Focus the work where it matters." description="Inspect affected claims, follow the audit, and review the evidence it returns."><Link className="ws-button primary" href="/revisions"><FileSearch size={15} />New revision audit</Link></PageHeading>
    {sample ? <SampleNotice onRequest={() => setAccessOpen(true)} /> : <ReferenceNotice />}
    <div className="ws-form-layout"><ClaimTable claims={affected} title="Claims requiring attention" description="Reopened claims and exceptions from the displayed records." /><section className="ws-panel"><AuditResult /></section></div></>;
}
