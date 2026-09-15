import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—';
  return `${score.toFixed(1)}%`;
}

export function getImageUrl(path: string | null | undefined): string {
  if (!path) return '/placeholder-product.png';
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  if (path.startsWith('http')) return path;
  return `${base}${path}`;
}