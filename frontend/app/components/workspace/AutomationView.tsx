'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, ArrowRight, FileUp, Radio, ShieldCheck } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { record } from './model';
import { requestJson } from './client';
import { savedDate } from './labels';
import { PanelTitle } from './Primitives';

const rows = (value: unknown) => Array.isArray(value) ? value.map(record) : [];
const stateName = (value: unknown) => ({ QUEUED: 'Queued', PROCESSING: 'Investigating', COMPLETED: 'Completed',
  FAILED: 'Needs attention', NO_CHANGE: 'No material change', WAITING_FOR_MATCH: 'Needs document assignment',
  WORKING: 'Working', BLOCKED: 'Blocked', PENDING: 'Waiting for information', WAITING_FOR_INFORMATION: 'Waiting for information', READY_FOR_REVIEW: 'Ready for reviewer', INCONCLUSIVE: 'Source check inconclusive', NEEDS_ATTENTION: 'Research needs attention', ASSIGNED: 'Assigned to clarification' }[String(value)] || String(value || 'Ready'));

export function MissionTimeline({ compact = false }: { compact?: boolean }) {
  const { mission, snapshot, automation, sample } = useWorkspace();
  if (sample) return null;
  const policy = record(automation.policy), trigger = record(mission.trigger || snapshot?.trigger);
  const tasks = rows(mission.tasks || snapshot?.tasks);
  const visible = compact ? tasks.slice(-3) : tasks;
  return <section className="ws-panel ws-section-gap"><PanelTitle title="Production activity" description={policy.enabled ? 'Automatic processing enabled · decisions remain with your reviewer' : 'Automatic processing paused'}><Radio size={18} /></PanelTitle>
    <div className="ws-panel-body"><p className="ws-progress-label"><Activity size={16} />{trigger.name ? String(trigger.name) : 'Connect a source and authorize a budget to start monitoring.'}</p>
      <p className="ws-muted">{automation.worker_available ? 'Worker connected' : 'Worker heartbeat unavailable'}{automation.worker_seen_at ? ` · Last seen ${savedDate(automation.worker_seen_at)}` : ''}</p>
      {Boolean(mission.status) && <p className="ws-muted">{stateName(mission.outcome || mission.status)} · {savedDate(mission.created_at)}</p>}
      {Boolean(mission.error) && <p className="ws-error" role="alert">{String(mission.error)}</p>}
      {rows(mission.recoveries).map((recovery, i) => <p key={i} className="ws-soft-box">Worker recovery: {String(recovery.completed_calls_reused)} completed call results retained. {String(recovery.reason)} {savedDate(recovery.recovered_at)}</p>)}
      {visible.length ? <ol className="ws-agent-timeline" aria-label="Recorded task handoffs">{visible.map(task => <li key={String(task.task_id)} className={String(task.status).toLowerCase()}>
        <div className="ws-agent-task-heading"><strong>{String(task.agent)}</strong><span>{stateName(task.status)}</span></div>
        <p>{String(task.objective)}</p>{Boolean(task.outcome) && <p className="ws-agent-outcome">{String(task.outcome)}</p>}
        <small>{task.handoff_from ? `From ${String(task.handoff_from)} · ` : ''}{savedDate(task.started_at)}</small>
      </li>)}</ol> : <p className="ws-muted">Actual tasks and handoffs will appear here when the worker accepts a source event.</p>}
      {compact && <Link className="ws-text-button" href="/investigations">View the investigation <ArrowRight size={14} /></Link>}
    </div></section>;
}

export function RevisionOutcome() {
  const { snapshot, claims, sample } = useWorkspace();
  const comparison = record(snapshot?.comparison);
  const entries = rows(snapshot?.claims).filter(c => c.state !== 'removed');
  if (sample || !comparison.baseline_snapshot_id) return null;
  const unresolved = claims.filter(c => !['preserved', 'reviewed', 'removed'].includes(c.status)).length;
  return <section className="ws-panel ws-section-gap"><PanelTitle title="What changed for delivery" description="Measured against the recorded baseline; reviewer decisions update the current result." />
    <div className="ws-panel-body ws-stat-list">{[
      ['Approvals before', comparison.approvals_before], ['Approvals preserved', claims.filter(c => c.status === 'preserved').length],
      ['Blockers before', comparison.blockers_before], ['Blockers now', unresolved], ['Missing facts resolved during audit', comparison.missing_facts_resolved],
      ['Elapsed time', `${Number(comparison.elapsed_seconds || 0).toFixed(1)} seconds`],
    ].map(([label, value]) => <div key={String(label)}><span>{String(label)}</span><strong>{String(value ?? 'Not available')}</strong></div>)}</div>
    <div className="ws-panel-body"><details className="ws-disclosure"><summary>Why each approval changed or carried forward</summary><div className="ws-table-scroll"><table className="ws-table"><thead><tr><th>ASSET</th><th>CHANGE BASIS</th><th>BEFORE → AFTER</th></tr></thead><tbody>{entries.map(entry => <tr key={String(entry.claim_id)}><td>{String(entry.description)}</td><td>{String(entry.change_basis || 'Refer to the recorded investigation.')}</td><td>{rows(entry.change_summary).map((change, i) => <p key={i}><strong>{String(change.field)}:</strong> {String(change.before || 'Not specified')} → {String(change.after || 'Not specified')}</p>)}</td></tr>)}</tbody></table></div></details></div>
  </section>;
}

