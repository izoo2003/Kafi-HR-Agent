import type { InputHTMLAttributes, ReactNode } from "react";
import "./FormField.css";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: ReactNode;
};

export function FormField({ label, error, hint, id, className = "", ...rest }: Props) {
  const fieldId = id ?? rest.name ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className={`form-field ${className}`.trim()} htmlFor={fieldId}>
      <span className="form-field__label">{label}</span>
      <input
        id={fieldId}
        className={`form-field__input${error ? " form-field__input--error" : ""}`}
        {...rest}
      />
      {error ? <span className="form-field__error">{error}</span> : null}
      {!error && hint ? <span className="form-field__hint">{hint}</span> : null}
    </label>
  );
}
