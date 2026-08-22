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
      employeeId: number;
      username: string;
      pin: string;
    }) => usersApi.createUser(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
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

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => usersApi.deactivateUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      qc.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}
