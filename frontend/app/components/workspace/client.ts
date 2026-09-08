import { record, type WorkspaceUser } from './model';

let csrfToken = '';
export async function requestJson(path: string, init?: RequestInit): Promise<unknown> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set('Content-Type', 'application/json');
  if (csrfToken && init?.method && init.method !== 'GET') headers.set('X-CSRF-Token', csrfToken);
  const response = await fetch(path, { ...init, signal: init?.signal || AbortSignal.timeout(20000), headers, credentials: 'same-origin', cache: 'no-store' });
  const token = response.headers.get('X-CSRF-Token') || response.headers.get('X-Session-ID');
  if (token) csrfToken = token;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = record(data).detail;
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}). Please try again.`);
  }
  return data;
}
export function parseUser(value: unknown): WorkspaceUser | null {
  const outer = record(value);
  const source = typeof outer.role === 'string' ? outer : record(outer.user);
  const fields = ['role', 'tenant_id', 'production_id'] as const;
  if (fields.some(field => typeof source[field] !== 'string' || !source[field])) return null;
  return {
    role: String(source.role), tenant_id: String(source.tenant_id), production_id: String(source.production_id),
    display_name: typeof source.display_name === 'string' ? source.display_name : 'Invited member',
    email: typeof source.email === 'string' ? source.email : '',
  };
}
let sessionRequest: Promise<WorkspaceUser | null> | undefined;
export function loadSession(): Promise<WorkspaceUser | null> {
  if (sessionRequest) return sessionRequest;
  sessionRequest = (async () => {
    const url = new URL(window.location.href);
    const invite = url.searchParams.get('invite');
    if (invite) {
      url.searchParams.delete('invite');
      window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
      await requestJson('/api/auth/redeem-invite', { method: 'POST', body: JSON.stringify({ invite_token: invite }) });
    }
    try { return parseUser(await requestJson('/api/auth/session')); }
    catch { return null; }
  })();
  return sessionRequest;
}
export function resetSession() { sessionRequest = undefined; csrfToken = ''; }
