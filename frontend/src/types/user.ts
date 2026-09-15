export type UserRole = 'admin' | 'officer' | 'viewer';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  department: string | null;
  employee_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface UserCreate {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  department?: string;
  employee_id?: string;
}