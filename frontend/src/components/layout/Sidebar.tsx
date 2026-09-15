'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  ScanLine,
  Package,
  AlertTriangle,
  FileText,
  Users,
  LogOut,
  Scale,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';
import { RoleBadge } from './RoleBadge';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, adminOnly: false },
  { href: '/scan', label: 'New Scan', icon: ScanLine, adminOnly: false },
  { href: '/products', label: 'Products', icon: Package, adminOnly: false },
  { href: '/violations', label: 'Violations', icon: AlertTriangle, adminOnly: false },
  { href: '/reports', label: 'Reports', icon: FileText, adminOnly: false },
  { href: '/users', label: 'Users', icon: Users, adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.adminOnly || user?.role === 'admin'
  );

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-govt-navy text-white">
      <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
          <Scale className="h-5 w-5" />
        </div>
        <div>
          <p className="text-lg font-bold leading-none">MetroCheck</p>
          <p className="text-[10px] text-blue-200 mt-1">Legal Metrology Compliance</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {visibleItems.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                active
                  ? 'bg-white/15 text-white'
                  : 'text-blue-200 hover:bg-white/5 hover:text-white'
              )}
            >
              <item.icon className="h-4 w-4 flex-shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-white/10 px-4 py-4 space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-white/15 text-sm font-bold">
            {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{user?.full_name ?? 'User'}</p>
            <RoleBadge role={user?.role ?? 'viewer'} />
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-blue-200 hover:bg-white/10 hover:text-white transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}