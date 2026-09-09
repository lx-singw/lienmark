import type { WorkspaceUser } from './model';

/** Display text only. Never use these values as API identifiers or permissions. */
export function readableLabel(value: unknown, fallback = 'Not specified'): string {
  if (typeof value !== 'string' || !value.trim()) return fallback;
  const text = value.trim().replace(/[_-]+/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}

function workspaceName(id: string | undefined, kind: 'production' | 'organization') {
  const fallback = kind === 'production' ? 'Assigned production' : 'Your organization';
  if (!id) return fallback;
  if (id === 'live_verification') return 'Demo production';
  if (id === 'local_verification') return 'Demo studio';
  const name = id.replace(/^(?:production|prod|organization|org|tenant)[_-]/i, '');
  if (/^[a-f0-9-]{16,}$/i.test(name) || /^[a-z]+_[a-f0-9]{16,}$/i.test(name)) return fallback;
  return name.replace(/[_-]+/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
}

export function productionName(user: WorkspaceUser | null) {
  return user?.production_name?.trim() || workspaceName(user?.production_id, 'production');
}

export function organizationName(user: WorkspaceUser | null) {
  return user?.organization_name?.trim() || workspaceName(user?.tenant_id, 'organization');
}

export function roleLabel(role: string | undefined) {
  return ({ producer: 'Producer', reviewer: 'Reviewer', admin: 'Administrator' } as Record<string, string>)[role?.toLowerCase() || ''] || 'Production member';
}

export function statusLabel(status: unknown) {
  const labels: Record<string, string> = {
    new: 'Awaiting review', stale: 'Revalidation required', carried_forward: 'Approval preserved',
    re_attested: 'Approved by reviewer', exception: 'Open exception', removed: 'Removed from revision',
    queued: 'Queued', accepted: 'Submitted', processing: 'Investigating', started: 'In progress',
    completed: 'Completed', failed: 'Could not complete', awaiting_results: 'Awaiting results',
    sign_off: 'Approval recorded', reject: 'Exception recorded',
  };
  return typeof status === 'string' ? labels[status.toLowerCase()] || 'Review required' : 'Not reported';
}

export function savedDate(value: unknown) {
  if (typeof value !== 'string' || !Number.isFinite(Date.parse(value))) return 'Date not recorded';
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

export function revisionLabel(snapshot: Record<string, unknown> | null | undefined) {
  return snapshot ? `Current revision · ${savedDate(snapshot.created_at)}` : 'No revision submitted';
}
