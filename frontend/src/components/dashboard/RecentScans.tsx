'use client';

import { useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { DashboardStats } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';

interface RecentScansProps {
  scans: DashboardStats['recent_scans'];
}

const STATUS_BADGE: Record<string, { label: string; variant: 'success' | 'destructive' | 'warning' | 'secondary' }> = {
  compliant: { label: 'Compliant', variant: 'success' },
  non_compliant: { label: 'Non-Compliant', variant: 'destructive' },
  partial: { label: 'Partial', variant: 'warning' },
  pending: { label: 'Pending', variant: 'secondary' },
};

export function RecentScans({ scans }: RecentScansProps) {
  const router = useRouter();

  if (!scans || scans.length === 0) {
    return (
      <p className="text-sm text-slate-500 py-6 text-center">
        No inspections yet. Run your first compliance scan to see results here.
      </p>
    );
  }

  return (
    <div className="divide-y divide-slate-100">
      {scans.map((scan) => {
        const status = STATUS_BADGE[scan.status] ?? STATUS_BADGE.pending;
        return (
          <button
            key={scan.scan_id}
            onClick={() => router.push(`/scan?scanId=${scan.scan_id}`)}
            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50 transition-colors"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">
                {scan.scan_id.slice(0, 8).toUpperCase()}
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                {formatDate(scan.created_at)}
                {scan.location ? ` - ${scan.location}` : ''}
              </p>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              {scan.score !== null && scan.score !== undefined && (
                <span className="text-sm font-semibold text-slate-700">
                  {scan.score.toFixed(1)}%
                </span>
              )}
              <Badge variant={status.variant}>{status.label}</Badge>
              <ArrowRight className="w-4 h-4 text-slate-300" />
            </div>
          </button>
        );
      })}
    </div>
  );
}