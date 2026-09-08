'use client';
import Link from 'next/link';
import { ArrowRight, Plus, RefreshCw, ShieldCheck, GitCompareArrows, Files, CircleAlert, FileCheck2 } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { countClaims } from './model';
import { PageHeading, PanelTitle, SampleNotice, ReferenceNotice } from './Primitives';
import { ClaimTable } from './ClaimTable';

export function SummaryCards() {
  const { claims, sample } = useWorkspace();
  const counts = countClaims(claims);
  return <div className="ws-summary">{[
    { label: 'Rights-bearing assets', value: counts.total, note: 'In the displayed clearance records', icon: Files, color: '' },
    { label: 'Approvals preserved', value: counts.preserved, note: 'Prior decisions carried forward', icon: ShieldCheck, color: 'green' },
    { label: 'Claims to revalidate', value: counts.reopened, note: 'Changed dependencies need review', icon: GitCompareArrows, color: 'amber' },
    { label: 'Open exceptions', value: counts.exceptions, note: 'Require resolution or disclosure', icon: CircleAlert, color: 'red' },
  ].map(({ label, value, note, icon: Icon, color }) => <section className="ws-metric" key={label}><div className="ws-metric-top"><span>{label}</span><span className={`ws-metric-icon ${color}`}><Icon size={17} /></span></div><div className="ws-metric-number">{value}</div><small>{sample ? 'Illustrative · ' : ''}{note}</small></section>)}</div>;
}
function NextSteps() {
  return <div className="ws-stack"><section className="ws-panel"><PanelTitle title="From change to delivery" description="Keep the review focused." /><div className="ws-panel-body">{[
    ['Compare the revision', 'Identify changed uses and the dependencies they affect.'],
    ['Resolve the exceptions', 'Investigate affected claims and record an authorized decision.'],
    ['Prepare the handoff', 'Keep the draft schedule aligned with the reviewed version.'],
  ].map(([title, description], index) => <div className="ws-workflow-step" key={title}><span className="ws-step-number">{index + 1}</span><div><h3>{title}</h3><p>{description}</p></div></div>)}</div></section>
    <section className="ws-delivery-card"><FileCheck2 size={25} /><h2>A clear path<br />to your next delivery.</h2><p>See what remains unresolved before preparing the Exceptions Schedule.</p><Link href="/delivery">Open delivery workspace <ArrowRight size={14} /></Link></section></div>;
}
export default function Overview() {
  const { claims, sample, error, loading, checking, refresh, setAccessOpen, audit } = useWorkspace();
  return <><PageHeading eyebrow="PRODUCTION OVERVIEW" title="Every revision. A clear next step." description="See what changed, which approvals carry forward, and what needs attention.">
    <button className="ws-button" disabled={sample || loading} onClick={() => void refresh()}><RefreshCw size={14} />{loading ? 'Refreshing…' : 'Refresh'}</button><Link className="ws-button primary" href="/revisions"><Plus size={15} />New revision</Link></PageHeading>
    {sample ? <SampleNotice onRequest={() => setAccessOpen(true)} /> : <ReferenceNotice />}{error && <div className="ws-error" role="alert">{error}</div>}
    <div className="ws-revision-strip"><div className="ws-revision-pair"><label>REFERENCE COMPARISON</label><span className="ws-revision-pill">Cut v7 · Baseline</span><ArrowRight size={14} /><span className="ws-revision-pill target">Cut v8 · Revision</span></div><span className="ws-revision-caption">Approval continuity, asset by asset</span></div>
    {checking ? <div className="ws-loading" role="status">Checking workspace access…</div> : <><SummaryCards /><div className="ws-overview-grid"><ClaimTable claims={claims} /><NextSteps /></div></>}
  </>;
}
