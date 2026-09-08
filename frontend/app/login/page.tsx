"use client";
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const res = await fetch("/api/auth/redeem-invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      if (!res.ok) {
        throw new Error("Invalid token");
      }
      router.push("/");
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    }
  };

  return (
    <main className="p-8">
      <h1>Login</h1>
      <p className="text-sm text-gray-500 mb-4">Demo Account Authentication · Fictional Production Workspace</p>
      <form onSubmit={handleLogin} className="flex flex-col gap-4 max-w-sm">
        <label>
          Access Token:
          <input 
            type="text" 
            value={token} 
            onChange={(e) => setToken(e.target.value)} 
            className="border p-2 w-full text-black"
            required
          />
        </label>
        <button type="submit" className="bg-blue-600 text-white p-2">Login</button>
        {error && <p className="text-red-500">{error}</p>}
      </form>
    </main>
  );
}
