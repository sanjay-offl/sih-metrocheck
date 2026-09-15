'use client';

import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  label: string;
  value: number | string;
  sub?: string;
  icon: LucideIcon;
  accent: 'navy' | 'green' | 'red' | 'amber' | 'blue' | 'slate';
}

const ACCENTS = {
  navy: {
    icon: 'bg-govt-navy/10 text-govt-navy',
    ring: 'border-govt-navy/10',
  },
  green: {
    icon: 'bg-green-50 text-green-600',
    ring: 'border-green-100',
  },
  red: {
    icon: 'bg-red-50 text-red-600',
    ring: 'border-red-100',
  },
  amber: {
    icon: 'bg-amber-50 text-amber-600',
    ring: 'border-amber-100',
  },
  blue: {
    icon: 'bg-blue-50 text-blue-600',
    ring: 'border-blue-100',
  },
  slate: {
    icon: 'bg-slate-100 text-slate-600',
    ring: 'border-slate-200',
  },
};

export function StatsCard({ label, value, sub, icon: Icon, accent }: StatsCardProps) {
  const a = ACCENTS[accent];
  return (
    <div className={cn('rounded-xl border bg-white p-5 shadow-sm', a.ring)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900">{value}</p>
          {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
        </div>
        <div className={cn('rounded-lg p-2.5', a.icon)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}