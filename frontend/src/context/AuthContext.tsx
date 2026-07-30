import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as authApi from "../api/auth";
import { clearTokens, getAccessToken, setUnauthorizedHandler } from "../api/client";
import { AGENT_KEY, PERMISSION_RANK } from "../lib/case";
import type { AuthContextData, PermissionLevel } from "../types/common";

type AuthState = {
  user: AuthContextData | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
  hasPermission: (moduleKey: string, minLevel: PermissionLevel) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthContextData | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      return;
    }
    const me = await authApi.getMe();
    setUser(me);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clearTokens();
      setUser(null);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (getAccessToken()) {
          await refreshMe();
        }
      } catch {
        clearTokens();
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshMe]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login(email, password);
    setUser(res.auth);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      clearTokens();
    }
    setUser(null);
  }, []);

  const hasPermission = useCallback(
    (moduleKey: string, minLevel: PermissionLevel) => {
      if (!user) return false;
      const key = `${AGENT_KEY}.${moduleKey}`;
      const level = user.agentPermissions[key] ?? "none";
      return (PERMISSION_RANK[level] ?? 0) >= (PERMISSION_RANK[minLevel] ?? 99);
    },
    [user],
  );

  const value = useMemo(
    () => ({ user, loading, login, logout, refreshMe, hasPermission }),
    [user, loading, login, logout, refreshMe, hasPermission],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}
