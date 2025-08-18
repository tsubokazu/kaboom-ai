import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error, label, helperText, className = "", ...props }, ref) => {
    return (
      <div className="space-y-1">
        {label && (
          <label
            className="block text-sm font-medium"
            style={{ color: "var(--kb-text)" }}
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={`
            kb-input
            w-full
            ${error ? "border-red-500 focus:border-red-500" : "focus:border-[var(--kb-brand)]"}
            focus:outline-none focus:ring-2 focus:ring-[var(--kb-brand)] focus:ring-opacity-20
            transition-colors duration-200
            ${className}
          `.trim()}
          {...props}
        />
        {(error || helperText) && (
          <p
            className="text-xs"
            style={{
              color: error ? "var(--kb-error)" : "var(--kb-text-muted)",
            }}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
