'use client';

import { useState } from 'react';
import { Search, Filter } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface ReportFilterProps {
  onSearch: (q: string) => void;
  onStatusFilter: (status: string) => void;
}

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'compliant', label: 'Compliant' },
  { value: 'non_compliant', label: 'Non-compliant' },
  { value: 'partial', label: 'Partially compliant' },
  { value: 'pending', label: 'Pending' },
];

export function ReportFilter({ onSearch, onStatusFilter }: ReportFilterProps) {
  const [status, setStatus] = useState('all');

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder="Search by report or scan ID..."
          onChange={(e) => onSearch(e.target.value)}
          className="pl-9"
        />
      </div>
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-slate-400" />
        <Select
          value={status}
          onValueChange={(value) => {
            setStatus(value);
            onStatusFilter(value);
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}