'use client';
import Link from 'next/link';
import { ArrowRight, Radio } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { productionOutcome } from './outcome';

export function ProductionOutcome() {
  const { snapshot, mission, automation, sample } = useWorkspace();
  if (sample) return null;
  const result = productionOutcome(snapshot, mission, automation);
  return <section className="ws-outcome ws-section-gap" aria-label="Production outcome">
    <div className="ws-outcome-heading"><span className="ws-eyebrow"><Radio size={14} /> {result.active ? 'WORK IN PROGRESS' : 'CURRENT PRODUCTION POSITION'}</span><h2>{result.title}</h2><p>{result.next[2]}</p></div>
    <div className="ws-outcome-grid">
      <div><span>What arrived</span><strong>{result.trigger}</strong><Link href="/investigations">Inspect the source event</Link></div>
      <div><span>What changed</span><strong>{result.changeDescription}</strong><small>{result.active ? 'Comparison updates when the investigation finishes.' : `${result.total} active claims in the saved record`}</small></div>
      <div><span>What remains valid</span><strong>{result.preserved} approvals preserved</strong><small>{result.approved} total recorded approvals</small></div>
      <div><span>What needs attention</span><strong>{result.total ? `${result.blockers} unresolved claims` : 'No review record yet'}</strong><small>{result.completedCalls} completed calls in the latest investigation</small></div>
    </div>
    <div className="ws-outcome-footer"><p>{result.active ? 'Figures below refer to the last saved snapshot until the new result is published.' : 'Source evidence supports findings. Only an assigned reviewer records clearance decisions.'}</p><Link className="ws-button primary" href={result.next[1]}>{result.next[0]}<ArrowRight size={14} /></Link></div>
  </section>;
}
