'use client';

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { TrendPoint } from '@/lib/api';

interface ComplianceTrendProps {
  data: TrendPoint[];
}

export function ComplianceTrend({ data }: ComplianceTrendProps) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
          <defs>
            <linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#003580" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#003580" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={(d: string) => {
              const [y, m, day] = d.split('-');
              return `${day}/${m}`;
            }}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: '#64748b' }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            formatter={(value) => [`${value}%`, 'Avg. Score']}
            labelFormatter={(d: string) => {
              const [y, m, day] = d.split('-');
              return `${day}/${m}/${y}`;
            }}
            contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 13 }}
          />
          <Area
            type="monotone"
            dataKey="average_score"
            stroke="#003580"
            strokeWidth={2.5}
            fill="url(#scoreFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}