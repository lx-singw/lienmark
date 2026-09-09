'use client';
import { RefreshCw } from 'lucide-react';
import { useWorkspace } from './WorkspaceProvider';
import { PageHeading } from './Primitives';
import { WorkspaceNotice } from './RecordViews';
import { ClaimTable } from './ClaimTable';
import { Clarifications } from './AutomationView';

export default function InboxView() {
  const { sample, claims, refresh, loading } = useWorkspace();
  return <><PageHeading eyebrow="ACTION INBOX" title="Know what needs your attention." description="Unresolved claims from the current production snapshot.">
    <button className="ws-button" disabled={sample || loading} onClick={() => void refresh()}><RefreshCw size={14} />Refresh inbox</button></PageHeading><WorkspaceNotice />
    <Clarifications /><ClaimTable claims={claims.filter(claim => ['reopened', 'exception', 'new'].includes(claim.status))} title={sample ? 'Illustrative action queue' : 'Production action queue'} />
  </>;
}
