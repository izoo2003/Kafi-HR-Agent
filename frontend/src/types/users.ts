export interface User {
  id: number;
  email: string;
  fullName: string;
  isActive: boolean;
}

export interface Role {
  id: number;
  name: string;
  description: string | null;
}
