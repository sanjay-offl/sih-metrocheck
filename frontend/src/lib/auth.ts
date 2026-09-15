import { useAuthStore } from '@/store/authStore';

export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}

export function isAuthenticated(): boolean {
  return useAuthStore.getState().isAuthenticated;
}

export function isAdmin(): boolean {
  return useAuthStore.getState().user?.role === 'admin';
}

export function isOfficer(): boolean {
  const r = useAuthStore.getState().user?.role;
  return r === 'officer' || r === 'admin';
}