'use client';

import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Download,
  RotateCcw,
} from 'lucide-react';
import { reportApi } from '@/lib/api';
import { Scan } from '@/types/compliance';
import { useToast } from '@/components/ui/toast';
import { ComplianceCard } from './ComplianceCard';
import { ViolationList } from './ViolationList';

interface ScanResultProps {
  scan: Scan;
  onReprocess?: () => void;
}

export function ScanResult({ scan, onReprocess }: ScanResultProps) {
  const [downloading, setDownloading] = useState(false);
  const { toast } = useToast();
  const status = scan.compliance_status || 'pending';
  const result = scan.compliance_result;

  const statusConfig = {
    compliant: {
      label: 'COMPLIANT',
      icon: CheckCircle,
      color: 'text-green-600',
      bg: 'bg-green-50',
      border: 'border-green-200',
    },
    non_compliant: {
      label: 'NON-COMPLIANT',
      icon: XCircle,
      color: 'text-red-600',
      bg: 'bg-red-50',
      border: 'border-red-200',
    },
    partial: {
      label: 'PARTIALLY COMPLIANT',
      icon: AlertTriangle,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
    },
    pending: {
      label: 'PENDING',
      icon: AlertTriangle,
      color: 'text-slate-600',
      bg: 'bg-slate-50',
      border: 'border-slate-200',
    },
  } as const;

  const config = statusConfig[status as keyof typeof statusConfig] ?? statusConfig.pending;
  const StatusIcon = config.icon;

  const handleDownload = async () => {
    if (downloading) return;
    setDownloading(true);
    try {
      const genRes = await reportApi.generate(scan.scan_id);
      const id = genRes.data.report_id;
      const blobRes = await reportApi.download(id);
      const url = URL.createObjectURL(blobRes.data as Blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `MetroCheck_${scan.scan_id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast('success', 'Report downloaded', 'The PDF compliance report has been generated.');
    } catch {
      toast('error', 'Download failed', 'Could not generate the PDF report.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className={`rounded-xl border p-6 ${config.bg} ${config.border}`}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <StatusIcon className={`w-8 h-8 ${config.color}`} />
            <div>
              <p className={`font-bold text-xl ${config.color}`}>{config.label}</p>
              <p className="text-slate-600 text-sm">
                Compliance Score:{' '}
                {scan.compliance_score !== null && scan.compliance_score !== undefined
                  ? `${scan.compliance_score.toFixed(1)}%`
                  : '—'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onReprocess && (
              <button
                onClick={onReprocess}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-slate-300 text-slate-600 hover:bg-white"
              >
                <RotateCcw className="w-4 h-4" />
                Re-scan
              </button>
            )}
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
            >
              <Download className="w-4 h-4" />
              {downloading ? 'Generating...' : 'Download PDF Report'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
          {[
            { label: 'Total Checks', value: result?.total_checks ?? scan.total_violations ?? 0 },
            { label: 'Passed', value: result?.passed_checks ?? 0, color: 'text-green-600' },
            { label: 'Violations', value: scan.total_violations ?? 0, color: 'text-red-600' },
            { label: 'Critical', value: scan.critical_violations ?? 0, color: 'text-red-700' },
          ].map((stat) => (
            <div
              key={stat.label}
              className="text-center bg-white rounded-lg p-3 border border-white shadow-sm"
            >
              <p className={`text-2xl font-bold ${stat.color ?? 'text-slate-800'}`}>{stat.value}</p>
              <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>

      {result?.summary && (
        <p className="text-slate-600 text-sm leading-relaxed bg-white rounded-xl p-4 border border-slate-200">
          {result.summary}
        </p>
      )}

      {scan.extracted_data && <ComplianceCard extracted={scan.extracted_data} />}

      {result && <ViolationList result={result} />}
    </div>
  );
}