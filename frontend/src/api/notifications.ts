import { apiRequest } from "./client";
import type { PaginatedResponse } from "../types/common";

export interface AppNotification {
  id: number;
  userId: number;
  title: string;
  body: string;
  kind: string;
  payload: Record<string, unknown> | null;
  readAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export function listNotifications(params?: {
  page?: number;
  pageSize?: number;
  unreadOnly?: boolean;
}): Promise<PaginatedResponse<AppNotification>> {
  return apiRequest<PaginatedResponse<AppNotification>>("/notifications", { params });
}

export function getUnreadNotificationCount(): Promise<{ unread: number }> {
  return apiRequest<{ unread: number }>("/notifications/unread-count");
}

export function markNotificationRead(id: number): Promise<AppNotification> {
  return apiRequest<AppNotification>(`/notifications/${id}/read`, { method: "POST" });
}

export function markAllNotificationsRead(): Promise<{ message: string }> {
  return apiRequest<{ message: string }>("/notifications/read-all", { method: "POST" });
}
