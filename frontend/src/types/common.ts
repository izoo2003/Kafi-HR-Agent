export type PermissionLevel = "none" | "read" | "write" | "approve" | "admin";

export type AuthSource = "standalone" | "orchestrator";

export interface AuthContextData {
  userId: number;
  email: string;
  username: string | null;
  roles: string[];
  agentPermissions: Record<string, string>;
  source: AuthSource;
  linkedEmployeeId: number | null;
  departmentId: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
}

export interface ApiErrorResponse {
  error: ApiErrorBody;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
  sort?: string;
  [key: string]: string | number | boolean | undefined;
}

export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  auth: AuthContextData;
}

export interface MessageResponse {
  message: string;
}
