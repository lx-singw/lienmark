'use client';

/**
 * IngestionActivityFeed Component
 * Real-time and polling activity feed showing recent storage events, Eventarc watcher status, and filter controls.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Inbox, AlertCircle } from 'lucide-react';
import type {
  IngestionEvent,
  IngestionFeedFilterState,
  WatcherStatus,
} from './types';
import { INITIAL_INGESTION_EVENTS } from './seed_data';
import { WatcherStatusBar } from './WatcherStatusBar';
import { IngestionFeedControls } from './IngestionFeedControls';
import { IngestionFeedItem } from './IngestionFeedItem';
import { DropzoneModal } from './DropzoneModal';

interface IngestionActivityFeedProps {
  initialEvents?: IngestionEvent[];
  defaultOrgId?: string;
  defaultProdId?: string;
  bucketName?: string;
}

export const IngestionActivityFeed: React.FC<IngestionActivityFeedProps> = ({
  initialEvents = INITIAL_INGESTION_EVENTS,
  defaultOrgId = 'studio-alpha',
  defaultProdId = 'prod-001',
  bucketName = 'lienmark-intake-storage',
}) => {
  const [events, setEvents] = useState<IngestionEvent[]>(initialEvents);
  const [filters, setFilters] = useState<IngestionFeedFilterState>({
    searchQuery: '',
    statusFilter: 'ALL',
    sourceFilter: 'ALL',
  });
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isDropzoneOpen, setIsDropzoneOpen] = useState<boolean>(false);
  const [watcherStatus, setWatcherStatus] = useState<WatcherStatus>({
    eventarcHealthy: true,
    pollerActive: true,
    lastSyncUtc: new Date().toISOString(),
    bucketUri: `gs://${bucketName}/organizations/`,
    activeWatchersCount: 3,
  });

  const fetchLiveEvents = useCallback(async () => {
    try {
      const res = await fetch('/api/ingest/events', {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.events) && data.events.length > 0) {
          setEvents(data.events);
        }
      }
    } catch {
      // Backend not yet running live; retain current client state
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await fetchLiveEvents();
    setWatcherStatus((prev) => ({ ...prev, lastSyncUtc: new Date().toISOString() }));
    setTimeout(() => setIsRefreshing(false), 500);
  }, [fetchLiveEvents]);

  useEffect(() => {
    if (!isPolling) return;
    const intervalId = setInterval(() => {
      fetchLiveEvents();
    }, 10000);
    return () => clearInterval(intervalId);
  }, [isPolling, fetchLiveEvents]);

  const handleUploadComplete = useCallback((runId: string) => {
    const newEvent: IngestionEvent = {
      eventId: `evt_drop_${Date.now()}`,
      timestampUtc: `${new Date().toISOString().replace('T', ' ').slice(0, 19)} UTC`,
      fileName: 'Draft_Milestone_Locked.pdf',
      fileSizeBytes: 1468006,
      orgId: defaultOrgId,
      prodId: defaultProdId,
      gcsPath: `gs://${bucketName}/organizations/${defaultOrgId}/productions/${defaultProdId}/locked/Draft_Milestone_Locked.pdf`,
      status: 'PROCESSING',
      runId,
      source: 'Dropzone',
      sourceDetails: 'Direct signed URL upload',
    };
    setEvents((prev) => [newEvent, ...prev]);
  }, [defaultOrgId, defaultProdId, bucketName]);

  const filteredEvents = useMemo(() => {
    return events.filter((evt) => {
      const q = filters.searchQuery.trim().toLowerCase();
      const matchesQuery =
        !q ||
        evt.fileName.toLowerCase().includes(q) ||
        evt.orgId.toLowerCase().includes(q) ||
        evt.prodId.toLowerCase().includes(q) ||
        (evt.runId && evt.runId.toLowerCase().includes(q));

      const matchesStatus =
        filters.statusFilter === 'ALL' || evt.status === filters.statusFilter;

      const matchesSource =
        filters.sourceFilter === 'ALL' || evt.source === filters.sourceFilter;

      return matchesQuery && matchesStatus && matchesSource;
    });
  }, [events, filters]);

  return (
    <div className="space-y-4 rounded-xl border border-slate-800 bg-[#090e1a]/95 p-5 text-slate-100 shadow-xl">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-base font-semibold text-slate-100">
            Storage Watchers & Background Ingestion
          </h3>
          <p className="text-xs text-slate-400">
            Autonomous Google Cloud Eventarc triggers and GCS bucket pollers routing locked screenplays to ADK clearance runs.
          </p>
        </div>
      </div>

      <WatcherStatusBar
        status={watcherStatus}
        isPolling={isPolling}
        onTogglePolling={() => setIsPolling(!isPolling)}
      />

      <IngestionFeedControls
        filters={filters}
        onFilterChange={setFilters}
        isRefreshing={isRefreshing}
        onRefresh={handleRefresh}
        onOpenUpload={() => setIsDropzoneOpen(true)}
      />

      <div className="space-y-2 pt-1">
        {filteredEvents.length > 0 ? (
          filteredEvents.map((evt) => (
            <IngestionFeedItem key={evt.eventId} event={evt} />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-800 p-10 text-center text-slate-400">
            <Inbox className="h-9 w-9 text-slate-600 mb-2" />
            <p className="text-sm font-medium text-slate-300">No matching ingestion events</p>
            <p className="text-xs text-slate-500 mt-1">
              Adjust search filters or upload a new locked script draft.
            </p>
            <button
              onClick={() => setFilters({ searchQuery: '', statusFilter: 'ALL', sourceFilter: 'ALL' })}
              className="mt-3 text-xs text-sky-400 hover:text-sky-300 underline"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>

      <DropzoneModal
        isOpen={isDropzoneOpen}
        onClose={() => setIsDropzoneOpen(false)}
        onUploadComplete={handleUploadComplete}
        defaultOrgId={defaultOrgId}
        defaultProdId={defaultProdId}
        bucketName={bucketName}
      />
    </div>
  );
};

export default IngestionActivityFeed;
