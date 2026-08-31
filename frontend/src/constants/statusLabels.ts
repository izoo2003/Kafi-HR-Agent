/** Single vocabulary for status labels — UI_DESIGN_SYSTEM.md §6. */

export const ATTENDANCE_STATUS_LABELS = {
  present: "Present",
  absent: "Absent",
  late: "Late",
  half_day: "Half Day",
  on_leave: "On Leave",
  holiday: "Holiday",
} as const;

export const PAYROLL_STATUS_LABELS = {
  draft: "Draft",
  pending_approval: "Pending Approval",
  approved: "Approved",
  paid: "Paid",
} as const;

export const CANDIDATE_STATUS_LABELS = {
  uploaded: "Uploaded",
  parsed: "Parsed",
  scored: "Scored",
  shortlisted: "Shortlisted",
  rejected: "Rejected",
  hired: "Hired",
} as const;

export const KPI_STATUS_LABELS = {
  on_target: "On Target",
  at_risk: "At Risk",
  below_target: "Below Target",
  complete: "Complete",
} as const;

export const LEAVE_STATUS_LABELS = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
} as const;

export const LEAVE_TYPE_LABELS = {
  annual: "Annual",
  sick: "Sick",
  unpaid: "Unpaid",
  other: "Other",
} as const;

export const LINKEDIN_POST_STATUS_LABELS = {
  posted: "Posted",
  failed: "Failed",
} as const;

export const RESIGNATION_STATUS_LABELS = {
  draft: "Draft",
  pending: "Pending",
  accepted: "Accepted",
  rejected: "Rejected",
  cancelled: "Cancelled",
} as const;

