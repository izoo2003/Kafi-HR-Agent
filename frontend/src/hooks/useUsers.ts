import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      fullName: string;
      username: string;
      pin: string;
      departmentId: number;
    }) => usersApi.createUser(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}

export function useSetUserPassword() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, password }: { userId: number; password: string }) =>
      usersApi.setUserPassword(userId, password),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}
