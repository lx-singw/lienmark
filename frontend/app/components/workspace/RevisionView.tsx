'use client';
import { useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowRight, GitCompareArrows, Plus, Trash2, Check } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { PageHeading, PanelTitle, SampleNotice, ReferenceNotice } from './Primitives';
import { requestJson } from './client';
import { record } from './model';
import { revisionLabel, statusLabel } from './labels';
import { SourceInbox } from './AutomationView';

interface Change { stable_lineage_key: string; description: string; duration_or_prominence?: string; intended_territory?: string[]; intended_media?: string[] }
export default function RevisionView() {
  const { sample, user, claims, setAccessOpen, setAudit, audit, snapshot } = useWorkspace();
  const parent = String(snapshot?.revision_id || '');
  const [source, setSource] = useState('');
  const [budget, setBudget] = useState('1');
  const [asset, setAsset] = useState('');
  const [prominence, setProminence] = useState('');
  const [territory, setTerritory] = useState('');
  const [media, setMedia] = useState('');
  const [changes, setChanges] = useState<Change[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const retry = useRef<{ body: string; key: string } | null>(null);
  const selected = claims.find(claim => claim.id === asset);
  const canSubmit = !!user && ['PRODUCER', 'REVIEWER', 'ADMIN'].includes(user.role.toUpperCase());
  function addChange(event: FormEvent) {
    event.preventDefault();
    if (!selected || !(prominence.trim() || territory.trim() || media.trim())) return;
    const split = (value: string) => value.split(',').map(item => item.trim()).filter(Boolean);
    const change: Change = { stable_lineage_key: selected.id, description: selected.title,
      ...(prominence.trim() ? { duration_or_prominence: prominence.trim() } : {}),
      ...(territory.trim() ? { intended_territory: split(territory) } : {}),
      ...(media.trim() ? { intended_media: split(media) } : {}),
    };
    setChanges(prior => [...prior.filter(item => item.stable_lineage_key !== selected.id), change]);
    setAsset(''); setProminence(''); setTerritory(''); setMedia('');
  }
  async function submit() {
    if (sample) { setAccessOpen(true); return; }
    if (!user || !canSubmit || (!parent && source.trim().length < 20) || busy) return;
    setBusy(true); setError('');
    const body = JSON.stringify({ production_id: user.production_id, max_spend_usd: Number(budget),
      ...(parent ? { parent_revision_id: parent, expected_parent_snapshot_id: snapshot?.snapshot_id, revised_uses: changes } : { source_text: source.trim() }) });
    if (retry.current?.body !== body) retry.current = { body, key: crypto.randomUUID() };
    try {
      const result = record(await requestJson('/api/clearance/revisions', { method: 'POST', headers: { 'Idempotency-Key': retry.current.key }, body }));
      const expectedPath = `/api/clearance/productions/${encodeURIComponent(user.production_id)}/audits/${encodeURIComponent(String(result.audit_id))}`;
      if (typeof result.audit_id !== 'string' || typeof result.revision_id !== 'string' || result.status_url !== expectedPath)
        throw new Error('The server accepted the request but did not return a usable audit reference. Retry safely to retrieve it.');
      setAudit({ id: result.audit_id, revisionId: result.revision_id, statusUrl: result.status_url, status: 'accepted' });
      setChanges([]); retry.current = null;
    } catch (err) { setError(err instanceof Error ? err.message : 'The revision could not be submitted.'); }
    finally { setBusy(false); }
  }
  return <><PageHeading eyebrow="REVISION CONTROL" title="Make the change. Keep the context." description="Describe changed uses, then submit a revision against its recorded baseline." />
    {sample ? <SampleNotice onRequest={() => setAccessOpen(true)} /> : <ReferenceNotice />}
    <SourceInbox />
    {audit && <div className="ws-soft-box ws-section-gap" role="status">Revision audit · {audit.result ? 'Results available' : statusLabel(audit.status)} <Link href="/investigations" className="ws-text-button">View audit <ArrowRight size={14} /></Link></div>}
    {error && <div className="ws-error" role="alert">{error}</div>}
    <div className="ws-form-layout ws-section-gap"><section className="ws-panel">
      <div className="ws-form-section"><h3>{parent ? '01 / Confirm the baseline' : '01 / Add source material'}</h3><p>{parent ? 'The version against which these changes will be evaluated.' : 'Start with your actual scene or cue sheet. No claims or approvals are preloaded.'}</p>
        {parent ? <label className="ws-field">Current baseline<input readOnly value={revisionLabel(snapshot)} /><small>Uses your latest saved review record. Submit without changes to re-investigate unresolved claims.</small></label> : <label className="ws-field">Screenplay excerpt or cue sheet<textarea value={source} onChange={e => setSource(e.target.value)} minLength={20} maxLength={24000} rows={8} placeholder="Paste actual scene or cue-sheet text. Include asset names, occurrences and intended use." /><small>Initial intake supports up to 20 occurrences. Text is sent to Gemini for extraction; public asset descriptions are used for live web searches.</small></label>}
        <label className="ws-field" style={{ marginTop: 16 }}>Investigation reservation limit (USD)<input type="number" min="0.05" max="5" step="0.05" value={budget} onChange={e => setBudget(e.target.value)} /><small>Reservations limit provider dispatches; provider invoices remain the source of billed cost.</small></label></div>
      {(parent || sample) && <><form onSubmit={addChange}><div className="ws-form-section"><h3>02 / Describe a changed use</h3><p>Stage one or more changes. Fields left blank retain their baseline values.</p>
        <div className="ws-form-grid"><label className="ws-field full">Asset occurrence<select required value={asset} onChange={e => setAsset(e.target.value)}><option value="">Select an asset…</option>{claims.map(claim => <option key={claim.id} value={claim.id}>{claim.title} · {claim.scene}</option>)}</select></label>
          <label className="ws-field full">Duration or prominence<input value={prominence} onChange={e => setProminence(e.target.value)} placeholder="e.g. 14 seconds, foreground close-up" /></label>
          <label className="ws-field">Intended territories<input value={territory} onChange={e => setTerritory(e.target.value)} placeholder="e.g. United States, Canada" /><small>Separate multiple territories with commas.</small></label>
          <label className="ws-field">Intended media<input value={media} onChange={e => setMedia(e.target.value)} placeholder="e.g. theatrical, trailer" /><small>Describe the intended distribution scope.</small></label></div>
        <button className="ws-button" style={{ marginTop: 20 }} disabled={!asset || !(prominence.trim() || territory.trim() || media.trim()) || busy}><Plus size={15} />Stage change</button></div></form>
      <div className="ws-form-section"><h3>03 / Review staged changes <span className="ws-count-pill">{changes.length}</span></h3>
        {changes.length ? <ul className="ws-change-list">{changes.map(change => <li key={change.stable_lineage_key}><div><strong>{change.description}</strong><p>{[change.duration_or_prominence, change.intended_territory?.join(', '), change.intended_media?.join(', ')].filter(Boolean).join(' · ')}</p></div><button className="ws-icon-button" aria-label={`Remove change to ${change.description}`} disabled={busy} onClick={() => setChanges(prior => prior.filter(item => item !== change))}><Trash2 size={16} /></button></li>)}</ul> : <p>No changes staged. Add an occurrence above to begin.</p>}</div></>}
      <div className="ws-form-footer"><p>{sample ? 'Preview the editor freely. Running an audit requires an invitation.' : 'Submitting creates a revision and may incur investigation costs.'}</p><button className="ws-button primary" onClick={() => void submit()} disabled={busy || (!sample && (!canSubmit || (!parent && source.trim().length < 20)))}><GitCompareArrows size={15} />{busy ? 'Submitting…' : sample ? 'Request access to run audit' : parent ? 'Submit revision audit' : 'Investigate initial intake'}</button></div>
    </section><aside className="ws-stack"><section className="ws-panel"><PanelTitle title="What happens next" /><div className="ws-panel-body ws-check-list"><div><Check size={15} /><span>Compare each changed use with its recorded baseline.</span></div><div><Check size={15} /><span>Identify affected dependencies and preserve unaffected decisions.</span></div><div><Check size={15} /><span>Review available results before preparing a delivery schedule.</span></div></div></section>
      <div className="ws-soft-box"><h3>Be specific about the use.</h3><p>A longer cue, a more prominent image, or a broader distribution scope can change the basis of an earlier clearance.</p></div></aside></div></>;
}
