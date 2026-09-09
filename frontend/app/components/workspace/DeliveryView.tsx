'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Download, Printer, ArrowRight, FileCheck2, CircleAlert, ShieldCheck } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { countClaims, record } from './model';
import { productionName, revisionLabel, statusLabel } from './labels';
import { PageHeading, PanelTitle, EmptyState } from './Primitives';
import { WorkspaceNotice } from './RecordViews';
import { ClaimTable } from './ClaimTable';

import { RevisionOutcome } from './AutomationView';
export default function DeliveryView() {
  const { claims, sample, snapshot, user } = useWorkspace();
  const audit = snapshot ? { result: snapshot, revisionId: String(snapshot.revision_id), snapshotId: String(snapshot.snapshot_id),
    statusUrl: `/api/clearance/productions/${encodeURIComponent(user?.production_id || '')}/revisions/${encodeURIComponent(String(snapshot.revision_id))}/snapshots/${encodeURIComponent(String(snapshot.snapshot_id))}` } : null;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const counts = countClaims(claims);
  const snapshotDecisions = Array.isArray(audit?.result?.decisions) ? audit.result.decisions.map(record) : [];
  async function download(format: 'pdf' | 'execution-record' = 'pdf') {
    if (sample || !audit?.result || !audit.snapshotId || busy) return;
    setBusy(true); setError('');
    try {
      const response = await fetch(`${audit.statusUrl}/${format}`, { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok || !response.headers.get('content-type')?.includes(format === 'pdf' ? 'application/pdf' : 'application/json')) throw new Error('The server did not return the requested export. Please retry after checking the audit.');
      const blob = await response.blob();
      if (format === 'pdf' && await blob.slice(0, 5).text() !== '%PDF-') throw new Error('The export was not a valid PDF response.');
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${productionName(user).replace(/[^a-z0-9]+/gi, '-').toLowerCase()}-${format === 'pdf' ? 'exceptions-schedule.pdf' : 'execution-record.json'}`; anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err instanceof Error ? err.message : 'Export failed.'); }
    finally { setBusy(false); }
  }
  return <><PageHeading eyebrow="DELIVERY" title="A clear record for the handoff." description="Review unresolved matters and prepare a draft schedule tied to a returned audit snapshot.">
    <button className="ws-button" disabled={sample || !audit?.result} onClick={() => window.print()}><Printer size={14} />Print view</button><button className="ws-button primary" disabled={sample || !audit?.snapshotId || busy} onClick={() => void download()}><Download size={15} />{busy ? 'Preparing PDF…' : 'Download draft PDF'}</button></PageHeading><WorkspaceNotice />
    {error && <div className="ws-error" role="alert">{error}</div>}
    <RevisionOutcome />
    {!sample && audit?.snapshotId && <section className="ws-panel ws-section-gap"><PanelTitle title="Execution record" description="Inspect the source trigger, recorded ADK events, provider receipts, recovery history and reviewer actions for this snapshot." /><div className="ws-panel-body"><button className="ws-button" disabled={busy} onClick={() => void download('execution-record')}><Download size={14} />Download execution record</button><p className="ws-muted ws-section-gap">Includes production evidence. Review its contents before sharing outside the assigned production.</p></div></section>}
    <div className="ws-form-layout"><div className="ws-stack"><section className="ws-panel"><PanelTitle title="Draft Exceptions Schedule" description={sample ? 'Illustrative preview · No legal sign-off' : audit?.snapshotId ? revisionLabel(snapshot) : 'Awaiting a saved review record'}><span className="ws-count-pill">DRAFT</span></PanelTitle>
      {!sample && audit?.result ? <div className="ws-panel-body"><p className="ws-muted" style={{ fontSize: 12 }}>These decisions come from the latest saved review record. Confirm their revision scope and supporting evidence before delivery.</p>{snapshotDecisions.length ? <div className="ws-table-scroll ws-section-gap"><table className="ws-table"><thead><tr><th>ASSET</th><th>REVIEW STATUS</th><th>RATIONALE</th></tr></thead><tbody>{snapshotDecisions.map((decision, index) => <tr key={String(decision.decision_id || index)}><td style={{ whiteSpace: 'normal' }}>{claims.find(claim => claim.id === decision.stable_lineage_key)?.title || 'Recorded asset'}</td><td>{statusLabel(decision.status)}</td><td style={{ whiteSpace: 'normal' }}>{String(decision.counsel_rationale || 'Not supplied')}</td></tr>)}</tbody></table></div> : <EmptyState title="No decision entries returned" description="An empty record does not establish clearance. Confirm the audit before exporting." />}</div>
        : <EmptyState title={sample ? 'See what the delivery handoff contains' : 'No audit snapshot selected'} description={sample ? 'The sample below illustrates unresolved matters. An authenticated audit provides the snapshot for a downloadable draft.' : 'Submit a revision audit and inspect its results before exporting the draft schedule.'}><Link className="ws-button" href="/revisions">Open revisions <ArrowRight size={14} /></Link></EmptyState>}</section>
      <ClaimTable claims={claims.filter(claim => ['reopened', 'exception', 'new'].includes(claim.status))} title="Unresolved matters in current records" description="Review needed and open exceptions are distinct from a final delivery determination." /></div>
      <aside className="ws-stack"><section className="ws-panel"><PanelTitle title="Delivery review checklist" /><div className="ws-panel-body ws-check-list"><div><ShieldCheck size={16} /><span>{counts.preserved + counts.reviewed} preserved or re-attested {sample ? 'sample ' : ''}records</span></div><div><CircleAlert size={16} /><span>{counts.reopened} claims require revalidation; {counts.exceptions} open exceptions</span></div><div><FileCheck2 size={16} /><span>Confirm the applicable revision, reviewer decisions, and supporting evidence.</span></div></div></section>
        <div className="ws-soft-box"><h3>A draft for authorized review.</h3><p>Preparing or downloading a schedule does not grant clearance or indicate that an underwriter has accepted the production.</p></div></aside></div></>;
}
