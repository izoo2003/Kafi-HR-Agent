import { apiRequest, setTokens, clearTokens } from "./client";
import type { AuthContextData, MessageResponse, TokenResponse } from "../types/common";

export async function login(username: string, password: string): Promise<TokenResponse> {
  const data = await apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
  setTokens(data.accessToken, data.refreshToken);
  return data;
}

export async function register(payload: {
  fullName: string;
  username: string;
  pin: string;
  departmentId: number;
}): Promise<TokenResponse> {
  const data = await apiRequest<TokenResponse>("/auth/register", {
    method: "POST",
    body: payload,
    auth: false,
  });
  setTokens(data.accessToken, data.refreshToken);
  return data;
}

export async function getRegisterOptions(): Promise<{ departments: { id: number; name: string }[] }> {
  const data = await apiRequest<{ departments: { id: number; name: string }[] }>(
    "/auth/register-options",
    { method: "GET", auth: false },
  );
  return { departments: data?.departments ?? [] };
}

export async function refresh(refreshToken: string): Promise<TokenResponse> {
  const data = await apiRequest<TokenResponse>("/auth/refresh", {
    method: "POST",
    body: { refreshToken },
    auth: false,
  });
  setTokens(data.accessToken, data.refreshToken);
  return data;
}

export async function logout(): Promise<MessageResponse> {
  try {
    return await apiRequest<MessageResponse>("/auth/logout", { method: "POST" });
  } finally {
    clearTokens();
  }
}

export async function getMe(): Promise<AuthContextData> {
  return apiRequest<AuthContextData>("/auth/me");
}
