import { StatusBadge } from "../ui/Badge";
import { LINKEDIN_POST_STATUS_LABELS } from "../../constants/statusLabels";
import { linkedInPostViewUrl } from "../../lib/linkedin";
import type { LinkedInPostResult } from "../../types/cvScreening";

function formatPostedAt(iso: string | null): string {
  if (!iso) return "Published";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "Published";
  return `Published ${parsed.toLocaleString()}`;
}

type Props = {
  posts: LinkedInPostResult[];
};

export function LinkedInPostResults({ posts }: Props) {
  if (posts.length === 0) return null;
  const succeeded = posts.filter((p) => Boolean(p.postUrn) && !p.error).length;
  const failed = posts.length - succeeded;
  const summary =
    failed === 0
      ? `Posted successfully to ${succeeded === 1 ? "LinkedIn" : `${succeeded} LinkedIn accounts`}.`
      : succeeded === 0
        ? "LinkedIn posting failed."
        : `Posted to ${succeeded} of ${posts.length} LinkedIn accounts.`;

  return (
    <div style={{ display: "grid", gap: "var(--space-3)" }}>
      <p
        style={{
          margin: 0,
          color: failed === 0 ? "var(--color-status-positive)" : "var(--color-text-primary)",
          fontWeight: "var(--weight-medium)",
        }}
      >
        {summary}
      </p>
      <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: "var(--space-2)" }}>
        {posts.map((post) => {
          const ok = Boolean(post.postUrn) && !post.error;
          const viewUrl = linkedInPostViewUrl(post.postUrn, post.postUrl);
          return (
            <li
              key={post.account}
              data-status={ok ? "positive" : "critical"}
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "var(--space-2)",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "var(--space-3)",
                paddingLeft: "calc(var(--space-3) + 3px)",
                border: "1px solid var(--color-border)",
                borderLeft: `3px solid ${ok ? "var(--color-status-positive)" : "var(--color-status-critical)"}`,
                borderRadius: "var(--radius-sm)",
                background: "var(--color-surface)",
              }}
            >
              <div style={{ display: "grid", gap: 4 }}>
                <strong>{post.label || post.account}</strong>
                {ok ? (
                  <span style={{ fontSize: "var(--text-sm)", color: "var(--color-text-secondary)" }}>
                    {formatPostedAt(post.postedAt)}
                  </span>
                ) : (
                  <span style={{ fontSize: "var(--text-sm)", color: "var(--color-status-critical)" }}>
                    {post.error || "Not posted"}
                  </span>
                )}
              </div>
              <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
                <StatusBadge status={ok ? "posted" : "failed"}>
                  {ok ? LINKEDIN_POST_STATUS_LABELS.posted : LINKEDIN_POST_STATUS_LABELS.failed}
                </StatusBadge>
                {ok && viewUrl ? (
                  <a
                    href={viewUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "var(--color-accent)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)" }}
                  >
                    View post
                  </a>
                ) : ok ? (
                  <a
                    href="https://www.linkedin.com/feed/"
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: "var(--color-accent)", fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)" }}
                  >
                    Open LinkedIn feed
                  </a>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
