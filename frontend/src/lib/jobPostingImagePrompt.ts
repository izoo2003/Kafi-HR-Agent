export const GEMINI_APP_URL = "https://gemini.google.com/";

export const HIRING_APPLY_EMAIL = "hr@kafi-group.com";

export type JobPostingImagePromptInput = {
  title: string;
  departmentName?: string | null;
  descriptionText?: string | null;
  requirementsText?: string | null;
  skillNames?: string[];
  /** Ignored — posters use HIRING_APPLY_EMAIL, never a Google Form URL. */
  applicationFormUrl?: string | null;
};

function stripApplyUrls(value: string | null | undefined): string {
  let text = (value ?? "").trim();
  if (!text) return "";
  text = text.replace(/\n*Apply Here\s*->\s*\S+/gi, "");
  text = text.replace(/https?:\/\/(?:docs\.)?google\.com\/forms\/\S+/gi, "");
  text = text.replace(/https?:\/\/forms\.gle\/\S+/gi, "");
  return text.replace(/\n{3,}/g, "\n\n").trim();
}

function section(label: string, value: string | null | undefined): string {
  const text = stripApplyUrls(value);
  return text
    ? `${label}\n${text}`
    : `${label}\n(not provided — infer concise professional copy for this role)`;
}

export function buildJobPostingImagePrompt(input: JobPostingImagePromptInput): string {
  const title = input.title.trim();
  const department = (input.departmentName ?? "").trim();
  const skills = (input.skillNames ?? []).map((s) => s.trim()).filter(Boolean);

  const skillsBlock = skills.length
    ? `KEY SKILLS\n${skills.map((s) => `- ${s}`).join("\n")}`
    : "";

  const parts = [
    "Generate a professional LinkedIn hiring poster image for Kafi Group. Do not write a text-only reply — create the image.",
    "OUTPUT FORMAT: Produce the poster as a PNG or JPG image file (raster image). Do not return SVG, PDF, or text-only output.",
    section("JOB TITLE", title),
    department ? `DEPARTMENT\n${department}` : null,
    section("DESCRIPTION", input.descriptionText),
    section("RESPONSIBILITIES / REQUIREMENTS", input.requirementsText),
    skillsBlock || null,
    [
      "WHERE TO APPLY (footer of the poster)",
      `Show this email clearly as the apply / send-CV address: ${HIRING_APPLY_EMAIL}`,
      "Do NOT put any Google Form URL, docs.google.com link, forms.gle link, or any other website URL on the image.",
    ].join("\n"),
    [
      "DESIGN DIRECTIONS",
      "- Vertical recruitment poster (about 1080×1350) suitable for LinkedIn",
      "- Deliver the final poster as PNG or JPG only",
      "- Company name: Kafi Group",
      "- Large, readable job title at the top",
      "- Two clear sections: Description and Responsibilities, using the copy above (do not invent extra duties)",
      `- Footer must say Apply here / Send your CV to ${HIRING_APPLY_EMAIL} — email only, no URLs`,
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
