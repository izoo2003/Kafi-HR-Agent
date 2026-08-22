export type EducationVerificationStatus =
  | "verified"
  | "partial"
  | "unverified"
  | "unreadable"
  | "not_education_document"
  | "needs_documents";

export type EducationDocumentType = "marks_sheet" | "grade_sheet" | "unknown";

export interface EducationDocumentSummary {
  documentType: EducationDocumentType;
  readable: boolean;
  looksLikeEducationDocument: boolean;
  studentName: string | null;
  programOrDegree: string | null;
  boardOrUniversity: string | null;
  notes: string | null;
}

export interface EducationInstitutionCheck {
  name: string;
  institutionType: "school" | "college" | "university" | "board" | "other";
  country: string | null;
  city: string | null;
  verified: boolean;
  confidence: "high" | "medium" | "low";
  verificationNote: string;
  sourceHint: string | null;
}

export interface EducationVerificationChecks {
  documentsProvided: number;
  documentsReadable: boolean;
  looksLikeEducationDocuments: boolean;
  allInstitutionsVerified: boolean;
  anyInstitutionVerified: boolean;
}

export interface EducationVerificationResult {
  status: EducationVerificationStatus;
  verified: boolean;
  message: string;
  documents: EducationDocumentSummary[];
  institutions: EducationInstitutionCheck[];
  checks: EducationVerificationChecks;
  disclaimer: string;
}
