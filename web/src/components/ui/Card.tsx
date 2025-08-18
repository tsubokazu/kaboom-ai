import { ReactNode, HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
  hover?: boolean;
}

export function Card({
  children,
  padding = "md",
  hover = false,
  className = "",
  ...props
}: CardProps) {
  const paddingClasses = {
    none: "",
    sm: "p-4",
    md: "p-6",
    lg: "p-8",
  };

  return (
    <div
      className={`
        kb-card
        ${paddingClasses[padding]}
        ${hover ? "hover:shadow-lg transition-shadow duration-200" : ""}
        ${className}
      `.trim()}
      {...props}
    >
      {children}
    </div>
  );
}
