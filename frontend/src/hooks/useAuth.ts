import { useAuthContext } from "../context/AuthContext";

/** Thin wrapper — pages/hooks import useAuth, not the context module directly. */
export function useAuth() {
  return useAuthContext();
}