export function DocumentArrival({ clarificationId }: { clarificationId?: string }) {
  const { user, refresh, automation } = useWorkspace();
  const [kind, setKind] = useState(clarificationId ? 'agreement' : 'revision');
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState('');
  if (!user) return null;
  async function upload(file?: File) {
    if (!file || !user) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const params = new URLSearchParams({ name: file.name, kind, ...(clarificationId ? { clarification_id: clarificationId } : {}) });
      const result = record(await requestJson(`/api/clearance/productions/${encodeURIComponent(user.production_id)}/documents?${params}`, {
        method: 'POST', body: file, headers: { 'Content-Type': 'application/octet-stream' },
      }));
      setMessage(result.duplicate ? 'This document is already recorded. No duplicate investigation was created.' : record(automation.policy).enabled ? 'Document received. The worker will process it automatically.' : 'Document received. Enable automatic processing in workspace settings to investigate it.');
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed.'); }
    finally { setBusy(false); }
  }
  return <div className="ws-document-arrival">
    {!clarificationId && <label className="ws-field">Document type<select value={kind} onChange={e => setKind(e.target.value)} disabled={busy}><option value="revision">Complete screenplay or cue sheet</option><option value="agreement">Agreement or release</option></select></label>}
    <label className="ws-upload-zone"><FileUp size={22} /><strong>{busy ? 'Receiving document…' : clarificationId ? 'Supply the requested agreement' : 'Add a production document'}</strong>
      <span>PDF with readable text, TXT, Fountain, FDX or JSON · up to 4 MB</span>
      <input type="file" aria-label={clarificationId ? 'Upload requested agreement' : 'Upload production document'} accept=".pdf,.txt,.fountain,.fdx,.json,.md" disabled={busy} onChange={e => { void upload(e.target.files?.[0]); e.target.value = ''; }} />
    </label>{message && <p role="status">{message}</p>}{error && <p className="ws-error" role="alert">{error}</p>}
  </div>;
}

export function Clarifications() {
  const { automation, sample } = useWorkspace();
  const questions = rows(automation.clarifications).filter(q => q.status === 'PENDING');
  if (sample || !questions.length) return null;
  return <section className="ws-panel ws-section-gap"><PanelTitle title="Waiting for information" description="Investigations resume automatically when a matching document arrives. Open questions retain their saved context." />
    <div className="ws-panel-body">{questions.map(q => <details className="ws-disclosure" key={String(q.clarification_id)}><summary>{String(q.description)}</summary>
      <ul>{(Array.isArray(q.questions) ? q.questions : []).map((question, i) => <li key={i}>{String(question)}</li>)}</ul>
      <DocumentArrival clarificationId={String(q.clarification_id)} />
    </details>)}</div></section>;
}

