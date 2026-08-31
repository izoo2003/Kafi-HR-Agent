import { apiRequest } from "./client";
import type { HrPoliciesDocument } from "../types/hrPolicies";

export async function getHrPolicies(): Promise<HrPoliciesDocument> {
  return apiRequest<HrPoliciesDocument>("/hr-policies");
}

export async function saveHrPolicies(payload: HrPoliciesDocument): Promise<HrPoliciesDocument> {
  return apiRequest<HrPoliciesDocument>("/hr-policies", { method: "PUT", body: payload });
}
