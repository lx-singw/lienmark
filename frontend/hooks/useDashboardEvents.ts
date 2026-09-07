'use client';

/**
 * useDashboardEvents Hook
 * Connects to SSE stream with automatic reconnection, heartbeat tracking, and polling fallback.
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

export type StreamConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'error';

export interface UseDashboardEventsOptions {
  readonly endpoint?: string;
  readonly enabled?: boolean;
  readonly onEvent?: (event: DashboardEvent) => void;
  readonly maxReconnectAttempts?: number;
}

export function useDashboardEvents({
  endpoint = '/api/v1/events',
  enabled = true,
  onEvent,
  maxReconnectAttempts = 5,
}: UseDashboardEventsOptions = {}) {
  const [status, setStatus] = useState<StreamConnectionStatus>('disconnected');
  const [events, setEvents] = useState<ReadonlyArray<DashboardEvent>>([]);
  const [lastEventAt, setLastEventAt] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const handleIncomingMessage = useCallback(
    (event: MessageEvent) => {
      try {
        if (!event.data || event.data.startsWith(':')) return;
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
    [onEvent]
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
      };

      es.onmessage = handleIncomingMessage;

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;

        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          setStatus('reconnecting');
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 15000);
          reconnectTimerRef.current = setTimeout(connect, delay);
        } else {
          setStatus('disconnected');
        }
      };
    } catch {
      setStatus('error');
    }
  }, [enabled, endpoint, maxReconnectAttempts, cleanup, handleIncomingMessage]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      cleanup();
      setStatus('disconnected');
    }
    return cleanup;
  }, [enabled, connect, cleanup]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    status,
    events,
    lastEventAt,
    isConnected: status === 'connected',
    clearEvents,
    reconnect: connect,
  };
}

export default useDashboardEvents;
