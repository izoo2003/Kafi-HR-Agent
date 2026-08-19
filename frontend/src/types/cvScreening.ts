export interface LinkedInAccount {
  name: string;
  label: string;
}

export interface LinkedInPostResult {
  account: string;
  label: string | null;
  authorUrn: string | null;
  postUrn: string | null;
  postUrl: string | null;
  postedAt: string | null;
  error: string | null;
}

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
  applicantsCount: number;
  applicationFormUrl: string | null;
  linkedinPosts: LinkedInPostResult[];
}

export interface JobDescriptionCreate {
  title: string;
  departmentId: number;
  descriptionText: string;
  requirementsText?: string;
  status?: "draft" | "open" | "closed";
  linkedinAccountNames?: string[];
}

export interface JobPostingAiDraftRequest {
  title: string;
  departmentId: number;
}

export interface JobPostingAiDraftSkill {
  name: string;
  level: number;
}

export interface JobPostingAiDraftResult {
  descriptionText: string;
  requirementsText: string;
  skills: JobPostingAiDraftSkill[];
  applicationFormUrl: string | null;
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

export type CvSource = "manual" | "webmail" | "outlook" | "whatsapp" | "gmail" | "google_form";

export interface Candidate {
  id: number;
  jobDescriptionId: number | null;
  fullName: string | null;
  email: string | null;
  phone: string | null;
  cvFilePath: string;
  parsedData: Record<string, unknown> | null;
  status: string;
  source: CvSource;
  sourceRef: string | null;
  matchConfidence: number | null;
  matchReasoning: string | null;
  submittedAt: string | null;
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
  ratingOutOf10: number | null;
  recommendation: "shortlist" | "consider" | "reject";
  recommendationLabel: string;
  summary: string;
  whyAccepted: string;
  whyRejected: string;
  strengths: string[];
  gaps: string[];
  skills: SkillEvaluationRow[];
}

export interface CvSourceResult {
  source: "webmail" | "outlook" | "whatsapp" | "gmail" | "google_form";
  configured: boolean;
  fetched: number;
  message: string | null;
}

export interface CvSyncResult {
  sources: CvSourceResult[];
  totalFetched: number;
  autoMatched: number;
  unassigned: number;
  duplicatesSkipped: number;
  restoredFiles?: number;
  candidates: Candidate[];
}

export interface CandidateAssignRequest {
  jobDescriptionId: number;
}
