/** Public feed URL for a LinkedIn Posts API share/ugcPost/activity URN. */
export function linkedInPostViewUrl(
  postUrn: string | null | undefined,
  storedUrl?: string | null,
): string | null {
  if (storedUrl?.startsWith("http")) return storedUrl;
  let raw = (postUrn || "").trim();
  if (!raw || raw.toLowerCase() === "posted") return null;
  try {
    raw = decodeURIComponent(raw);
  } catch {
    // keep raw
  }
  if (raw.includes("/posts/")) {
    raw = raw.split("/posts/").pop() || raw;
  }
  raw = raw.replace(/^\/+|\/+$/g, "");
  if (/^\d+$/.test(raw)) raw = `urn:li:share:${raw}`;
  if (!raw.startsWith("urn:li:")) return null;
  return `https://www.linkedin.com/feed/update/${raw}`;
}
