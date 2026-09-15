'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Download, FileText, Loader2, Trash2 } from 'lucide-react';
import { reportApi, ReportSummary } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/components/ui/toast';
import { formatDate } from '@/lib/utils';
import { RequireAuth } from '@/components/layout/RequireAuth';

function ReportDetailContent() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useToast();
  const [report, setReport] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await reportApi.get(params.id);
      setReport(res.data);
    } catch {
      toast('error', 'Report not found');
      router.replace('/reports');
    } finally {
      setLoading(false);
    }
  }, [params.id, router, toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDownload = useCallback(async () => {
    if (!report) return;
    try {
      const res = await reportApi.download(report.report_id);
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `MetroCheck_Report_${report.report_id.slice(0, 8)}.${report.format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast('error', 'Download failed');
    }
  }, [report, toast]);

  const handleDelete = useCallback(async () => {
    if (!report) return;
    if (!window.confirm('Delete this report permanently?')) return;
    try {
      await reportApi.delete(report.report_id);
      toast('success', 'Report deleted');
      router.replace('/reports');
    } catch {
      toast('error', 'Delete failed');
    }
  }, [report, router, toast]);

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center gap-3 text-slate-500">
        <Loader2 className="h-6 w-6 animate-spin" /> Loading report...
      </div>
    );
  }

  if (!report) return null;

  const statusVariant =
    report.compliance_status === 'compliant'
      ? 'success'
      : report.compliance_status === 'non_compliant'
        ? 'destructive'
        : report.compliance_status === 'partial'
          ? 'warning'
          : 'secondary';

  const rows: [string, string][] = [
    ['Report ID', report.report_id],
    ['Title', report.title],
    ['Format', report.format.toUpperCase()],
    ['Generated', formatDate(report.created_at)],
    [
      'File Size',
      report.file_size_bytes !== null && report.file_size_bytes !== undefined
        ? `${(report.file_size_bytes / 1024).toFixed(1)} KB`
        : '—',
    ],
    ['Compliance Status', (report.compliance_status ?? 'pending').replace('_', ' ')],
  ];

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-govt-navy/10 p-3">
              <FileText className="h-6 w-6 text-govt-navy" />
            </div>
            <div>
              <CardTitle className="text-base">{report.title}</CardTitle>
              <p className="text-xs text-slate-400 mt-1">
                Scan: {report.scan_ref ? report.scan_ref.slice(0, 8).toUpperCase() : '—'}
              </p>
            </div>
          </div>
          <Badge variant={statusVariant}>
            {(report.compliance_status ?? 'pending').replace('_', ' ')}
          </Badge>
        </CardHeader>
        <CardContent>
          <dl className="divide-y divide-slate-100">
            {rows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 py-2.5">
                <dt className="text-sm text-slate-500">{label}</dt>
                <dd className="text-sm font-medium text-slate-800 text-right">{value}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-6 flex items-center gap-2">
            <Button onClick={handleDownload} className="flex-1">
              <Download className="h-4 w-4" /> Download {report.format.toUpperCase()}
            </Button>
            <Button variant="outline" onClick={() => router.push('/reports')}>
              All reports
            </Button>
            <Button variant="ghost" onClick={handleDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ReportDetailPage() {
  return (
    <RequireAuth>
      <Suspense fallback={null}>
        <ReportDetailContent />
      </Suspense>
    </RequireAuth>
  );
}