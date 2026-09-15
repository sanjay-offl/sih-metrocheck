'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Loader2, ShieldAlert } from 'lucide-react';
import { dashboardApi, ViolationBreakdown } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { formatDate } from '@/lib/utils';
import { RequireAuth } from '@/components/layout/RequireAuth';

export default function ViolationsPage() {
  const router = useRouter();
  const [data, setData] = useState<ViolationBreakdown | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await dashboardApi.violations(20);
      setData(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const sevBadge = (sev: string) =>
    sev === 'critical' ? 'destructive' : sev === 'major' ? 'warning' : 'success';

  if (loading) {
    return (
      <RequireAuth>
        <div className="flex h-48 items-center justify-center gap-3 text-slate-500">
          <Loader2 className="h-6 w-6 animate-spin" /> Loading violations...
        </div>
      </RequireAuth>
    );
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Violations</h1>
          <p className="mt-1 text-sm text-slate-500">
            Most frequently breached Legal Metrology rules across inspections
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <SummaryCard
            label="Scans Analysed"
            value={data?.scans_analysed ?? 0}
            accent="text-govt-navy"
          />
          <SummaryCard
            label="Total Violations"
            value={data?.total_violations ?? 0}
            accent="text-slate-700"
          />
          <SummaryCard
            label="Critical"
            value={data?.by_severity?.critical ?? 0}
            accent="text-red-600"
          />
          <SummaryCard
            label="Major / Minor"
            value={(data?.by_severity?.major ?? 0) + (data?.by_severity?.minor ?? 0)}
            accent="text-amber-600"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-red-600" />
                Most Breached Rules
              </CardTitle>
              <CardDescription>Ranked by occurrences</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {!data || data.top_rules.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-400">
                  No violations detected across any inspections.
                </p>
              ) : (
                data.top_rules.map((rule, idx) => (
                  <div
                    key={`${rule.rule_id}-${rule.rule_title}`}
                    className="flex items-start gap-3 rounded-lg border border-slate-100 bg-slate-50/60 p-3"
                  >
                    <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-govt-navy text-xs font-bold text-white">
                      {idx + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-800">{rule.rule_title}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{rule.rule_id}</p>
                      {rule.recommendation && (
                        <p className="mt-1 text-xs text-slate-500 italic line-clamp-2">
                          {rule.recommendation}
                        </p>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-lg font-bold text-slate-800">{rule.occurrences}</p>
                      <Badge variant={sevBadge(rule.severity)} className="text-[10px]">
                        {rule.severity}
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                Recent Violations
              </CardTitle>
              <CardDescription>Latest rule breaches, newest first</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {!data || data.recent_violations.length === 0 ? (
                <p className="px-6 pb-6 text-sm text-slate-400">No violations recorded.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Rule</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>Scan</TableHead>
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.recent_violations.map((v, i) => (
                      <TableRow
                        key={i}
                        className="cursor-pointer"
                        onClick={() => router.push(`/scan?scanId=${v.scan_id}`)}
                      >
                        <TableCell>
                          <p className="font-medium text-slate-800 text-sm">{v.rule_title}</p>
                          <p className="text-xs text-slate-400">{v.rule_id}</p>
                        </TableCell>
                        <TableCell>
                          <Badge variant={sevBadge(v.severity)} className="text-[10px]">
                            {v.severity}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {v.scan_id.slice(0, 8).toUpperCase()}
                        </TableCell>
                        <TableCell className="text-xs">{formatDate(v.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </RequireAuth>
  );
}

function SummaryCard({ label, value, accent }: { label: string; value: number; accent: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${accent}`}>{value}</p>
    </div>
  );
}