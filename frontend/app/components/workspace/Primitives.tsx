import { ArrowUpRight, LockKeyhole, SearchX } from 'lucide-react';
import type { ReactNode } from 'react';
import type { ClaimStatus } from './model';
import { statusLabels } from './model';

export function StatusBadge({ status }: { status: ClaimStatus }) {
  return <span className={`ws-status ${status}`}><i />{statusLabels[status]}</span>;
}
export function PageHeading({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) {
  return <div className="ws-page-heading"><div><p className="ws-eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div><div className="ws-heading-actions">{children}</div></div>;
}
export function SampleNotice({ onRequest }: { onRequest: () => void }) {
  return <div className="ws-sample-notice"><LockKeyhole size={16} /><p><strong>Sample workspace.</strong> Fictional records illustrate the workflow. Counts are examples, not live audit results.</p>
    <button onClick={onRequest}>Request access <ArrowUpRight size={14} /></button></div>;
}
export function EmptyState({ title, description, children }: { title: string; description: string; children?: ReactNode }) {
  return <div className="ws-empty"><span className="ws-empty-icon"><SearchX size={24} /></span><h3>{title}</h3><p>{description}</p>{children}</div>;
}
export function ReferenceNotice() {
  return <div className="ws-sample-notice"><LockKeyhole size={16} /><p><strong>Production records.</strong> Findings support review. Only an authorized reviewer can record a clearance decision.</p></div>;
}
export function PanelTitle({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return <div className="ws-panel-heading"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{children}</div>;
}
