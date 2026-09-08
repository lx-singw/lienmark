'use client';
import { useState, type FormEvent } from 'react';
import { ExternalLink, X, ShieldCheck } from 'lucide-react';
import { Dialog } from './Dialog';
import { StatusBadge } from './Primitives';
import { useWorkspace } from './WorkspaceProvider';
import { requestJson } from './client';
import { safeUrl, type WorkspaceClaim } from './model';

function DecisionForm({ claim }: { claim: WorkspaceClaim }) {
  const { user, refresh, select } = useWorkspace();
  const [action, setAction] = useState('reject');
  const [rationale, setRationale] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!user || !claim.decisionId || !rationale.trim() || busy) return;
    setBusy(true); setError('');
    try {
      await requestJson(`/api/v1/claims/${encodeURIComponent(claim.decisionId)}/decision?production_id=${encodeURIComponent(user.production_id)}`, { method: 'POST', body: JSON.stringify({
        action, counsel_id: user.email || user.display_name, counsel_name: user.display_name,
        ...(action === 'reject' ? { directive_text: rationale.trim() } : { citation_text: rationale.trim() }),
      }) });
      await refresh(); select(null);
    } catch (err) { setError(err instanceof Error ? err.message : 'Decision could not be saved.'); }
    finally { setBusy(false); }
  }
  return <form onSubmit={submit}><h3>Record a reviewer decision</h3><p>Your decision is submitted under your current production session.</p>
    <label className="ws-field" style={{ marginTop: 16 }}>Decision<select value={action} onChange={e => setAction(e.target.value)}><option value="reject">Return for investigation</option><option value="sign_off">Sign off with supporting citation</option></select></label>
    <label className="ws-field" style={{ marginTop: 14 }}>{action === 'reject' ? 'Investigation directive' : 'Supporting citation and rationale'}<textarea required minLength={3} value={rationale} onChange={e => setRationale(e.target.value)} placeholder="Explain the basis for your decision…" /></label>
    {error && <div className="ws-error" role="alert">{error}</div>}<button className="ws-button primary" disabled={busy || rationale.trim().length < 3} style={{ marginTop: 16 }}><ShieldCheck size={15} />{busy ? 'Saving decision…' : 'Record decision'}</button>
  </form>;
}
export function ClaimDetail() {
  const { selected: claim, select, sample, user, setAccessOpen } = useWorkspace();
  const canReview = !!user && ['REVIEWER', 'ADMIN'].includes(user.role.toUpperCase());
  return <Dialog open={!!claim} onClose={() => select(null)} label={claim ? `Clearance details: ${claim.title}` : 'Clearance details'} drawer>
    {claim && <><div className="ws-dialog-header"><span className="ws-eyebrow">CLEARANCE DETAIL</span><button className="ws-icon-button" aria-label="Close asset details" onClick={() => select(null)}><X size={20} /></button></div>
      <p className="ws-muted">{claim.scene} · {claim.category}</p><h2>{claim.title}</h2><StatusBadge status={claim.status} />
      <div className="ws-diff-boxes"><div><span>Baseline</span><p>{claim.before}</p></div><div><span>Current revision</span><p>{claim.after}</p></div></div>
      <section className="ws-detail-section"><h3>Why this status</h3><p>{claim.reason}</p></section>
      <section className="ws-detail-section"><h3>Next action</h3><p>{claim.nextAction}</p></section>
      <section className="ws-detail-section"><h3>Supporting evidence</h3>{claim.evidence ? <><p>{claim.evidence.excerpt}</p>{safeUrl(claim.evidence.url) && <a className="ws-text-button" href={safeUrl(claim.evidence.url)} target="_blank" rel="noreferrer" style={{ marginTop: 12 }}>{claim.evidence.title}<ExternalLink size={14} /></a>}</> : <p>{sample ? 'This fictional example has no live evidence attached. Authenticated investigations can provide attributable sources here.' : 'No supporting evidence was returned for this claim.'}</p>}</section>
      <section className="ws-detail-section">{!sample && canReview && claim.decisionId ? <DecisionForm key={claim.id} claim={claim} /> : <><h3>Reviewer authority</h3><p>{sample ? 'An invitation is required to submit revisions or record decisions.' : !claim.decisionId ? 'This comparison record has no actionable claim reference. Open a production claim with a verified identifier to record a decision.' : 'Only an authorized reviewer assigned to this production can record clearance decisions.'}</p>{sample && <button className="ws-button" style={{ marginTop: 15 }} onClick={() => { select(null); setAccessOpen(true); }}>Request workspace access</button>}</>}</section></>}
  </Dialog>;
}
