import { apiRequest } from "./client";
import type { MessageResponse } from "../types/common";

export async function listPayrollRuns(): Promise<MessageResponse> {
  return apiRequest<MessageResponse>("/payroll-runs");
}
