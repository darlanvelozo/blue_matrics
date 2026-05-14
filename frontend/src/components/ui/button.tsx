"use client";
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--background)] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-[color:var(--primary)] text-[color:var(--primary-foreground)] hover:opacity-90 shadow-sm",
        secondary:
          "bg-[color:var(--secondary)] text-[color:var(--secondary-foreground)] hover:opacity-90",
        outline:
          "border border-[color:var(--border)] bg-transparent hover:bg-[color:var(--accent)] hover:text-[color:var(--accent-foreground)]",
        ghost: "hover:bg-[color:var(--accent)] hover:text-[color:var(--accent-foreground)]",
        link: "text-[color:var(--primary)] underline-offset-4 hover:underline",
        destructive:
          "bg-[color:var(--destructive)] text-[color:var(--destructive-foreground)] hover:opacity-90",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-11 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  ),
);
Button.displayName = "Button";
