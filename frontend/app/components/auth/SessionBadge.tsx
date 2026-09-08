"use client";

import React, { useEffect, useState } from 'react';
import RequestAccessModal from './RequestAccessModal';

export interface UserIdentity {
  display_name?: string;
  name?: string;
  email?: string;
  role?: string;
  production?: string;
  production_name?: string;
  production_id?: string;
  tenant_id?: string;
}

export interface SessionBadgeProps {
  onSignOut?: () => void;
  onRequestAccess?: () => void;
}

function getProductionName(user: UserIdentity): string {
  if (user.production) return user.production;
  if (user.production_name) return user.production_name;
  if (user.production_id) {
    if (user.production_id.toLowerCase().includes('shadows')) {
      return 'Shadows Over Broadway';
    }
    return user.production_id;
  }
  return 'Shadows Over Broadway';
}

function getRole(user: UserIdentity): string {
  return user.role || 'Reviewer';
}

function getUserName(user: UserIdentity): string {
  return user.display_name || user.name || user.email || 'Evaluator';
}

interface AuthenticatedBadgeProps {
  user: UserIdentity;
  onSignOut: () => void;
}

function AuthenticatedBadge({ user, onSignOut }: AuthenticatedBadgeProps) {
  const prodName = getProductionName(user);
  const role = getRole(user);
  const name = getUserName(user);

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-700/80 bg-slate-800/80 px-3.5 py-1 text-xs text-slate-300 shadow-sm backdrop-blur-sm">
      <span className="font-semibold text-slate-100">{prodName}</span>
      <span className="text-slate-500 select-none">·</span>
      <span className="text-slate-300">{role}</span>
      <span className="text-slate-500 select-none">·</span>
      <span className="text-slate-300">{name}</span>
      <span className="text-slate-500 select-none">·</span>
      <button
        type="button"
        onClick={onSignOut}
        className="rounded font-medium text-rose-400 hover:text-rose-300 hover:underline transition-colors focus:outline-none"
      >
        Sign Out
      </button>
    </div>
  );
}

interface UnauthenticatedBadgeProps {
  onRequestAccess: () => void;
}

function UnauthenticatedBadge({ onRequestAccess }: UnauthenticatedBadgeProps) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-700/80 bg-slate-800/60 px-3.5 py-1 text-xs text-slate-300 shadow-sm backdrop-blur-sm">
      <span className="font-medium text-slate-300">Sample workspace</span>
      <span className="text-slate-500 select-none">·</span>
      <span className="text-slate-400">Read-only</span>
      <span className="text-slate-500 select-none">·</span>
      <button
        type="button"
        onClick={onRequestAccess}
        className="rounded font-semibold text-blue-400 hover:text-blue-300 hover:underline transition-colors focus:outline-none"
      >
        Request Access
      </button>
    </div>
  );
}

export default function SessionBadge({
  onSignOut,
  onRequestAccess,
}: SessionBadgeProps) {
  const [user, setUser] = useState<UserIdentity | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    fetch('/api/auth/session')
      .then((res) => (res.ok ? res.json() : null))
      .then((data: unknown) => {
        if (!isMounted || !data || typeof data !== 'object') return;
        const payload = data as Record<string, unknown>;
        const userObj = (payload.user || payload) as UserIdentity;
        if (userObj.display_name || userObj.email || userObj.role) {
          setUser(userObj);
        }
      })
      .catch(() => {
        if (isMounted) setUser(null);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSignOut = async () => {
    try {
      await fetch('/api/auth/signout', { method: 'POST' });
    } catch {
      // Ignore network error on signout
    }
    setUser(null);
    if (onSignOut) {
      onSignOut();
    }
  };

  const handleRequestAccess = () => {
    if (onRequestAccess) {
      onRequestAccess();
    } else {
      setIsModalOpen(true);
    }
  };

  return (
    <>
      {user ? (
        <AuthenticatedBadge user={user} onSignOut={handleSignOut} />
      ) : (
        <UnauthenticatedBadge onRequestAccess={handleRequestAccess} />
      )}
      <RequestAccessModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  );
}