export function AutomationSettings() {
  const { user, automation, refresh, sample } = useWorkspace();
  const policy = record(automation.policy);
  const [enabled, setEnabled] = useState(false), [watch, setWatch] = useState(false);
  const [name, setName] = useState('Production workspace'), [perRun, setPerRun] = useState(1), [total, setTotal] = useState(5), [hours, setHours] = useState(24);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState('');
  useEffect(() => { setEnabled(Boolean(policy.enabled)); setWatch(Boolean(policy.watch_evidence)); setName(String(policy.production_name || 'Production workspace'));
    setPerRun(Number(policy.per_run_usd || 1)); setTotal(Number(policy.total_allowance_usd || 5)); setHours(Number(policy.evidence_interval_hours || 24));
  }, [policy.updated_at]); // Keep unsaved form edits stable during background polling.
  if (sample || !user) return null;
  async function save(e: React.FormEvent) {
    e.preventDefault(); if (!user) return; setBusy(true); setMessage('');
    try { await requestJson(`/api/clearance/productions/${encodeURIComponent(user.production_id)}/automation`, { method: 'PUT', body: JSON.stringify({
      enabled, watch_evidence: watch, production_name: name, per_run_usd: perRun, total_allowance_usd: total, evidence_interval_hours: hours,
    }) }); setMessage('Production policy saved.'); await refresh(); }
    catch (e) { setMessage(e instanceof Error ? e.message : 'Policy could not be saved.'); } finally { setBusy(false); }
  }
  return <section className="ws-panel ws-section-gap"><PanelTitle title="Automatic processing" description="Authorize source monitoring and a bounded research allowance for this production." /><form className="ws-panel-body ws-automation-form" onSubmit={save}>
    <label className="ws-field">Production name<input value={name} maxLength={120} required onChange={e => setName(e.target.value)} /></label>
    <label><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> Automatically process new cuts, agreements and reviewer directives</label>
    <label><input type="checkbox" checked={watch} onChange={e => setWatch(e.target.checked)} /> Periodically check previously relied-on public evidence</label>
    <div className="ws-automation-limits"><label className="ws-field">Per investigation allowance ($)<input type="number" min={0.05} max={5} step={0.05} required value={perRun} onChange={e => setPerRun(Number(e.target.value))} /></label>
      <label className="ws-field">Total authorized allowance ($)<input type="number" min={0.05} max={100} step={0.05} required value={total} onChange={e => setTotal(Number(e.target.value))} /></label>
      <label className="ws-field">Evidence check interval (hours)<input type="number" min={1} max={168} required value={hours} onChange={e => setHours(Number(e.target.value))} /></label></div>
    <p className="ws-muted">${Number(policy.reserved_usd || 0).toFixed(2)} reserved for dispatched calls · ${Number(policy.allocated_usd || 0).toFixed(2)} allocated to active jobs. Reservations are not provider invoices. Pausing stops new jobs; accepted jobs finish within their allowance.</p>
    <button className="ws-button primary" disabled={busy}><ShieldCheck size={15} />{busy ? 'Saving…' : 'Save processing policy'}</button>{message && <p role="status">{message}</p>}
    <details className="ws-disclosure"><summary>Connected folder details</summary><p>{automation.storage_configured ? 'A storage watcher is configured on the server. Files are detected independently of this browser.' : 'No server folder is connected yet. Document uploads use the same durable inbox.'}</p><p>Revision folder: <code>{String(automation.folder || '')}</code></p><p>Agreement folder: <code>{String(automation.agreement_folder || '')}</code></p></details>
  </form></section>;
}

export function SourceInbox() {
  const { automation, sample } = useWorkspace();
  if (sample) return null;
  const sources = rows(automation.sources);
  return <section className="ws-panel ws-section-gap"><PanelTitle title="Incoming changes" description="Documents and source checks persist here across worker restarts." /><div className="ws-panel-body"><DocumentArrival />
    {sources.length > 0 && <ul className="ws-timeline">{sources.map(source => <li key={String(source.event_id)}><div><strong>{String(source.name)}</strong><p>{stateName(source.status)}</p>{Boolean(source.reason) && <p>{String(source.reason)}</p>}<small>{savedDate(source.created_at)}</small>{source.status === 'WAITING_FOR_MATCH' && <AssignDocument eventId={String(source.event_id)} />}</div></li>)}</ul>}
    {!record(automation.policy).enabled && <p><Link href="/policy">Enable automatic processing in workspace settings <ArrowRight size={14} /></Link></p>}
  </div></section>;
}

function AssignDocument({ eventId }: { eventId: string }) {
  const { automation, user, refresh } = useWorkspace();
  const [question, setQuestion] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const questions = rows(automation.clarifications).filter(q => q.status === 'PENDING');
  async function assign() {
    if (!user || !question) return;
    setBusy(true); setError('');
    try { await requestJson(`/api/clearance/productions/${encodeURIComponent(user.production_id)}/documents/${eventId}/assign?clarification_id=${encodeURIComponent(question)}`, { method: 'POST' }); await refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Assignment failed.'); } finally { setBusy(false); }
  }
  return <div className="ws-document-arrival ws-section-gap"><label className="ws-field">Assign to an open question<select value={question} onChange={e => setQuestion(e.target.value)}><option value="">Select the related asset</option>{questions.map(q => <option key={String(q.clarification_id)} value={String(q.clarification_id)}>{String(q.description)}</option>)}</select></label>
    <button className="ws-button" disabled={!question || busy} onClick={() => void assign()}>{busy ? 'Assigning…' : 'Assign and resume investigation'}</button>{error && <p className="ws-error" role="alert">{error}</p>}</div>;
}


