'use client';

import { useCallback, useEffect, useState } from 'react';
import { reportApi, ReportSummary } from '@/lib/api';

export function useReports() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await reportApi.list();
      setReports(res.data);
      setError(null);
    } catch {
      setError('Could not load reports');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const downloadReport = useCallback(async (reportId: string) => {
    try {
      const res = await reportApi.download(reportId);
      const url = URL.createObjectURL(res.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      const disposition = res.headers['content-disposition'] ?? '';
      const match = disposition.match(/filename="?(.+)"?$/);
      a.download = match?.[1] ?? `MetroCheck_Report_${reportId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      return true;
    } catch {
      return false;
    }
  }, []);

  const generate = useCallback(async (scanId: string) => {
    const res = await reportApi.generate(scanId);
    return res.data;
  }, []);

  const remove = useCallback(
    async (reportId: string) => {
      await reportApi.delete(reportId);
      await load();
    },
    [load]
  );

  return { reports, isLoading, error, load, downloadReport, generate, remove };
}