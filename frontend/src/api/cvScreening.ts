import { apiRequest } from "./client";
import type { MessageResponse } from "../types/common";

export async function listCandidatesPlaceholder(): Promise<MessageResponse> {
  return apiRequest<MessageResponse>("/candidates");
}
