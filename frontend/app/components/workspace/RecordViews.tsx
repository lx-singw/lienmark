'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ExternalLink, FileText, ArrowRight, ShieldCheck, CheckCircle2, Search } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { safeUrl } from './model';
import { PageHeading, PanelTitle, EmptyState, SampleNotice, ReferenceNotice } from './Primitives';
import { ClaimTable } from './ClaimTable';

export function WorkspaceNotice() {
  const { sample, error, setAccessOpen } = useWorkspace();
  return <>{sample ? <SampleNotice onRequest={() => setAccessOpen(true)} /> : <ReferenceNotice />}{!sample && error && <div className="ws-error" role="alert">{error}</div>}</>;
}
export function EvidenceView() {
  const { claims } = useWorkspace();
  const [query, setQuery] = useState('');
  const evidence = claims.filter(claim => claim.evidence).filter(claim => `${claim.title} ${claim.evidence?.title}`.toLowerCase().includes(query.toLowerCase()));
  return <><PageHeading eyebrow="EVIDENCE LIBRARY" title="A source behind every finding." description="Inspect attributable evidence in the context of the claim it supports." /><WorkspaceNotice />
    <div className="ws-table-tools" style={{ paddingLeft: 0 }}><label className="ws-search"><Search size={15} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search sources and assets…" aria-label="Search evidence" /></label></div>
    {evidence.length ? <div className="ws-evidence-grid">{evidence.map(claim => <article className="ws-panel ws-evidence-card" key={claim.id}><FileText size={22} /><h3>{claim.evidence!.title}</h3><p>{claim.evidence!.excerpt || 'No excerpt was supplied.'}</p>
      <dl className="ws-definition ws-section-gap"><dt>Related asset</dt><dd>{claim.title}</dd><dt>Provider</dt><dd>{claim.evidence!.provider}</dd><dt>Retrieved</dt><dd>{claim.evidence!.retrievedAt || 'Not supplied'}</dd></dl>
      {safeUrl(claim.evidence!.url) && <a href={safeUrl(claim.evidence!.url)} target="_blank" rel="noreferrer">Open source <ExternalLink size={14} /></a>}</article>)}</div>
      : <section className="ws-panel"><EmptyState title={query ? 'No matching evidence' : 'No source records to display'} description={query ? 'Try another asset or source name.' : 'Sources returned by an investigation appear here with their attribution and related claim.'}><Link className="ws-button" href="/investigations">View investigations <ArrowRight size={14} /></Link></EmptyState></section>}</>;
}
export function DecisionsView() {
  const { claims, events } = useWorkspace();
  const [tab, setTab] = useState('review');
  return <><PageHeading eyebrow="REVIEW & DECISIONS" title="Keep every sign-off accountable." description="Review affected claims and inspect recorded decisions without losing their lineage." /><WorkspaceNotice />
    <div className="ws-tabs" role="tablist" aria-label="Review views">{[['review', 'Needs review'], ['preserved', 'Preserved approvals'], ['history', 'Decision history']].map(([key, label]) => <button id={`tab-${key}`} aria-controls="review-panel" role="tab" aria-selected={tab === key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)} key={key}>{label}</button>)}</div>
    <div id="review-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>{tab !== 'history' ? <ClaimTable key={tab} claims={claims.filter(claim => tab === 'preserved' ? ['preserved', 'reviewed'].includes(claim.status) : ['reopened', 'new', 'exception'].includes(claim.status))} title={tab === 'preserved' ? 'Approval continuity' : 'Reviewer queue'} />
      : <section className="ws-panel">{events.length ? <ul className="ws-timeline">{events.map((event, index) => <li key={event.event_id || index}><ShieldCheck size={18} /><div><h3>{event.action?.replace(/_/g, ' ') || 'Recorded decision'}</h3><p>{event.counsel_rationale || event.rationale || 'No rationale returned.'}</p><small>{event.reviewer_name || 'Recorded actor'} · {event.timestamp}</small><details className="ws-disclosure"><summary>Decision lineage</summary><dl className="ws-definition ws-section-gap"><dt>Asset key</dt><dd>{event.stable_lineage_key}</dd><dt>Prior decision</dt><dd>{event.prior_decision_id || 'Not supplied'}</dd><dt>Event digest</dt><dd>{event.event_hash || 'Not supplied'}</dd></dl></details></div></li>)}</ul> : <EmptyState title="No recorded decisions" description="Verified reviewer actions will appear here when returned by the production service." />}</section>}</div></>;
}
export function ProductionsView() {
  const { user, sample } = useWorkspace();
  return <><PageHeading eyebrow="PRODUCTIONS" title="A dedicated space for each production." description="Your current workspace is scoped to the production assigned to your session." /><WorkspaceNotice />
    <section className="ws-panel"><PanelTitle title={sample ? 'The Noir Protocol' : user?.production_id || 'Production'} description={sample ? 'Fictional feature production · Preview workspace' : 'Assigned production'} /><div className="ws-panel-body"><dl className="ws-definition"><dt>Access</dt><dd>{sample ? 'Read-only sample' : user?.role}</dd><dt>Organization</dt><dd>{sample ? 'Fictional studio' : user?.tenant_id}</dd><dt>Workspace</dt><dd>Clearance change control</dd></dl><Link className="ws-button primary ws-section-gap" href="/">Open production <ArrowRight size={14} /></Link></div></section></>;
}
export function SettingsView() {
  const { user, sample, setAccessOpen } = useWorkspace();
  return <><PageHeading eyebrow="WORKSPACE SETTINGS" title="The right access. The right context." description="Inspect your session and understand how responsibilities are separated." /><WorkspaceNotice />
    <div className="ws-evidence-grid"><section className="ws-panel"><PanelTitle title="Workspace identity" /><div className="ws-panel-body"><dl className="ws-definition"><dt>Member</dt><dd>{user?.display_name || 'Guest'}</dd><dt>Role</dt><dd>{user?.role || 'Read-only preview'}</dd><dt>Production</dt><dd>{user?.production_id || 'Fictional sample'}</dd><dt>Organization</dt><dd>{user?.tenant_id || 'Not signed in'}</dd></dl>{sample && <button className="ws-button ws-section-gap" onClick={() => setAccessOpen(true)}>Request an invitation</button>}</div></section>
      <section className="ws-panel"><PanelTitle title="Review responsibilities" /><div className="ws-panel-body ws-check-list"><div><CheckCircle2 size={15} /><span>Producers supply revision facts and supporting material.</span></div><div><ShieldCheck size={15} /><span>Authorized reviewers record clearance decisions for their assigned production.</span></div><div><CheckCircle2 size={15} /><span>Public preview access does not confer reviewer authority.</span></div></div></section></div>
    <section className="ws-panel ws-section-gap"><PanelTitle title="Workspace preferences" /><div className="ws-panel-body"><details className="ws-disclosure"><summary>Access and session recovery</summary><p>Returning members with a valid session open their workspace directly. Request a new invitation if your link is expired or already used.</p></details><details className="ws-disclosure"><summary>Production policy and budget controls</summary><p>Production policy and investigation limits are administered by the workspace owner. This screen does not change those controls. Contact your administrator for policy changes.</p></details></div></section></>;
}
