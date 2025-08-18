import { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  variant?: "buy" | "sell" | "hold" | "default" | "primary" | "success" | "warning" | "error";
  size?: "sm" | "md";
  className?: string;
}

export function Badge({
  children,
  variant = "default",
  size = "md",
  className = "",
}: BadgeProps) {
  const variantClasses = {
    buy: "badge-buy",
    sell: "badge-sell",
    hold: "badge-hold",
    default: "bg-gray-500",
    primary: "bg-blue-500",
    success: "bg-green-500", 
    warning: "bg-orange-500",
    error: "bg-red-500",
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
        ${className}
      `.trim()}
    >
      {children}
    </span>
  );
}
