import type { Metadata } from 'next';
import './globals.css';
import './workspace.css';
import { WorkspaceProvider } from './components/workspace/WorkspaceProvider';
import { WorkspaceShell } from './components/workspace/WorkspaceShell';
export const metadata: Metadata = {
  title: 'Lienmark — Clearance Change Control',
  description: 'Track clearance drift, preserve unaffected decisions, and keep the delivery record aligned with each production revision.',
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><WorkspaceProvider><WorkspaceShell>{children}</WorkspaceShell></WorkspaceProvider></body></html>;
}