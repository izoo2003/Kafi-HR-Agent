import "./Toast.css";

export type ToastItem = {
  id: string;
  message: string;
  tone?: "info" | "warning" | "critical" | "positive";
};

type Props = {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
};

export function ToastStack({ toasts, onDismiss }: Props) {
  if (!toasts.length) return null;
  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast--${t.tone ?? "info"}`} role="status">
          <span>{t.message}</span>
          <button type="button" className="toast__close" onClick={() => onDismiss(t.id)} aria-label="Dismiss">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
