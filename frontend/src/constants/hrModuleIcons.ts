/**
 * Sprite indices for /hr-module-icons.png (7 columns × 3 rows).
 * Labels match the generated HR AI Module icon set.
 */
export const HR_MODULE_ICONS = {
  employeeDirectory: 0,
  addEmployee: 1,
  attendance: 2,
  leave: 3,
  timeShift: 4,
  performanceReviews: 5,
  goalsOkrs: 6,
  payroll: 7,
  salaryReports: 8,
  compliancePolicies: 9,
  trainingDevelopment: 10,
  rewards: 11,
  employeeFeedback: 12,
  onboarding: 13,
  documentManagement: 14,
  notifications: 15,
  hrAiAssistant: 16,
  analyticsDashboard: 17,
  recruitment: 18,
  exitManagement: 19,
  employeeHandbook: 20,
} as const;

export type HrModuleIconKey = keyof typeof HR_MODULE_ICONS;

export function hrModuleIconIndex(key: HrModuleIconKey): number {
  return HR_MODULE_ICONS[key];
}

/** Map sidebar routes to the best-fit generated icon. */
export const SIDEBAR_ICON_BY_PATH: Record<string, HrModuleIconKey> = {
  "/admin/dashboard": "analyticsDashboard",
  "/my-role": "employeeHandbook",
  "/employees": "employeeDirectory",
  "/job-descriptions": "recruitment",
  "/cv-screening": "documentManagement",
  "/attendance": "attendance",
  "/payroll/runs": "payroll",
  "/kpi/dashboard": "goalsOkrs",
  "/employee-development/performance": "trainingDevelopment",
  "/hr-policies": "compliancePolicies",
  "/admin/users": "addEmployee",
};

/** Icons for sidebar subsection links (same sprite as top-level nav). */
export const SIDEBAR_SUB_ICON: Record<string, HrModuleIconKey> = {
  departments: "compliancePolicies",
  appointmentLetter: "documentManagement",
  contractLetter: "employeeHandbook",
  documentVerification: "documentManagement",
  verifyCnic: "addEmployee",
  verifyEducation: "trainingDevelopment",
  employeePerformance: "performanceReviews",
  employeeTraining: "trainingDevelopment",
  employeeResignation: "exitManagement",
  thingsToLearn: "goalsOkrs",
  viewUsers: "employeeDirectory",
  createUsers: "addEmployee",
};
