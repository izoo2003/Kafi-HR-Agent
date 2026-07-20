const VERDICT_STYLES: Record<string, { bg: string; fg: string }> = {
  "STRONG HIRE": { bg: "#c6efce", fg: "#1e6b2e" },
  RECOMMEND: { bg: "#dce6f1", fg: "#1f4e79" },
  CONDITIONAL: { bg: "#ffeb9c", fg: "#8a6100" },
  "NOT RECOMMENDED": { bg: "#ffc7ce", fg: "#9c1c28" },
};

export function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="badge badge-neutral">—</span>;
  const style = VERDICT_STYLES[verdict] ?? { bg: "#eee", fg: "#333" };
  return (
    <span className="badge" style={{ backgroundColor: style.bg, color: style.fg }}>
      {verdict}
    </span>
  );
}
