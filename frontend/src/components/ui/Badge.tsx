import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

const VARIANTS = {
  default: "bg-secondary text-secondary-foreground",
  primary: "bg-primary text-primary-foreground",
  success: "bg-success text-success-foreground",
  warning: "bg-warning text-warning-foreground",
  destructive: "bg-destructive text-destructive-foreground",
  outline: "border border-border text-foreground",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof VARIANTS;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        VARIANTS[variant],
        className
      )}
      {...props}
    />
  );
}

// maps a Run state to a sensible badge variant, used across every surface
// that displays run status so the visual language stays consistent
export function runStateVariant(state: string): keyof typeof VARIANTS {
  if (["COMPLETED"].includes(state)) return "success";
  if (["FAILED", "CANCELLED"].includes(state)) return "destructive";
  if (["REVIEW_REQUIRED", "AWAITING_APPROVAL", "RECOVERY"].includes(state)) return "warning";
  if (["CREATED"].includes(state)) return "outline";
  return "primary";
}

export function significanceVariant(sig: string): keyof typeof VARIANTS {
  if (sig === "significant") return "destructive";
  if (sig === "notable") return "warning";
  if (sig === "minor") return "primary";
  return "default";
}
