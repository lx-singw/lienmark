"use client";
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface UserIdentity {
  display_name: string;
  role: string;
  production: string;
}

export default function SessionBadge() {
  const [user, setUser] = useState<UserIdentity | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetch('/api/auth/session')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && data.user) {
          setUser(data.user as UserIdentity);
        }
      })
      .catch(() => setUser(null));
  }, []);

  const handleSignOut = async () => {
    await fetch('/api/auth/signout', { method: 'POST' });
    setUser(null);
    router.push('/login');
  };

  if (!user) return <div className="text-sm">Not logged in</div>;

  return (
    <div className="border p-4 rounded shadow-sm flex items-center justify-between bg-white text-black">
      <div className="mr-4">
        <div className="font-bold">{user.display_name}</div>
        <div className="text-sm text-gray-600">Role: {user.role} | Prod: {user.production}</div>
      </div>
      <button onClick={handleSignOut} className="bg-red-500 text-white px-3 py-1 rounded">
        Sign Out
      </button>
    </div>
  );
}
