import React from 'react';
import { Sidebar } from './components/Sidebar';
import { TopNav } from './components/TopNav';
import { OfflineConnectivityBanner } from '@/components/network';

/**
 * Lienmark Dashboard Layout
 * 6-Destination shell with modern cinema dark mode (#0B0F17) and glassmorphism.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

export default function DashboardLayout({
  children,
}: {
  readonly children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen w-full bg-[#0B0F17] text-slate-100 overflow-hidden relative">
      {/* Global Offline Connectivity Watchdog Banner */}
      <OfflineConnectivityBanner />

      {/* 6-Destination Navigation Sidebar */}
      <Sidebar />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-y-auto p-6 relative">
          {children}
        </main>
      </div>
    </div>
  );
}
