import { apiRequest } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type { Role, User } from "../types/users";

export async function listUsers(
  params: PaginationParams & { isActive?: boolean; selfRegisteredOnly?: boolean } = {},
): Promise<PaginatedResponse<User>> {
  return apiRequest<PaginatedResponse<User>>("/users", { params });
}

export async function listRoles(): Promise<Role[]> {
  return apiRequest<Role[]>("/roles");
}

export async function setUserPassword(
  userId: number,
  password: string,
): Promise<{
  id: number;
  fullName: string;
  username: string | null;
  email: string;
  loginIdentifier: string;
  password: string;
}> {
  return apiRequest(`/users/${userId}/set-password`, {
    method: "POST",
    body: { password },
  });
}
