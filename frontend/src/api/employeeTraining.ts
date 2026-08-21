import { apiRequest } from "./client";
import type {
  EmployeeTrainingAssignment,
  EmployeeTrainingList,
  EmployeeTrainingRecommendResult,
  TrainingCourseRecommendation,
  TrainingStatus,
} from "../types/employeeTraining";

export async function recommendEmployeeTraining(payload: {
  employeeId: number;
  topic: string;
}): Promise<EmployeeTrainingRecommendResult> {
  return apiRequest<EmployeeTrainingRecommendResult>("/employee-training/recommend", {
    method: "POST",
    body: payload,
  });
}

export async function assignEmployeeTraining(payload: {
  employeeId: number;
  topic: string;
  courses: TrainingCourseRecommendation[];
}): Promise<{ items: EmployeeTrainingAssignment[] }> {
  return apiRequest("/employee-training/assign", {
    method: "POST",
    body: payload,
  });
}

export async function listEmployeeTraining(params?: {
  employeeId?: number;
}): Promise<EmployeeTrainingList> {
  return apiRequest<EmployeeTrainingList>("/employee-training", {
    params: params?.employeeId != null ? { employeeId: params.employeeId } : undefined,
  });
}

export async function updateEmployeeTrainingStatus(
  assignmentId: number,
  status: TrainingStatus,
): Promise<EmployeeTrainingAssignment> {
  return apiRequest<EmployeeTrainingAssignment>(`/employee-training/${assignmentId}`, {
    method: "PATCH",
    body: { status },
  });
}
