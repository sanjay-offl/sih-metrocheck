'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Download, FileText, Trash2, Eye } from 'lucide-react';
import { ReportSummary } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';

interface ReportCardProps {
  report: ReportSummary;
  onDownload: (id: string) => Promise<boolean>;
  onDelete: (id: string) => Promise<void>;
}

export function ReportCard({ report, onDownload, onDelete }: ReportCardProps) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  const handleDownload = async () => {
    setBusy(true);
    await onDownload(report.report_id);
    setBusy(false);
  };

  const statusVariant =
    report.compliance_status === 'compliant'
      ? 'success'
      : report.compliance_status === 'non_compliant'
        ? 'destructive'
        : report.compliance_status === 'partial'
          ? 'warning'
          : 'secondary';

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-govt-navy/10 p-2.5">
            <FileText className="h-5 w-5 text-govt-navy" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-800 truncate">{report.title}</p>
            <p className="text-xs text-slate-400 mt-0.5">
              {report.scan_ref ? `Scan ${report.scan_ref.slice(0, 8).toUpperCase()}` : `#${report.report_id.slice(0, 8).toUpperCase()}`}
              {' - '}
              {formatDate(report.created_at)}
            </p>
          </div>
        </div>
        <Badge variant={statusVariant}>
          {(report.compliance_status ?? 'pending').replace('_', ' ')}
        </Badge>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px]">
            {report.format.toUpperCase()}
          </Badge>
          {report.file_size_bytes !== null && report.file_size_bytes !== undefined && (
            <span className="text-xs text-slate-400">
              {(report.file_size_bytes / 1024).toFixed(1)} KB
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {report.scan_ref && (
            <button
              onClick={() => router.push(`/scan?scanId=${report.scan_ref}`)}
              title="View scan"
              className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <Eye className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={handleDownload}
            disabled={busy}
            title="Download"
            className="rounded-md p-2 text-blue-600 hover:bg-blue-50 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            onClick={() => onDelete(report.report_id)}
            title="Delete"
            className="rounded-md p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}