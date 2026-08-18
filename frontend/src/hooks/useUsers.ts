import { useQuery } from "@tanstack/react-query";
import * as usersApi from "../api/users";
import type { PaginationParams } from "../types/common";

export function useUsers(
  params: PaginationParams & { isActive?: boolean; selfRegisteredOnly?: boolean } = {},
) {
  return useQuery({
    queryKey: ["users", params],
    queryFn: () => usersApi.listUsers(params),
    refetchOnWindowFocus: true,
  });
}

export function useRoles() {
  return useQuery({
    queryKey: ["roles"],
    queryFn: () => usersApi.listRoles(),
  });
}
