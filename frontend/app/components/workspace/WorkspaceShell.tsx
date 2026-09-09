'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, type ReactNode } from 'react';
import { ArrowUpRight, Activity, Building2, ChevronDown, ChevronRight, Clapperboard, FileCheck2, Files,
  GitCompareArrows, Inbox, LayoutDashboard, LogOut, Menu, Settings2, ShieldCheck, X } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import RequestAccessModal from '../auth/RequestAccessModal';
import { ClaimDetail } from './ClaimDetail';
import { productionName, roleLabel } from './labels';

const navigation = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/revisions', label: 'Revisions', icon: GitCompareArrows },
  { href: '/investigations', label: 'Investigations', icon: Activity },
  { href: '/evidence', label: 'Evidence library', icon: Files },
  { href: '/decisions', label: 'Review & decisions', icon: ShieldCheck },
  { href: '/delivery', label: 'Delivery', icon: FileCheck2 },
];
function Navigation({ close }: { close: () => void }) {
  const pathname = usePathname();
  return <nav aria-label="Main navigation" className="ws-nav">
    <span className="ws-nav-label">WORKSPACE</span>
    {navigation.map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={close}
      className={pathname === href ? 'active' : ''} aria-current={pathname === href ? 'page' : undefined}>
      <Icon size={18} strokeWidth={1.7} /><span>{label}</span>{pathname === href && <span className="ws-active-dot" />}
    </Link>)}
    <span className="ws-nav-label ws-nav-secondary">MANAGE</span>
    {[{ href: '/inbox', label: 'Action inbox', icon: Inbox }, { href: '/productions', label: 'Productions', icon: Building2 },
      { href: '/policy', label: 'Workspace settings', icon: Settings2 }].map(({ href, label, icon: Icon }) =>
      <Link key={href} href={href} onClick={close} className={pathname === href ? 'active' : ''} aria-current={pathname === href ? 'page' : undefined}>
        <Icon size={18} strokeWidth={1.7} /><span>{label}</span></Link>)}
  </nav>;
}
function AccountMenu() {
  const { user, sample, signOut, setAccessOpen } = useWorkspace();
  const [error, setError] = useState('');
  const logout = async () => {
    try { await signOut(); }
    catch { setError('Sign-out failed. Please retry.'); }
  };
  return <details className="ws-account">
    <summary><span className="ws-avatar">{user?.display_name.slice(0, 1) || 'G'}</span>
      <span><strong>{user?.display_name || 'Guest workspace'}</strong><small>{sample ? 'Read-only access' : roleLabel(user?.role)}</small></span><ChevronDown size={15} /></summary>
    <div className="ws-dropdown"><p>{sample ? 'Explore the sample. An invitation unlocks your assigned production.' : user?.email || 'Invited production member'}</p>
      {sample ? <button onClick={() => setAccessOpen(true)}><ArrowUpRight size={15} />Request access</button>
        : <button onClick={() => void logout()}><LogOut size={15} />Sign out</button>}
      {error && <p role="alert">{error}</p>}
    </div>
  </details>;
}
function TopBar({ toggle }: { toggle: () => void }) {
  const { sample, user, checking } = useWorkspace();
  const pathname = usePathname();
  const current = navigation.find(item => item.href === pathname)?.label || ({ '/inbox': 'Action inbox', '/productions': 'Productions', '/policy': 'Workspace settings' }[pathname]) || 'Workspace';
  return <header className="ws-topbar no-print">
    <div className="ws-breadcrumb"><button className="ws-icon-button ws-mobile-toggle" onClick={toggle} aria-label="Open navigation"><Menu size={21} /></button>
      <span className="ws-breadcrumb-production">{sample ? 'The Noir Protocol' : productionName(user)}</span><ChevronRight size={14} /><strong>{current}</strong></div>
    <div className="ws-topbar-end"><span className="ws-mode"><span />{checking ? 'Checking access' : sample ? 'Sample · Read-only' : 'Authenticated workspace'}</span><AccountMenu /></div>
  </header>;
}
export function WorkspaceShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { accessOpen, setAccessOpen, sample, user } = useWorkspace();
  return <div className="ws-app">
    <a className="ws-skip-link" href="#workspace-content">Skip to content</a>
    {mobileOpen && <button className="ws-nav-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`ws-sidebar no-print ${mobileOpen ? 'is-open' : ''}`}>
      <Link className="ws-brand" href="/" onClick={() => setMobileOpen(false)}><span className="ws-brand-icon"><ShieldCheck size={23} /></span><span>lienmark<span className="ws-brand-period">.</span></span></Link>
      <button className="ws-icon-button ws-sidebar-close" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X size={20} /></button>
      <Link href="/productions" className="ws-production-switch" onClick={() => setMobileOpen(false)}><span className="ws-production-icon"><Clapperboard size={18} /></span>
        <span><strong>{sample ? 'The Noir Protocol' : productionName(user)}</strong><small>{sample ? 'Fictional feature production' : 'Production workspace'}</small></span><ChevronDown size={14} /></Link>
      <Navigation close={() => setMobileOpen(false)} />
      <div className="ws-sidebar-bottom"><ShieldCheck size={18} /><div><strong>Clarity through every cut.</strong><p>Clearance change control for E&O.</p></div></div>
    </aside>
    <div className="ws-main"><TopBar toggle={() => setMobileOpen(true)} />
      <main id="workspace-content" tabIndex={-1} className="ws-content">{children}</main>
      <footer className="ws-footer no-print"><span>Lienmark · Clearance change control</span><span>Evidence informs. Authorized reviewers decide.</span></footer>
    </div>
    <RequestAccessModal isOpen={accessOpen} onClose={() => setAccessOpen(false)} />
    <ClaimDetail />
  </div>;
}
