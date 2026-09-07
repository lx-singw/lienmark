/**
 * Lienmark Network & Resilience Types (Sprint 7.2)
 * Models for offline detection, connection transitions, and connectivity banner.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

export type NetworkStatus = 'online' | 'offline' | 'reconnecting';

export type NetworkTransition = 'connected' | 'disconnected' | 'restored';

export interface NetworkState {
  readonly isOnline: boolean;
  readonly status: NetworkStatus;
  readonly transition: NetworkTransition;
  readonly lastChangedAt: string | null;
  readonly offlineDurationSeconds: number;
}

export interface OfflineConnectivityBannerProps {
  readonly onRetry?: () => void;
  readonly className?: string;
}
