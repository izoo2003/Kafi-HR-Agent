export interface User {
  id: number;
  email: string;
  username: string | null;
  fullName: string;
  isActive: boolean;
  roles: string[];
  departmentId: number | null;
  departmentName: string | null;
  linkedEmployeeId: number | null;
  isSelfRegistered: boolean;
  loginIdentifier: string | null;
  loginPin: string | null;
  lastLoginAt: string | null;
  createdAt: string | null;
}

export interface Role {
  id: number;
  name: string;
  description: string | null;
}
