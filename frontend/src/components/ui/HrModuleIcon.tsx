import type { HrModuleIconKey } from "../../constants/hrModuleIcons";
import { hrModuleIconIndex } from "../../constants/hrModuleIcons";
import "./HrModuleIcon.css";

type Props = {
  icon: HrModuleIconKey | number;
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
  label?: string;
};

const SIZE_PX = { sm: 22, md: 28, lg: 36, xl: 48 } as const;

export function HrModuleIcon({ icon, size = "md", className = "", label }: Props) {
  const index = typeof icon === "number" ? icon : hrModuleIconIndex(icon);
  const col = index % 7;
  const row = Math.floor(index / 7);
  const px = SIZE_PX[size];

  return (
    <span
      className={`hr-module-icon hr-module-icon--${size} ${className}`.trim()}
      style={{
        width: px,
        height: px,
        backgroundPosition: `${(col / 6) * 100}% ${(row / 2) * 100}%`,
      }}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    />
  );
}
