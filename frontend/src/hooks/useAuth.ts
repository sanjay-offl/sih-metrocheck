'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/lib/api';

export function useAuth() {
  const { user, token, isAuthenticated, setAuth, setUser, logout } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const router = useRouter();

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      try {
        const res = await authApi.login(email, password);
        setAuth(res.data.user, res.data.access_token);
        router.push('/dashboard');
        return { ok: true as const };
      } catch (error: unknown) {
        const detail =
          (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        return { ok: false as const, error: detail ?? 'Login failed. Please try again.' };
      } finally {
        setIsLoading(false);
      }
    },
    [router, setAuth]
  );

  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      const res = await authApi.me();
      setUser(res.data);
    } catch {
      /* interceptor handles 401 */
    }
  }, [token, setUser]);

  useEffect(() => {
    let mounted = true;
    async function check() {
      if (!token) {
        if (mounted) setChecking(false);
        return;
      }
      try {
        const res = await authApi.me();
        if (mounted) {
          setUser(res.data);
          setChecking(false);
        }
      } catch {
        if (mounted) {
          logout();
          setChecking(false);
        }
      }
    }
    void check();
    return () => {
      mounted = false;
    };
  }, [token, setUser, logout]);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  return { user, isAuthenticated, isLoading, checking, login, logout, refreshUser };
}