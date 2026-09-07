'use client';

/**
 * Lienmark 6-Destination Dashboard Sidebar
 * Glassmorphic navigation linking Inbox, Productions, Investigations, Evidence, Decisions, and Policy.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Inbox,
  Film,
  Compass,
  FileCheck2,
  Gavel,
  SlidersHorizontal,
  ShieldCheck,
  Lock,
} from 'lucide-react';

interface NavItem {
  readonly label: string;
  readonly href: string;
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly badge?: string;
}

const NAV_ITEMS: ReadonlyArray<NavItem> = [
  { label: 'Inbox', href: '/inbox', icon: Inbox, badge: '3' },
  { label: 'Productions', href: '/productions', icon: Film },
  { label: 'Investigations', href: '/investigations', icon: Compass },
  { label: 'Evidence', href: '/evidence', icon: FileCheck2 },
  { label: 'Decisions', href: '/decisions', icon: Gavel },
  { label: 'Policy & Config', href: '/policy', icon: SlidersHorizontal },
];

function NavLinkItem({ item, isActive }: { item: NavItem; isActive: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={`group flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all ${
        isActive
          ? 'bg-gradient-to-r from-sky-500/20 to-indigo-500/10 text-sky-400 border border-sky-500/30 shadow-lg shadow-sky-950/40'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
      }`}
    >
      <div className="flex items-center gap-3">
        <Icon className={`h-4 w-4 transition-colors ${isActive ? 'text-sky-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
        <span>{item.label}</span>
      </div>
      {item.badge && (
        <span className="rounded-full bg-amber-500/20 border border-amber-500/40 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300">
          {item.badge}
        </span>
      )}
    </Link>
  );
}

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col justify-between border-r border-slate-800/80 bg-[#0e1424]/90 backdrop-blur-xl p-4 no-print select-none">
      <div className="space-y-6">
        {/* Brand Header */}
        <Link href="/inbox" className="flex items-center gap-3 px-2 py-1 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-indigo-600 shadow-md shadow-sky-500/20 ring-1 ring-white/20 group-hover:scale-105 transition-transform">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-base font-bold tracking-tight text-white group-hover:text-sky-400 transition-colors">
                Lienmark
              </span>
              <span className="rounded bg-sky-500/10 px-1.5 py-0.2 text-[9px] font-mono text-sky-400 border border-sky-500/20">
                E&amp;O Gate
              </span>
            </div>
            <p className="text-[10px] text-slate-400">Clearance Change Control</p>
          </div>
        </Link>

        {/* Navigation Menu */}
        <nav className="space-y-1.5" aria-label="Sidebar Navigation">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return <NavLinkItem key={item.href} item={item} isActive={isActive} />;
          })}
        </nav>
      </div>

      {/* Footer Identity & Statutory Badge */}
      <div className="space-y-3 pt-4 border-t border-slate-800/80 px-2">
        <div className="flex items-center gap-2 rounded-lg bg-slate-900/60 p-2 border border-slate-800 text-xs">
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <div className="truncate">
            <p className="font-semibold text-slate-200 truncate">Sarah Jenkins, Esq.</p>
            <p className="text-[10px] text-slate-400 truncate">Lead Clearance Counsel</p>
          </div>
        </div>
        <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span className="flex items-center gap-1">
            <Lock className="h-2.5 w-2.5 text-emerald-400" /> E&amp;O-2026.1
          </span>
          <span>Fail-Closed</span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
