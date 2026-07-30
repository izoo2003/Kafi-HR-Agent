import { apiRequest } from "./client";
import type { PaginatedResponse, PaginationParams } from "../types/common";
import type { Role, User } from "../types/users";

export async function listUsers(params: PaginationParams = {}): Promise<PaginatedResponse<User>> {
  return apiRequest<PaginatedResponse<User>>("/users", { params });
}

export async function listRoles(): Promise<Role[]> {
  return apiRequest<Role[]>("/roles");
}
