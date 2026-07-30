import { apiRequest, setTokens, clearTokens } from "./client";
import type { AuthContextData, MessageResponse, TokenResponse } from "../types/common";

export async function login(email: string, password: string): Promise<TokenResponse> {
  const data = await apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  setTokens(data.accessToken, data.refreshToken);
  return data;
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
