import { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  variant?: "buy" | "sell" | "hold" | "default";
  size?: "sm" | "md";
}

export function Badge({
  children,
  variant = "default",
  size = "md",
}: BadgeProps) {
  const variantClasses = {
    buy: "badge-buy",
    sell: "badge-sell",
    hold: "badge-hold",
    default: "bg-gray-500",
  };

  const sizeClasses = {
    sm: "text-xs px-2 py-1",
    md: "text-sm px-3 py-1",
  };

  return (
    <span
      className={`
        kb-badge
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        inline-flex items-center
      `.trim()}
    >
      {children}
    </span>
  );
}
