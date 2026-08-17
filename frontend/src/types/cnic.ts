export type CnicVerificationStatus =
  | "verified"
  | "mismatch"
  | "invalid_format"
  | "unreadable"
  | "not_cnic_document"
  | "needs_image";

export interface CnicExtractedFields {
  cnic: string | null;
  fullName: string | null;
  fatherName: string | null;
  dateOfBirth: string | null;
  gender: string | null;
  issueDate: string | null;
  expiryDate: string | null;
  address: string | null;
  notes: string | null;
}

export interface CnicVerificationChecks {
  formatValid: boolean;
  imageProvided: boolean;
  imageReadable: boolean;
  looksLikePakistanCnic: boolean;
  cnicMatch: boolean;
}

export interface CnicVerificationResult {
  status: CnicVerificationStatus;
  authentic: boolean;
  message: string;
  typedCnic: string;
  extracted: CnicExtractedFields | null;
  checks: CnicVerificationChecks;
  disclaimer: string;
}
