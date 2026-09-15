'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ShieldAlert,
  Gauge,
  ScanLine,
  Loader2,
} from 'lucide-react';
import { dashboardApi, DashboardStats, TrendPoint, ViolationBreakdown } from '@/lib/api';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { ViolationChart } from '@/components/dashboard/ViolationChart';
import { ComplianceTrend } from '@/components/dashboard/ComplianceTrend';
import { RecentScans } from '@/components/dashboard/RecentScans';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RequireAuth } from '@/components/layout/RequireAuth';

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [breakdown, setBreakdown] = useState<ViolationBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, trendRes, breakRes] = await Promise.all([
        dashboardApi.stats(),
        dashboardApi.trends(14),
        dashboardApi.violations(6),
      ]);
      setStats(statsRes.data);
      setTrend(trendRes.data.series);
      setBreakdown(breakRes.data);
    } catch {
      setError('Could not load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !stats) {
    return (
      <RequireAuth>
        <div className="flex h-64 items-center justify-center gap-3 text-slate-500">
          <Loader2 className="h-6 w-6 animate-spin" />
          Loading dashboard...
        </div>
      </RequireAuth>
    );
  }

  const pieData = [
    {
      name: 'Compliant',
      value: stats?.compliant ?? 0,
      color: '#059669',
    },
    {
      name: 'Non-Compliant',
      value: stats?.non_compliant ?? 0,
      color: '#DC2626',
    },
    {
      name: 'Partial',
      value: stats?.partial ?? 0,
      color: '#D97706',
    },
  ].filter((d) => d.value > 0);

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Compliance Dashboard</h1>
            <p className="mt-1 text-sm text-slate-500">
              Overview of packaged commodity inspections under the Legal Metrology Rules, 2011
            </p>
          </div>
          <Button onClick={() => router.push('/scan')}>
            <ScanLine className="h-4 w-4" />
            New Inspection
          </Button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
            <button onClick={() => void load()} className="ml-2 font-medium underline">
              Retry
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatsCard
            label="Total Scans"
            value={stats?.total_scans ?? 0}
            sub={`${stats?.compliance_rate ?? 0}% compliance rate`}
            icon={Activity}
            accent="navy"
          />
          <StatsCard
            label="Compliant"
            value={stats?.compliant ?? 0}
            icon={CheckCircle2}
            accent="green"
          />
          <StatsCard
            label="Non-Compliant"
            value={stats?.non_compliant ?? 0}
            icon={XCircle}
            accent="red"
          />
          <StatsCard
            label="Partial"
            value={stats?.partial ?? 0}
            icon={AlertTriangle}
            accent="amber"
          />
          <StatsCard
            label="Critical Violations"
            value={stats?.critical_violations ?? 0}
            icon={ShieldAlert}
            accent="red"
          />
          <StatsCard
            label="Avg. Score"
            value={`${stats?.average_compliance_score ?? 0}%`}
            sub={`${stats?.total_violations ?? 0} total violations`}
            icon={Gauge}
            accent="blue"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Compliance Status Mix</CardTitle>
              <CardDescription>Distribution across all inspections</CardDescription>
            </CardHeader>
            <CardContent>
              {pieData.length === 0 ? (
                <p className="py-12 text-center text-sm text-slate-400">
                  No completed inspections yet
                </p>
              ) : (
                <ViolationChart data={pieData} />
              )}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Average Compliance Score</CardTitle>
              <CardDescription>Daily trend over the last 14 days</CardDescription>
            </CardHeader>
            <CardContent>
              {trend.length === 0 || trend.every((t) => t.average_score === 0) ? (
                <p className="py-12 text-center text-sm text-slate-400">
                  No score data available yet
                </p>
              ) : (
                <ComplianceTrend data={trend} />
              )}
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
              <div>
                <CardTitle>Recent Inspections</CardTitle>
                <CardDescription>Latest compliance scans</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/reports')}
              >
                View all
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <RecentScans scans={stats?.recent_scans ?? []} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Top Violations</CardTitle>
              <CardDescription>Most frequently breached rules</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {!breakdown || breakdown.top_rules.length === 0 ? (
                <p className="py-6 text-center text-sm text-slate-400">
                  No violations recorded
                </p>
              ) : (
                breakdown.top_rules.map((rule) => (
                  <div
                    key={`${rule.rule_id}-${rule.rule_title}`}
                    className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-xs font-medium text-slate-700">
                        {rule.rule_title}
                      </p>
                      <p className="text-[11px] text-slate-400">{rule.rule_id}</p>
                    </div>
                    <span
                      className={`flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-bold ${
                        rule.severity === 'critical'
                          ? 'bg-red-100 text-red-700'
                          : rule.severity === 'major'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      {rule.occurrences}
                    </span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </RequireAuth>
  );
}