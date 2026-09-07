'use client';

/**
 * IngestionFeedControls Component
 * Search inputs, status filters, source filters, and refresh triggers for the ingestion feed.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React from 'react';
import { Search, RefreshCw, UploadCloud } from 'lucide-react';
import type { IngestionFeedFilterState } from './types';

interface IngestionFeedControlsProps {
  filters: IngestionFeedFilterState;
  onFilterChange: (newFilters: IngestionFeedFilterState) => void;
  isRefreshing: boolean;
  onRefresh: () => void;
  onOpenUpload: () => void;
}

const STATUS_OPTIONS = [
  { value: 'ALL', label: 'All Statuses' },
  { value: 'QUEUED', label: 'Queued' },
  { value: 'PROCESSING', label: 'Processing' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'REJECTED_OUT_OF_SCOPE', label: 'Rejected' },
];

const SOURCE_OPTIONS = [
  { value: 'ALL', label: 'All Sources' },
  { value: 'CloudEvent Eventarc', label: 'Eventarc' },
  { value: 'GCS Poller', label: 'GCS Poller' },
  { value: 'Dropzone', label: 'Dropzone' },
];

export const IngestionFeedControls: React.FC<IngestionFeedControlsProps> = ({
  filters,
  onFilterChange,
  isRefreshing,
  onRefresh,
  onOpenUpload,
}) => {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-1 flex-wrap items-center gap-2">
        {/* Search Input */}
        <div className="relative min-w-[200px] flex-1 sm:max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            value={filters.searchQuery}
            onChange={(e) => onFilterChange({ ...filters, searchQuery: e.target.value })}
            placeholder="Search filename, org, prod, or run..."
            className="w-full rounded-md border border-slate-700 bg-slate-900/80 pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:border-sky-500 focus:outline-none"
          />
        </div>

        {/* Status Dropdown */}
        <select
          value={filters.statusFilter}
          onChange={(e) => onFilterChange({ ...filters, statusFilter: e.target.value })}
          className="rounded-md border border-slate-700 bg-slate-900/80 px-2.5 py-1.5 text-xs text-slate-300 focus:border-sky-500 focus:outline-none"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Source Dropdown */}
        <select
          value={filters.sourceFilter}
          onChange={(e) => onFilterChange({ ...filters, sourceFilter: e.target.value })}
          className="rounded-md border border-slate-700 bg-slate-900/80 px-2.5 py-1.5 text-xs text-slate-300 focus:border-sky-500 focus:outline-none"
        >
          {SOURCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        {/* Refresh Trigger */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 disabled:opacity-50"
          title="Refresh activity feed"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin text-sky-400' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>

        {/* Dropzone Upload Trigger */}
        <button
          onClick={onOpenUpload}
          className="flex items-center gap-1.5 rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-500"
        >
          <UploadCloud className="h-3.5 w-3.5" />
          <span>Upload Draft</span>
        </button>
      </div>
    </div>
  );
};
