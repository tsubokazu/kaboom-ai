import { ReactNode, ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  children: ReactNode;
  icon?: ReactNode;
  loading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  children,
  icon,
  loading = false,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const baseClasses = "kb-btn";

  const variantClasses = {
    primary: "kb-btn-primary",
    secondary: "kb-btn-secondary",
    ghost: "hover:bg-gray-100 dark:hover:bg-gray-800",
  };

  const sizeClasses = {
    sm: "h-8 px-3 text-sm",
    md: "h-10 px-4",
    lg: "h-12 px-6 text-lg",
  };

  const isDisabled = disabled || loading;

  return (
    <button
      className={`
        ${baseClasses}
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${isDisabled ? "opacity-50 cursor-not-allowed" : ""}
        ${className}
      `.trim()}
      disabled={isDisabled}
      {...props}
    >
      {loading && (
        <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
      )}
      {icon && !loading && icon}
      {children}
    </button>
  );
}
