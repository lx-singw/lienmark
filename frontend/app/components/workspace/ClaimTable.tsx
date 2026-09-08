'use client';
import { useState } from 'react';
import { ChevronRight, Music2, Image as ImageIcon, Film, Search } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { EmptyState, PanelTitle, StatusBadge } from './Primitives';
import { statusLabels, type WorkspaceClaim } from './model';

export function ClaimTable({ claims, title = 'Clearance across the revision', description = 'Inspect an asset to see its change, dependencies, and next action.' }: {
  claims: WorkspaceClaim[]; title?: string; description?: string;
}) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [category, setCategory] = useState('all');
  const { select } = useWorkspace();
  const categories = [...new Set(claims.map(claim => claim.category))];
  const filtered = claims.filter(claim => (status === 'all' || claim.status === status) && (category === 'all' || claim.category === category)
    && `${claim.title} ${claim.scene} ${claim.reason}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="ws-panel"><PanelTitle title={title} description={description}><span className="ws-count-pill">{claims.length}</span></PanelTitle>
    <div className="ws-table-tools"><label className="ws-search"><Search size={15} /><input aria-label="Search clearance assets" placeholder="Search assets or scenes…" value={query} onChange={e => setQuery(e.target.value)} /></label>
      <select className="ws-filter" aria-label="Filter by clearance status" value={status} onChange={e => setStatus(e.target.value)}><option value="all">All statuses</option>{Object.entries(statusLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
      <select className="ws-filter" aria-label="Filter by asset type" value={category} onChange={e => setCategory(e.target.value)}><option value="all">All asset types</option>{categories.map(value => <option key={value}>{value}</option>)}</select></div>
    {filtered.length ? <div className="ws-table-scroll"><table className="ws-table"><thead><tr><th scope="col">ASSET / OCCURRENCE</th><th scope="col">CLEARANCE STATUS</th><th scope="col">NEXT ACTION</th><th scope="col"><span className="sr-only">Details</span></th></tr></thead>
      <tbody>{filtered.map(claim => { const music = /music|recording|composition/i.test(claim.category); const Icon = music ? Music2 : /photo|art|image/i.test(claim.category) ? ImageIcon : Film;
        return <tr key={claim.id}><td><button className="ws-asset-button" onClick={() => select(claim)}><span className={`ws-asset-icon ${music ? 'music' : ''}`}><Icon size={16} /></span><span><strong>{claim.title}</strong><small>{claim.scene} · {claim.category}</small></span></button></td>
          <td><StatusBadge status={claim.status} /></td><td className="ws-muted">{claim.status === 'preserved' ? 'Carry forward' : claim.status === 'removed' ? 'No longer in cut' : 'Review details'}</td>
          <td><button className="ws-icon-button" aria-label={`Inspect ${claim.title}`} onClick={() => select(claim)}><ChevronRight size={16} /></button></td></tr>; })}</tbody></table></div>
      : <EmptyState title={claims.length ? 'No matching assets' : 'No clearance records yet'} description={claims.length ? 'Try another search or clear the filters.' : 'Recorded clearance claims will appear here when they are available.'} />}
    <div className="ws-table-footer"><span>{filtered.length} of {claims.length} assets</span><span>Decisions follow the evidence</span></div>
  </section>;
}
