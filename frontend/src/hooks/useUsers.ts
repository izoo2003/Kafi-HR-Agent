import { useQuery } from "@tanstack/react-query";
import * as usersApi from "../api/users";
import type { PaginationParams } from "../types/common";

export function useUsers(params: PaginationParams) {
  return useQuery({
    queryKey: ["users", params],
    queryFn: () => usersApi.listUsers(params),
  });
}

export function useRoles() {
  return useQuery({
    queryKey: ["roles"],
    queryFn: () => usersApi.listRoles(),
  });
}
