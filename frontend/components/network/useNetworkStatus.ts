'use client';

/**
 * useNetworkStatus Hook
 * Monitors window online/offline events with transition tracking and clean cleanup.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { NetworkState, NetworkTransition } from './types';

export function useNetworkStatus(): NetworkState & {
  readonly checkConnectivity: () => Promise<boolean>;
} {
  const [isOnline, setIsOnline] = useState<boolean>(() => {
    return typeof navigator !== 'undefined' ? navigator.onLine : true;
  });
  const [transition, setTransition] = useState<NetworkTransition>('connected');
  const [lastChangedAt, setLastChangedAt] = useState<string | null>(null);
  const [offlineSeconds, setOfflineSeconds] = useState<number>(0);

  const restoredTimerRef = useRef<NodeJS.Timeout | null>(null);
  const offlineTimerRef = useRef<NodeJS.Timeout | null>(null);
  const offlineStartRef = useRef<number | null>(null);

  const clearTimers = useCallback(() => {
    if (restoredTimerRef.current) clearTimeout(restoredTimerRef.current);
    if (offlineTimerRef.current) clearInterval(offlineTimerRef.current);
    restoredTimerRef.current = null;
    offlineTimerRef.current = null;
  }, []);

  const handleOnline = useCallback(() => {
    clearTimers();
    setIsOnline(true);
    setTransition('restored');
    setLastChangedAt(new Date().toISOString());
    offlineStartRef.current = null;
    setOfflineSeconds(0);

    restoredTimerRef.current = setTimeout(() => {
      setTransition('connected');
    }, 4500);
  }, [clearTimers]);

  const handleOffline = useCallback(() => {
    clearTimers();
    setIsOnline(false);
    setTransition('disconnected');
    setLastChangedAt(new Date().toISOString());
    offlineStartRef.current = Date.now();

    offlineTimerRef.current = setInterval(() => {
      if (offlineStartRef.current) {
        const diff = Math.floor((Date.now() - offlineStartRef.current) / 1000);
        setOfflineSeconds(diff);
      }
    }, 1000);
  }, [clearTimers]);

  const checkConnectivity = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch('/api/v1/health', {
        method: 'HEAD',
        cache: 'no-store',
      });
      if (res.ok) {
        handleOnline();
        return true;
      }
      handleOffline();
      return false;
    } catch {
      handleOffline();
      return false;
    }
  }, [handleOnline, handleOffline]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearTimers();
    };
  }, [handleOnline, handleOffline, clearTimers]);

  return {
    isOnline,
    status: isOnline ? 'online' : 'offline',
    transition,
    lastChangedAt,
    offlineDurationSeconds: offlineSeconds,
    checkConnectivity,
  };
}

export default useNetworkStatus;
