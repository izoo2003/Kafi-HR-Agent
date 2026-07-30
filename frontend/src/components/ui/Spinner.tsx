import "./Spinner.css";

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="spinner" role="status" aria-label={label}>
      <span className="spinner__dot" />
      <span className="spinner__text">{label}…</span>
    </div>
  );
}
