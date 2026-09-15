'use client';

import { UserRole } from '@/types/user';
import { Badge } from '@/components/ui/badge';

const ROLE_CONFIG: Record<UserRole, { label: string; variant: 'navy' | 'blue' | 'secondary' }> = {
  admin: { label: 'Administrator', variant: 'navy' },
  officer: { label: 'Enforcement Officer', variant: 'blue' },
  viewer: { label: 'Viewer', variant: 'secondary' },
};

export function RoleBadge({ role }: { role: UserRole }) {
  const config = ROLE_CONFIG[role] ?? ROLE_CONFIG.viewer;
  return (
    <Badge variant={config.variant} className="mt-1 px-2 py-0 text-[10px]">
      {config.label}
    </Badge>
  );
}