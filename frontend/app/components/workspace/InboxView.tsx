'use client';
import { useEffect, useState } from 'react';
import { RefreshCw, ChevronRight } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { requestJson } from './client';
import { record } from './model';
import { EmptyState, PageHeading, PanelTitle } from './Primitives';
import { WorkspaceNotice } from './RecordViews';
import { ClaimTable } from './ClaimTable';
export default function InboxView() {
  const { user, sample, claims, select } = useWorkspace();
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [reload, setReload] = useState(0);
  const [filter, setFilter] = useState('all');
  useEffect(() => {
    if (!user) return;
    let active = true;
    setLoading(true); setError('');
    requestJson(`/api/v1/dashboard/inbox?production_id=${encodeURIComponent(user.production_id)}`)
      .then(value => { if (active) { const data = record(value); if (!Array.isArray(data.items)) throw new Error('No inbox list was returned.'); setItems(data.items.map(record)); } })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Inbox unavailable.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user, reload]);
  const shown = items.filter(item => filter === 'all' || item.severity === filter);
  return <><PageHeading eyebrow="ACTION INBOX" title="Know what needs your attention." description="Review production tasks and follow each item to its supporting clearance record."><button className="ws-button" disabled={sample || loading} onClick={() => setReload(value => value + 1)}><RefreshCw size={14} />Refresh inbox</button></PageHeading><WorkspaceNotice />
    {sample ? <ClaimTable claims={claims.filter(claim => ['reopened', 'exception'].includes(claim.status))} title="Illustrative action queue" description="Sample claims show how unresolved work is surfaced." /> : <section className="ws-panel"><PanelTitle title="Production action queue"><select className="ws-filter" aria-label="Filter inbox by priority" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All priorities</option><option value="P0_CRITICAL">Critical</option><option value="P1_HIGH">High</option><option value="P2_MEDIUM">Medium</option><option value="P3_STANDARD">Standard</option></select></PanelTitle>
      {error && <div className="ws-error" role="alert">{error}</div>}{loading ? <div className="ws-loading" role="status">Loading production inbox…</div> : shown.length ? <ul className="ws-timeline">{shown.map((item, index) => { const claim = claims.find(c => c.id === item.stable_lineage_key); return <li key={String(item.inbox_id || index)}><div style={{ flex: 1 }}><span className="ws-count-pill">{String(item.severity || 'Unspecified').replace(/_/g, ' ')}</span><h3 style={{ marginTop: 10 }}>{String(item.summary_headline || item.asset_name || 'Production task')}</h3><p>{String(item.detailed_context || '')}</p><small>Assigned to: {String(item.assigned_to_name || 'Unassigned')}</small></div>{claim && <button className="ws-icon-button" aria-label={`Inspect ${claim.title}`} onClick={() => select(claim)}><ChevronRight size={18} /></button>}</li>; })}</ul> : !error && <EmptyState title="No matching action items" description="Tasks returned for this production will appear here. This list alone does not certify delivery readiness." />}</section>}</>;
}
