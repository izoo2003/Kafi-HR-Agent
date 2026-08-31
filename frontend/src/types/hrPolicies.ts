export type HrPolicyIcon = "documents" | "timings" | "sop" | "leave" | "confidentiality";
export type HrPolicyListStyle = "ol" | "ul" | "paragraphs";

export interface HrPolicyItem {
  text: string;
  quoted: boolean;
  children: string[];
}

export interface HrPolicySection {
  id: string;
  title: string;
  icon: HrPolicyIcon;
  status: string;
  listStyle: HrPolicyListStyle;
  items: HrPolicyItem[];
}

export interface HrPoliciesDocument {
  welcomeTitle: string;
  welcomeSubtitle: string;
  sections: HrPolicySection[];
}
