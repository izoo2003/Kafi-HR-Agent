export interface JobDescription {
  id: number;
  title: string;
  departmentId: number;
  descriptionText: string;
  requirementsText: string | null;
  filePath: string | null;
  status: "draft" | "open" | "closed" | string;
  createdBy: number;
  createdAt: string;
  updatedAt: string;
}

export interface JobDescriptionCreate {
  title: string;
  departmentId: number;
  descriptionText: string;
  requirementsText?: string;
  status?: "draft" | "open" | "closed";
}

export interface ScoringCriteria {
  id: number;
  jobDescriptionId: number;
  criterionName: string;
  weight: number;
  scoringRules: Record<string, unknown> | null;
  createdAt: string;
  updatedAt: string;
}

export interface ScoringCriteriaInput {
  criterionName: string;
  weight: number;
  scoringRules: Record<string, unknown>;
}

export interface Candidate {
  id: number;
  jobDescriptionId: number;
  fullName: string | null;
  email: string | null;
  phone: string | null;
  cvFilePath: string;
  parsedData: Record<string, unknown> | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface RankingRow {
  candidateId: number;
  fullName: string | null;
  email: string | null;
  status: string;
  totalScore: number;
  rankPosition: number;
  pendingManualReview: boolean;
}

export interface SkillEvaluationRow {
  skill: string;
  requiredLevel: number;
  matched: boolean;
  rawScore: number | null;
  maxPoints: number;
  notes: string | null;
}

export interface CandidateEvaluation {
  candidateId: number;
  jobDescriptionId: number;
  jobTitle: string;
  overallScore: number | null;
  rankPosition: number | null;
  recommendation: "shortlist" | "consider" | "reject";
  recommendationLabel: string;
  summary: string;
  strengths: string[];
  gaps: string[];
  skills: SkillEvaluationRow[];
}
