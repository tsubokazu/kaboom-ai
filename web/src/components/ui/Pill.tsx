import { ReactNode } from "react";

interface PillProps {
  active?: boolean;
  children: ReactNode;
  onClick?: () => void;
}

export function Pill({ active = false, children, onClick }: PillProps) {
  return (
    <button className={`kb-pill ${active ? "active" : ""}`} onClick={onClick}>
      {children}
    </button>
  );
}
