'use client';

import { useCallback, useEffect, useState } from 'react';
import { Loader2, UserPlus, Shield, Trash2 } from 'lucide-react';
import { authApi, apiErrorMessage } from '@/lib/api';
import { User, UserRole } from '@/types/user';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { formatDate } from '@/lib/utils';
import { RequireAuth } from '@/components/layout/RequireAuth';
import { useAuthStore } from '@/store/authStore';

const ROLE_VARIANT: Record<UserRole, 'navy' | 'blue' | 'secondary'> = {
  admin: 'navy',
  officer: 'blue',
  viewer: 'secondary',
};

export default function UsersPage() {
  const { toast } = useToast();
  const currentUserId = useAuthStore((s) => s.user?.id);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<{ total: number; active: number } | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'officer' as UserRole,
    department: '',
    employee_id: '',
  });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [usersRes, statsRes] = await Promise.all([authApi.listUsers(), authApi.userStats()]);
      setUsers(usersRes.data);
      setStats(statsRes.data);
    } catch {
      toast('error', 'Failed to load users', 'You may not have administrator access.');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await authApi.register(form);
      toast('success', 'User created', `${form.full_name} added successfully.`);
      setAddOpen(false);
      setForm({ full_name: '', email: '', password: '', role: 'officer', department: '', employee_id: '' });
      await load();
    } catch (error) {
      toast('error', 'Could not create user', apiErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (user: User) => {
    try {
      if (user.id === currentUserId) {
        toast('error', 'Cannot modify your own account');
        return;
      }
      await authApi.updateUser(user.id, { is_active: !user.is_active });
      toast('success', user.is_active ? 'User deactivated' : 'User activated');
      await load();
    } catch (error) {
      toast('error', 'Update failed', apiErrorMessage(error));
    }
  };

  const handleDelete = async (user: User) => {
    if (!window.confirm(`Delete ${user.full_name}? This cannot be undone.`)) return;
    try {
      await authApi.deleteUser(user.id);
      toast('success', 'User deleted');
      await load();
    } catch (error) {
      toast('error', 'Delete failed', apiErrorMessage(error));
    }
  };

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
            <p className="mt-1 text-sm text-slate-500">
              {stats?.active ?? 0} active of {stats?.total ?? 0} enrolled personnel
            </p>
          </div>
          <Button onClick={() => setAddOpen(true)}>
            <UserPlus className="h-4 w-4" /> Add User
          </Button>
        </div>

        {loading ? (
          <div className="flex h-48 items-center justify-center gap-3 text-slate-500">
            <Loader2 className="h-6 w-6 animate-spin" /> Loading users...
          </div>
        ) : (
          <Card className="overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Employee ID</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-govt-navy/10 text-xs font-bold text-govt-navy">
                          {user.full_name[0]?.toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-800">{user.full_name}</p>
                          {user.id === currentUserId && (
                            <p className="text-[10px] text-blue-600">You</p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{user.email}</TableCell>
                    <TableCell>
                      <Badge variant={ROLE_VARIANT[user.role]}>{user.role}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{user.department ?? '—'}</TableCell>
                    <TableCell className="text-sm">{user.employee_id ?? '—'}</TableCell>
                    <TableCell className="text-xs">{formatDate(user.created_at)}</TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? 'success' : 'outline'}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => void handleToggleActive(user)}
                          disabled={user.id === currentUserId}
                          title={user.is_active ? 'Deactivate' : 'Activate'}
                          className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-40"
                        >
                          <Shield className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => void handleDelete(user)}
                          disabled={user.id === currentUserId}
                          title="Delete"
                          className="rounded-md p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-40"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}

        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Add Enforcement User</DialogTitle>
              <DialogDescription>
                Create a MetroCheck account for an enforcement officer or administrator.
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="block sm:col-span-2">
                <span className="mb-1 block text-xs text-slate-500">Full name</span>
                <Input
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="Rajesh Kumar"
                />
              </label>
              <label className="block sm:col-span-2">
                <span className="mb-1 block text-xs text-slate-500">Email</span>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="officer@metrocheck.gov.in"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-slate-500">Role</span>
                <Select
                  value={form.role}
                  onValueChange={(value) => setForm({ ...form, role: value as UserRole })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="officer">Enforcement Officer</SelectItem>
                    <SelectItem value="admin">Administrator</SelectItem>
                    <SelectItem value="viewer">Viewer</SelectItem>
                  </SelectContent>
                </Select>
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-slate-500">Password (min 8 chars)</span>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="••••••••"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-slate-500">Department</span>
                <Input
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                  placeholder="Enforcement - Delhi"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs text-slate-500">Employee ID</span>
                <Input
                  value={form.employee_id}
                  onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
                  placeholder="OFF001"
                />
              </label>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={saving}>
                {saving ? 'Creating...' : 'Create user'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </RequireAuth>
  );
}