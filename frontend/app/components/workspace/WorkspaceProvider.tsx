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
  snapshot: Record<string, unknown> | null;
  automation: Record<string, unknown>; mission: Record<string, unknown>;
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
    if (!audit?.statusUrl || audit.result || ['failed', 'FAILED', 'awaiting_results'].includes(audit.status)) return;
    let cancelled = false;
    let attempts = 0;
    const tick = async () => {
      try {
        const job = record(await requestJson(audit.statusUrl));
        if (job.audit_id !== audit.id) throw new Error('Audit reference mismatch.');
        const result = record(job.snapshot);
        const jobError = typeof job.error === 'string' ? job.error : undefined;
        if (!cancelled && (typeof result.snapshot_id === 'string' || job.status !== audit.status || jobError !== audit.error || JSON.stringify(job.calls) !== JSON.stringify(audit.progress))) setAudit({ ...audit, status: String(job.status || 'QUEUED'), progress: record(job.calls),
          result: typeof result.snapshot_id === 'string' ? result : undefined,
          snapshotId: typeof result.snapshot_id === 'string' ? result.snapshot_id : undefined,
          error: typeof job.error === 'string' ? job.error : undefined });
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
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null);
  const [automation, setAutomation] = useState<Record<string, unknown>>({});
  const [mission, setMission] = useState<Record<string, unknown>>({});
  const [selected, select] = useState<WorkspaceClaim | null>(null);
  const [accessOpen, setAccessOpen] = useState(false);
  const refresh = useCallback(async (quiet = false) => {
    if (!user) return;
    if (!quiet) setLoading(true); setError('');
    try {
      const state = record(await requestJson(`/api/clearance/productions/${encodeURIComponent(user.production_id)}`));
      if (!Array.isArray(state.claims)) throw new Error('The server did not return a clearance record list.');
      setClaims(state.claims.map(normalizeClaim));
      setSnapshot(state.snapshot ? record(state.snapshot) : null);
      setAutomation(record(state.automation));
      setMission(record(state.pending_audit || state.latest_audit));
      const pending = record(state.pending_audit);
      if (typeof pending.audit_id === 'string' && typeof pending.status_url === 'string')
        setAudit({ id: pending.audit_id, revisionId: String(pending.revision_id), statusUrl: pending.status_url, status: String(pending.status) });
      else if (typeof record(state.snapshot).snapshot_id === 'string') {
        const latest = record(state.snapshot);
        setAudit(previous => previous?.snapshotId === latest.snapshot_id ? previous : {
          id: String(latest.audit_id), revisionId: String(latest.revision_id), snapshotId: String(latest.snapshot_id),
          statusUrl: `/api/clearance/productions/${encodeURIComponent(user.production_id)}/audits/${encodeURIComponent(String(latest.audit_id))}`,
          status: 'COMPLETED', result: latest,
        });
      }
      const trail = state.events;
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
  useEffect(() => { if (!user) return; const timer = setInterval(() => void refresh(true), 3000); return () => clearInterval(timer); }, [user, refresh]);
  useEffect(() => { if (audit?.result || audit?.status === 'FAILED') void refresh(); }, [audit?.result, audit?.status, refresh]);
  useEffect(() => {
    if (!user) return;
    try {
      const saved = record(JSON.parse(sessionStorage.getItem(`lienmark:audit:${user.tenant_id}:${user.production_id}`) || 'null'));
      const prefix = `/api/clearance/productions/${encodeURIComponent(user.production_id)}/audits/`;
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
    resetSession(); setUser(null); setClaims([]); setEvents([]); setAudit(null); setSnapshot(null); select(null);
  };
  const displayUser = user && typeof record(automation.policy).production_name === 'string' ? { ...user, production_name: String(record(automation.policy).production_name) } : user;
  return <WorkspaceContext.Provider value={{ user: displayUser, checking, sample: !user, error, claims: user ? claims : sampleClaims,
    events, loading, audit, setAudit, snapshot, automation, mission, selected, select, accessOpen, setAccessOpen, refresh, signOut }}>{children}</WorkspaceContext.Provider>;
}
