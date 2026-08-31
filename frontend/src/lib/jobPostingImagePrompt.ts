export const GEMINI_APP_URL = "https://gemini.google.com/";

export type JobPostingImagePromptInput = {
  title: string;
  departmentName?: string | null;
  descriptionText?: string | null;
  requirementsText?: string | null;
  skillNames?: string[];
  applicationFormUrl?: string | null;
};

function section(label: string, value: string | null | undefined): string {
  const text = (value ?? "").trim();
  return text ? `${label}\n${text}` : `${label}\n(not provided — infer concise professional copy for this role)`;
}

export function buildJobPostingImagePrompt(input: JobPostingImagePromptInput): string {
  const title = input.title.trim();
  const department = (input.departmentName ?? "").trim();
  const applyUrl = (input.applicationFormUrl ?? "").trim();
  const skills = (input.skillNames ?? []).map((s) => s.trim()).filter(Boolean);

  const applyBlock = applyUrl
    ? `Candidates must submit their details and CV through this Google Form (show this URL clearly on the poster):\n${applyUrl}`
    : "Candidates should submit their details and CV to hr@kafi-group.com (show this email clearly on the poster).";

  const skillsBlock = skills.length
    ? `KEY SKILLS\n${skills.map((s) => `- ${s}`).join("\n")}`
    : "";

  const parts = [
    "Generate a professional LinkedIn hiring poster image for Kafi Group. Do not write a text-only reply — create the image.",
    section("JOB TITLE", title),
    department ? `DEPARTMENT\n${department}` : null,
    section("DESCRIPTION", input.descriptionText),
    section("RESPONSIBILITIES / REQUIREMENTS", input.requirementsText),
    skillsBlock || null,
    `WHERE TO SUBMIT THE CV\n${applyBlock}`,
    [
      "DESIGN DIRECTIONS",
      "- Vertical recruitment poster (about 1080×1350) suitable for LinkedIn",
      "- Company name: Kafi Group",
      "- Large, readable job title at the top",
      "- Two clear sections: Description and Responsibilities, using the copy above (do not invent extra duties)",
      "- Footer must show how to apply: the CV submission link or email above",
      "- High-contrast corporate look: deep black background, red and yellow accents, clean sans-serif type",
      "- No stock-photo clutter, no watermarks, no fake logos, no hashtags",
      "- All on-image text must be spelled correctly and match the provided copy",
    ].join("\n"),
  ];

  return parts.filter((part): part is string => Boolean(part)).join("\n\n");
}

export async function copyTextToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    document.body.removeChild(area);
  }
}
