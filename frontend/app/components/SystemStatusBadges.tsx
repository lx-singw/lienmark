'use client';

/**
 * SystemStatusBadges Component
 * Dynamically queries /api/health to display live connection & authentication telemetry
 * for Google Gemini (Vertex AI ADC vs direct API Key vs Sandbox) and Parallel Search API.
 * Authored strictly under Google AntiGravity: Defensive, zero-any TypeScript implementation.
 */

import React, { useEffect, useState } from 'react';
import { Sparkles, Search } from 'lucide-react';

interface HealthData {
  status?: string;
  gemini_auth_mode?: string;
  is_vertex_ai?: boolean;
  integrations?: {
    gemini?: string;
    parallel_search?: string;
    gemini_auth_mode?: string;
    is_vertex_ai?: boolean;
  };
  credentials?: {
    gemini?: string;
    parallel_search?: string;
    gemini_preview?: string;
    parallel_preview?: string;
  };
}

export const SystemStatusBadges: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [isError, setIsError] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/health', {
          method: 'GET',
          signal: controller.signal,
          headers: { Accept: 'application/json' },
          cache: 'no-store',
        });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data: HealthData = await res.json();
        if (isMounted) {
          setHealth(data);
          setIsLoading(false);
          setIsError(false);
        }
      } catch {
        if (isMounted) {
          setIsError(true);
          setIsLoading(false);
        }
      } finally {
        clearTimeout(timeoutId);
      }
    };

    fetchHealth();

    // Re-check every 30 seconds for live telemetry
    const intervalId = setInterval(fetchHealth, 30000);

    return () => {
      isMounted = false;
      controller.abort();
      clearTimeout(timeoutId);
      clearInterval(intervalId);
    };
  }, []);

  // Determine Gemini State
  const geminiIntegration = health?.integrations?.gemini || 'simulated_deterministic';
  const geminiAuthMode =
    health?.gemini_auth_mode ||
    health?.integrations?.gemini_auth_mode ||
    (geminiIntegration === 'configured' ? 'VERTEX_ADC' : 'SANDBOX_MOCKED');
  const isVertex = health?.is_vertex_ai ?? (geminiAuthMode === 'VERTEX_ADC');
  const isGeminiConfigured = !isError && geminiIntegration === 'configured';

  let geminiLabel = 'Gemini 2.5';
  let geminiTitle = 'Gemini 2.5 Flash: Connecting...';
  if (isLoading) {
    geminiLabel = 'Gemini 2.5';
    geminiTitle = 'Gemini 2.5 Flash: Querying runtime health...';
  } else if (isError) {
    geminiLabel = 'Gemini 2.5 (Offline)';
    geminiTitle = 'Backend /api/health endpoint unreachable; operational status unknown';
  } else if (isGeminiConfigured && isVertex) {
    geminiLabel = 'Gemini 2.5 (Vertex AI ADC)';
    geminiTitle = `Google Cloud Vertex AI ADC: Connected & Authenticated (${health?.credentials?.gemini_preview || 'Active'})`;
  } else if (isGeminiConfigured) {
    geminiLabel = 'Gemini 2.5 (API Key)';
    geminiTitle = `Gemini 2.5 Flash: Direct API Key Connected (${health?.credentials?.gemini_preview || 'Active'})`;
  } else {
    geminiLabel = 'Gemini 2.5 (Sandbox)';
    geminiTitle = 'Gemini 2.5 Flash: Running in deterministic verified sandbox mode';
  }

  // Determine Parallel Search State
  const parallelIntegration = health?.integrations?.parallel_search || 'simulated_deterministic';
  const isParallelConfigured = !isError && parallelIntegration === 'configured';

  let parallelLabel = 'Parallel Search';
  let parallelTitle = 'Parallel Search API: Connecting...';
  if (isLoading) {
    parallelLabel = 'Parallel Search';
    parallelTitle = 'Parallel Search API: Querying runtime health...';
  } else if (isError) {
    parallelLabel = 'Parallel Search (Offline)';
    parallelTitle = 'Backend /api/health endpoint unreachable; operational status unknown';
  } else if (isParallelConfigured) {
    parallelLabel = 'Parallel Search (Connected)';
    parallelTitle = `Parallel Search v1 API: Active & Authenticated (${health?.credentials?.parallel_preview || 'Active'})`;
  } else {
    parallelLabel = 'Parallel Search (Sandbox)';
    parallelTitle = 'Parallel Search API: Running in deterministic verified sandbox mode';
  }

  return (
    <div className="flex items-center gap-2" role="region" aria-label="Runtime Integration Health Indicators">
      {/* Gemini 2.5 Badge */}
      <div
        title={geminiTitle}
        className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors ${
          isError
            ? 'border border-rose-500/30 bg-rose-950/30 text-rose-300'
            : isGeminiConfigured
            ? 'border border-purple-500/40 bg-purple-950/40 text-purple-300'
            : 'border border-amber-500/30 bg-amber-950/30 text-amber-300'
        }`}
      >
        <Sparkles
          className={`h-3 w-3 ${
            isError ? 'text-rose-400' : isGeminiConfigured ? 'text-purple-400' : 'text-amber-400'
          }`}
          aria-hidden="true"
        />
        <span className="hidden sm:inline font-medium text-[11px]">{geminiLabel}</span>
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            isError
              ? 'bg-rose-400'
              : isGeminiConfigured
              ? 'bg-emerald-400 animate-pulse'
              : 'bg-amber-400'
          }`}
        />
      </div>

      {/* Parallel Search Badge */}
      <div
        title={parallelTitle}
        className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors ${
          isError
            ? 'border border-rose-500/30 bg-rose-950/30 text-rose-300'
            : isParallelConfigured
            ? 'border border-sky-500/40 bg-sky-950/40 text-sky-300'
            : 'border border-amber-500/30 bg-amber-950/30 text-amber-300'
        }`}
      >
        <Search
          className={`h-3 w-3 ${
            isError ? 'text-rose-400' : isParallelConfigured ? 'text-sky-400' : 'text-amber-400'
          }`}
          aria-hidden="true"
        />
        <span className="hidden sm:inline font-medium text-[11px]">{parallelLabel}</span>
        <span
          className={`h-1.5 w-1.5 rounded-full ${
            isError
              ? 'bg-rose-400'
              : isParallelConfigured
              ? 'bg-emerald-400 animate-pulse'
              : 'bg-amber-400'
          }`}
        />
      </div>
    </div>
  );
};

export default SystemStatusBadges;
