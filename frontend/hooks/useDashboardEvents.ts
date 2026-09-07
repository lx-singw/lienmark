'use client';

/**
 * useDashboardEvents Hook
 * Connects to SSE stream with 25s heartbeat watchdog, window online re-trigger,
 * and jittered exponential backoff.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface DashboardEvent {
  readonly id?: string;
  readonly type: string;
  readonly message?: string;
  readonly timestamp: string;
  readonly data?: Record<string, unknown>;
}

export type StreamConnectionStatus =
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'
  | 'error';

export interface UseDashboardEventsOptions {
  readonly endpoint?: string;
  readonly enabled?: boolean;
  readonly onEvent?: (event: DashboardEvent) => void;
  readonly maxReconnectAttempts?: number;
  readonly heartbeatTimeoutMs?: number;
}

export function useDashboardEvents({
  endpoint = '/api/v1/events',
  enabled = true,
  onEvent,
  maxReconnectAttempts = 8,
  heartbeatTimeoutMs = 25000,
}: UseDashboardEventsOptions = {}) {
  const [status, setStatus] = useState<StreamConnectionStatus>('disconnected');
  const [events, setEvents] = useState<ReadonlyArray<DashboardEvent>>([]);
  const [lastEventAt, setLastEventAt] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const watchdogTimerRef = useRef<NodeJS.Timeout | null>(null);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (watchdogTimerRef.current) {
      clearTimeout(watchdogTimerRef.current);
      watchdogTimerRef.current = null;
    }
  }, []);

  const scheduleReconnect = useCallback((reconnectFn: () => void) => {
    if (reconnectAttemptsRef.current < maxReconnectAttempts) {
      setStatus('reconnecting');
      reconnectAttemptsRef.current += 1;
      const baseDelay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 20000);
      const jitter = Math.floor(Math.random() * 1000);
      reconnectTimerRef.current = setTimeout(reconnectFn, baseDelay + jitter);
    } else {
      setStatus('disconnected');
    }
  }, [maxReconnectAttempts]);

  const resetHeartbeatWatchdog = useCallback((reconnectFn: () => void) => {
    if (watchdogTimerRef.current) clearTimeout(watchdogTimerRef.current);
    watchdogTimerRef.current = setTimeout(() => {
      console.warn('[useDashboardEvents] 25s SSE heartbeat watchdog expired. Re-establishing link...');
      cleanup();
      scheduleReconnect(reconnectFn);
    }, heartbeatTimeoutMs);
  }, [cleanup, scheduleReconnect, heartbeatTimeoutMs]);

  const handleIncomingMessage = useCallback(
    (event: MessageEvent, reconnectFn: () => void) => {
      resetHeartbeatWatchdog(reconnectFn);
      if (!event.data || event.data.startsWith(':')) return;
      try {
        const parsed = JSON.parse(event.data) as DashboardEvent;
        const normalized: DashboardEvent = {
          id: parsed.id || `evt_${Date.now()}_${Math.random().toString(16).slice(2, 6)}`,
          type: parsed.type || 'log',
          message: parsed.message || (typeof parsed === 'string' ? parsed : JSON.stringify(parsed)),
          timestamp: parsed.timestamp || new Date().toISOString(),
          data: parsed.data,
        };
        setEvents((prev) => [normalized, ...prev.slice(0, 99)]);
        setLastEventAt(normalized.timestamp);
        onEvent?.(normalized);
      } catch (err) {
        console.warn('[useDashboardEvents] Failed to parse SSE event data:', err);
      }
    },
    [onEvent, resetHeartbeatWatchdog]
  );

  const connect = useCallback(() => {
    if (!enabled || typeof window === 'undefined') return;
    cleanup();
    setStatus('connecting');

    try {
      const es = new EventSource(endpoint);
      eventSourceRef.current = es;

      es.onopen = () => {
        setStatus('connected');
        reconnectAttemptsRef.current = 0;
        resetHeartbeatWatchdog(connect);
      };

      es.onmessage = (evt) => handleIncomingMessage(evt, connect);

      es.onerror = () => {
        cleanup();
        scheduleReconnect(connect);
      };
    } catch {
      setStatus('error');
    }
  }, [enabled, endpoint, cleanup, scheduleReconnect, resetHeartbeatWatchdog, handleIncomingMessage]);

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return;
    const handleOnline = () => {
      reconnectAttemptsRef.current = 0;
      connect();
    };

    window.addEventListener('online', handleOnline);
    return () => {
      window.removeEventListener('online', handleOnline);
    };
  }, [enabled, connect]);

  useEffect(() => {
    if (enabled) connect();
    else {
      cleanup();
      setStatus('disconnected');
    }
    return cleanup;
  }, [enabled, connect, cleanup]);

  return {
    status,
    events,
    lastEventAt,
    isConnected: status === 'connected',
    clearEvents: useCallback(() => setEvents([]), []),
    reconnect: connect,
  };
}

export default useDashboardEvents;
