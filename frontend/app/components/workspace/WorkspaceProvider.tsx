'use client';

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { SupersessionEvent } from '@/lib/types';
import { normalizeClaim, record, type WorkspaceClaim, type WorkspaceUser, type ActiveAudit } from './model';
import { sampleClaims } from './sample';
import { loadSession, requestJson, resetSession } from './client';

interface WorkspaceContextValue {
  user: WorkspaceUser | null; checking: boolean; sample: boolean; error: string;
  claims: WorkspaceClaim[]; events: SupersessionEvent[]; loading: boolean;
  audit: ActiveAudit | null; setAudit: (audit: ActiveAudit | null) => void;
  selected: WorkspaceClaim | null; select: (claim: WorkspaceClaim | null) => void;
  accessOpen: boolean; setAccessOpen: (open: boolean) => void;
  refresh: () => Promise<void>; signOut: () => Promise<void>;
}
const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);
export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error('WorkspaceProvider is required.');
  return context;
}
function useAuditPolling(audit: ActiveAudit | null, setAudit: (audit: ActiveAudit | null) => void) {
  useEffect(() => {
    if (!audit?.statusUrl || audit.result || ['failed', 'awaiting_results'].includes(audit.status)) return;
    let cancelled = false;
    let attempts = 0;
    const tick = async () => {
      try {
        const result = record(await requestJson(audit.statusUrl));
        if (typeof result.snapshot_id !== 'string' || result.audit_id !== audit.id) throw new Error('Snapshot unavailable.');
        if (!cancelled) setAudit({ ...audit, result, status: String(result.status || 'results_available'),
          snapshotId: typeof result.snapshot_id === 'string' ? result.snapshot_id : undefined, error: undefined });
      } catch (error) {
        attempts += 1;
        if (!cancelled && attempts >= 15) {
          setAudit({ ...audit, status: 'awaiting_results', error: 'Results are not available yet. Refresh to check again.' });
          clearInterval(timer);
        }
      }
    };
    const timer = setInterval(tick, 4000);
    void tick();
    return () => { cancelled = true; clearInterval(timer); };
  }, [audit, setAudit]);
}
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<WorkspaceUser | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState('');
  const [claims, setClaims] = useState<WorkspaceClaim[]>([]);
  const [events, setEvents] = useState<SupersessionEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [audit, setAudit] = useState<ActiveAudit | null>(null);
  const [selected, select] = useState<WorkspaceClaim | null>(null);
  const [accessOpen, setAccessOpen] = useState(false);
  const refresh = useCallback(async () => {
    if (!user) return;
    setLoading(true); setError('');
    try {
      const scope = `production_id=${encodeURIComponent(user.production_id)}`;
      const [stateResponse, trailResponse] = await Promise.allSettled([
        requestJson(`/api/claims?${scope}`), requestJson(`/api/review/audit-trail?${scope}`),
      ]);
      if (stateResponse.status === 'rejected') throw stateResponse.reason;
      const state = record(stateResponse.value);
      if (!Array.isArray(state.claims)) throw new Error('The server did not return a clearance record list.');
      setClaims(state.claims.map(normalizeClaim));
      if (trailResponse.status === 'rejected') throw new Error('Decision history could not be loaded. Refresh to retry.');
      const trail = Array.isArray(trailResponse.value) ? trailResponse.value : record(trailResponse.value).events;
      setEvents(Array.isArray(trail) ? trail as SupersessionEvent[] : []);
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to load workspace.'); }
    finally { setLoading(false); }
  }, [user]);
  useEffect(() => {
    let active = true;
    loadSession().then(value => { if (active) setUser(value); })
      .catch(() => { if (active) { setError('This invitation could not be redeemed. Request a new invitation.'); setAccessOpen(true); } })
      .finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (!user) return;
    try {
      const saved = record(JSON.parse(sessionStorage.getItem(`lienmark:audit:${user.tenant_id}:${user.production_id}`) || 'null'));
      const prefix = `/api/tenants/${encodeURIComponent(user.tenant_id)}/productions/${encodeURIComponent(user.production_id)}/revisions/`;
      if (typeof saved.id === 'string' && typeof saved.revisionId === 'string' && typeof saved.statusUrl === 'string' && saved.statusUrl.startsWith(prefix))
        setAudit({ id: saved.id, revisionId: saved.revisionId, statusUrl: saved.statusUrl, status: 'accepted' });
    } catch { /* A blocked browser store does not prevent workspace access. */ }
  }, [user]);
  useEffect(() => {
    if (!user || !audit) return;
    try { sessionStorage.setItem(`lienmark:audit:${user.tenant_id}:${user.production_id}`, JSON.stringify({ id: audit.id, revisionId: audit.revisionId, statusUrl: audit.statusUrl })); }
    catch { /* Audit results remain available in this workspace session. */ }
  }, [user, audit]);
  useAuditPolling(audit, setAudit);
  const signOut = async () => {
    await requestJson('/api/auth/logout', { method: 'POST' });
    try { if (user) sessionStorage.removeItem(`lienmark:audit:${user.tenant_id}:${user.production_id}`); } catch { /* Storage may be unavailable. */ }
    resetSession(); setUser(null); setClaims([]); setEvents([]); setAudit(null); select(null);
  };
  return <WorkspaceContext.Provider value={{ user, checking, sample: !user, error, claims: user ? claims : sampleClaims,
    events, loading, audit, setAudit, selected, select, accessOpen, setAccessOpen, refresh, signOut }}>{children}</WorkspaceContext.Provider>;
}
