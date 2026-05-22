"use client";
import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "children"> {
  options: SelectOption[];
  placeholder?: string;
}

/**
 * Select estilizado usando `<select>` nativo — acessível, keyboard-friendly,
 * funciona em mobile com picker do SO.
 */
export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, placeholder, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "flex h-9 w-full appearance-none rounded-lg border border-[color:var(--input)] bg-[color:var(--background)] px-3 pr-8 text-sm transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-1 focus-visible:ring-offset-[color:var(--background)]",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      >
        {placeholder !== undefined && (
          <option value="">{placeholder}</option>
        )}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--muted-foreground)]" />
    </div>
  ),
);
Select.displayName = "Select";
