import axios from 'axios';
import { useAuthStore } from '@/store/authStore';
import { User, UserRole } from '@/types/user';
import { Scan } from '@/types/compliance';
import { Product } from '@/types/product';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 90000,
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const apiErrorMessage = (error: unknown, fallback = 'Something went wrong'): string => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
  }
  return fallback;
};

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) => api.post('/auth/login', { email, password }),
  me: () => api.get<User>('/auth/me'),
  register: (data: {
    email: string;
    full_name: string;
    password: string;
    role: UserRole;
    department?: string;
    employee_id?: string;
  }) => api.post<User>('/auth/register', data),
  listUsers: (params?: { skip?: number; limit?: number; role?: UserRole }) =>
    api.get<User[]>('/auth/users', { params }),
  userStats: () => api.get<{ total: number; active: number }>('/auth/users/count'),
  updateUser: (id: number, data: Partial<User> & { password?: string }) =>
    api.patch<User>(`/auth/users/${id}`, data),
  deleteUser: (id: number) => api.delete(`/auth/users/${id}`),
};

// ─── Scan ─────────────────────────────────────────────────────────────────────
export const scanApi = {
  upload: (formData: FormData) =>
    api.post<Scan>('/scan/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getResult: (scanId: string) => api.get<Scan>(`/scan/${scanId}`),
  listScans: (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    q?: string;
  }) => api.get<{ total: number; items: Scan[] }>('/scan/', { params }),
  reprocess: (scanId: string) => api.post<Scan>(`/scan/${scanId}/reprocess`),
  delete: (scanId: string) => api.delete(`/scan/${scanId}`),
  rules: () => api.get('/scan/rules'),
  engine: () => api.get<{ engine: string; model: string }>('/scan/engine'),
};

// ─── Products ─────────────────────────────────────────────────────────────────
export const productApi = {
  list: (params?: { skip?: number; limit?: number; q?: string; category?: string }) =>
    api.get<{ total: number; items: Product[] }>('/products/', { params }),
  categories: () => api.get<{ categories: { category: string; count: number }[] }>('/products/categories'),
  get: (id: number) => api.get<Product>(`/products/${id}`),
  update: (id: number, data: Partial<Product>) => api.patch<Product>(`/products/${id}`, data),
  delete: (id: number) => api.delete(`/products/${id}`),
};

// ─── Reports ──────────────────────────────────────────────────────────────────
export interface ReportSummary {
  id: number;
  report_id: string;
  scan_id: number;
  officer_id: number;
  title: string;
  format: 'pdf' | 'json';
  file_url: string | null;
  file_size_bytes: number | null;
  created_at: string;
  scan_ref: string | null;
  compliance_status: string | null;
}

export interface ReportGenerateResult {
  report_id: string;
  download_url: string;
  title: string;
}

export const reportApi = {
  generate: (scanId: string, format?: 'pdf' | 'json') =>
    api.post<ReportGenerateResult>(`/reports/generate/${scanId}`, null, {
      params: { format: format ?? 'pdf' },
    }),
  download: (reportId: string) =>
    api.get<Blob>(`/reports/download/${reportId}`, { responseType: 'blob' }),
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<ReportSummary[]>('/reports/', { params }),
  get: (reportId: string) => api.get<ReportSummary>(`/reports/${reportId}`),
  delete: (reportId: string) => api.delete(`/reports/${reportId}`),
};

// ─── Dashboard ────────────────────────────────────────────────────────────────
export interface DashboardStats {
  total_scans: number;
  completed_scans: number;
  processing_scans: number;
  failed_scans: number;
  compliant: number;
  non_compliant: number;
  partial: number;
  average_compliance_score: number;
  total_violations: number;
  critical_violations: number;
  compliance_rate: number;
  recent_scans: {
    scan_id: string;
    status: string;
    scan_status: string;
    score: number | null;
    violations: number;
    location: string | null;
    created_at: string | null;
  }[];
}

export interface TrendPoint {
  date: string;
  scans: number;
  compliant: number;
  non_compliant: number;
  partial: number;
  average_score: number;
}

export interface ViolationBreakdown {
  scans_analysed: number;
  total_violations: number;
  by_severity: { critical: number; major: number; minor: number };
  top_rules: {
    rule_id: string;
    rule_title: string;
    severity: string;
    occurrences: number;
    recommendation?: string;
    first_seen_scan?: string;
  }[];
  recent_violations: {
    scan_id: string;
    rule_id: string;
    rule_title: string;
    severity: string;
    created_at: string | null;
  }[];
}

export const dashboardApi = {
  stats: () => api.get<DashboardStats>('/dashboard/stats'),
  trends: (days?: number) =>
    api.get<{ days: number; series: TrendPoint[] }>('/dashboard/trends', {
      params: { days: days ?? 14 },
    }),
  violations: (limit?: number) =>
    api.get<ViolationBreakdown>('/dashboard/violations', { params: { limit: limit ?? 20 } }),
};