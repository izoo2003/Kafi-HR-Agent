/** User-facing CV → job match line. Never surfaces API-key / matcher internals. */

export function formatCvMatchGuess(
  reasoning: string | null | undefined,
  confidence: number | null | undefined,
): string | null {
  const cleaned = (reasoning ?? "")
    .replace(/\s*\([^)]*API[_ ]?KEY[^)]*\)\.?/gi, "")
    .replace(/\s*\(Gemini match failed:[^)]*\)\.?/gi, "")
    .replace(/\s*\(using fallback matcher\)\.?/gi, "")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[.\s]+$/, "");

  const pct =
    confidence != null && Number.isFinite(confidence)
      ? Math.round(Math.max(0, Math.min(1, confidence)) * 100)
      : null;

  const overlap = cleaned.match(/Keyword overlap with ['"]([^'"]+)['"]/i);
  const already = cleaned.match(/(?:^|\b)(?:\d+%\s+)?confident this is\s+(.+)$/i);
  const role = (overlap?.[1] ?? already?.[1] ?? "").replace(/\.$/, "").trim();
  const noMatch = /no matching role|no keyword overlap|no job descriptions/i.test(cleaned);

  if (role && !noMatch) {
    return pct != null ? `${pct}% confident this is ${role}` : `Confident this is ${role}`;
  }
  if (noMatch || (pct === 0 && !role)) {
    return "No matching role found";
  }
  if (pct != null) {
    return `${pct}% confident this is the best matching role`;
  }
  return cleaned || null;
}
