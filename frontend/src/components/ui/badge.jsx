import * as React from "react"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center border px-2 py-1 font-mono text-xs uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-foreground focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-foreground bg-muted text-foreground",
        primary:
          "border-primary bg-primary text-primary-foreground",
        secondary:
          "border-foreground bg-background text-foreground",
        destructive:
          "border-destructive bg-destructive text-white",
        outline: 
          "border-foreground bg-transparent text-foreground",
        ai:
          "border-accent bg-accent text-accent-foreground",
        success:
          "border-success bg-success text-white",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant,
  ...props
}) {
  return (<div className={cn(badgeVariants({ variant }), className)} {...props} />);
}

export { Badge, badgeVariants }
