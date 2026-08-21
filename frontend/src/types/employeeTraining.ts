export type TrainingLevel = "intermediate" | "advanced";
export type TrainingStatus = "assigned" | "in_progress" | "completed";

export interface TrainingCourseRecommendation {
  title: string;
  level: TrainingLevel;
  description: string;
  provider: string | null;
  urlHint: string | null;
}

export interface EmployeeTrainingRecommendResult {
  employeeId: number;
  employeeName: string;
  departmentName: string | null;
  roleTitle: string;
  topic: string;
  courses: TrainingCourseRecommendation[];
}

export interface EmployeeTrainingAssignment {
  id: number;
  employeeId: number;
  employeeName: string | null;
  employeeCode: string | null;
  title: string;
  level: TrainingLevel;
  description: string;
  provider: string | null;
  urlHint: string | null;
  topicPrompt: string;
  departmentName: string | null;
  roleTitle: string | null;
  status: TrainingStatus;
  assignedBy: number;
  assignedAt: string;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EmployeeTrainingList {
  items: EmployeeTrainingAssignment[];
  total: number;
}
