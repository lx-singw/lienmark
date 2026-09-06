import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';
import {
  ShieldCheck,
  FileText,
  Activity,
  Film,
  Lock,
} from 'lucide-react';
import SystemStatusBadges from './components/SystemStatusBadges';

export const metadata: Metadata = {
  title: 'Lienmark — Clearance Change Control for E&O',
  description:
    'Deterministic clearance drift detection and E&O underwriter change control for motion picture and television productions.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0f1d] text-slate-100 antialiased flex flex-col selection:bg-sky-500/30 selection:text-sky-200">
        {/* Navigation Header */}
        <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#0a0f1d]/90 backdrop-blur-md no-print">
          <div className="mx-auto max-w-[1720px] px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-between gap-4">
              {/* Brand & Project Identity */}
              <div className="flex items-center gap-6">
                <Link
                  href="/"
                  className="group flex items-center gap-2.5 transition-transform hover:scale-[1.01]"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 shadow-md shadow-sky-500/20 ring-1 ring-white/20">
                    <ShieldCheck className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold tracking-tight text-white group-hover:text-sky-400 transition-colors">
                        Lienmark
                      </span>
                      <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[10px] font-medium text-sky-400 border border-sky-500/20">
                        Agentic Cinema
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 hidden sm:block">
                      Motion Picture & Television E&O Clearance Change Control
                    </p>
                  </div>
                </Link>
              </div>

              {/* Navigation Links */}
              <nav className="hidden md:flex items-center gap-1">
                <Link
                  href="/"
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800/80 hover:text-white transition-colors"
                >
                  <Activity className="h-4 w-4 text-sky-400" />
                  Reviewer Dashboard
                </Link>
                <Link
                  href="/report/proj_blockbuster_cinema"
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800/80 hover:text-white transition-colors"
                >
                  <FileText className="h-4 w-4 text-amber-400" />
                  Form E&O-2026 Schedule
                </Link>
              </nav>

              {/* System Telemetry & Status Indicators */}
              <div className="flex items-center gap-2 sm:gap-3">
                {/* Policy Standard Badge */}
                <div className="hidden xl:flex items-center gap-1.5 rounded-md border border-slate-700/60 bg-slate-900/80 px-2.5 py-1 text-xs text-slate-300">
                  <Lock className="h-3 w-3 text-emerald-400" />
                  <span className="font-mono text-[11px]">E&O-2026.1-DEVPOST</span>
                </div>

                {/* AI & Search Engine Health Indicators */}
                <SystemStatusBadges />
              </div>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1">
          {children}
        </main>

        {/* Statutory Footer */}
        <footer className="border-t border-slate-800/80 bg-slate-950/80 py-6 text-xs text-slate-500 no-print">
          <div className="mx-auto max-w-[1720px] px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-slate-400" />
              <span>
                Lienmark Clearance Change Control &copy; {new Date().getFullYear()} Blockbuster Cinema LLC &middot; Fail-Closed Warranty Protocol
              </span>
            </div>
            <div className="flex items-center gap-4 text-[11px]">
              <span className="text-slate-400">Agentic Cinema Track ($15,000 Parallel Prize Pool)</span>
              <span>&bull;</span>
              <span className="text-slate-400">Deterministic Invalidation Engine</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
