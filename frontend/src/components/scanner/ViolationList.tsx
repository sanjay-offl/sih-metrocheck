'use client';

import { CheckCircle, AlertTriangle } from 'lucide-react';
import { ComplianceResult, Severity } from '@/types/compliance';
import { cn } from '@/lib/utils';

interface ViolationListProps {
  result: ComplianceResult;
}

const SEVERITY_STYLES: Record<Severity, { badge: string; card: string }> = {
  critical: {
    badge: 'bg-red-100 text-red-700 border-red-200',
    card: 'bg-red-50/50 border-red-200',
  },
  major: {
    badge: 'bg-amber-100 text-amber-700 border-amber-200',
    card: 'bg-amber-50/50 border-amber-200',
  },
  minor: {
    badge: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    card: 'bg-emerald-50/50 border-emerald-200',
  },
};

export function ViolationList({ result }: ViolationListProps) {
  const violations = result.violations ?? [];
  const passed = result.passed_checks_list ?? [];

  return (
    <div className="space-y-6">
      {violations.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <h3 className="font-semibold text-slate-800">
              Violations Detected ({violations.length})
            </h3>
          </div>
          <div className="space-y-3">
            {violations.map((v, i) => {
              const style = SEVERITY_STYLES[v.severity] ?? SEVERITY_STYLES.minor;
              return (
                <div
                  key={i}
                  className={cn('rounded-lg border p-4', style.card)}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div>
                      <p className="font-semibold text-sm text-slate-800">{v.rule_title}</p>
                      <p className="text-xs text-slate-500">{v.rule_id}</p>
                    </div>
                    <span className={cn('text-xs font-bold px-2 py-0.5 rounded border flex-shrink-0', style.badge)}>
                      {v.severity.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mb-2">{v.description}</p>
                  <div className="space-y-0.5 text-xs">
                    {v.detected_value && (
                      <p className="text-slate-600">
                        <span className="font-medium text-slate-700">Found:</span>{' '}
                        {v.detected_value}
                      </p>
                    )}
                    {v.required_value && (
                      <p className="text-slate-600">
                        <span className="font-medium text-slate-700">Required:</span>{' '}
                        {v.required_value}
                      </p>
                    )}
                    {v.recommendation && (
                      <p className="text-slate-500 italic mt-1">
                        <span className="font-medium text-slate-600 not-italic">Fix:</span>{' '}
                        {v.recommendation}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {passed.length > 0 && (
        <div>
          <h3 className="font-semibold text-slate-800 mb-3">Checks Passed</h3>
          <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-1.5">
            {passed.map((check, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-green-700">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>{check}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {violations.length === 0 && passed.length === 0 && (
        <p className="text-sm text-slate-500">No compliance data available.</p>
      )}
    </div>
  );
}