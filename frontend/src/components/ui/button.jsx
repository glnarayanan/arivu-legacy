import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap font-mono text-sm uppercase tracking-wider border-2 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-foreground text-background border-foreground shadow-brutal hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none",
        destructive:
          "bg-destructive text-white border-destructive shadow-brutal-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]",
        outline:
          "bg-background text-foreground border-foreground hover:bg-foreground hover:text-background",
        secondary:
          "bg-muted text-foreground border-foreground hover:bg-foreground hover:text-background",
        ghost: 
          "border-transparent hover:bg-muted hover:border-foreground",
        link: 
          "text-foreground underline-offset-4 hover:underline border-transparent",
        accent:
          "bg-primary text-primary-foreground border-primary shadow-brutal-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]",
        ai:
          "bg-accent text-accent-foreground border-accent shadow-brutal-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]",
      },
      size: {
        default: "h-11 px-6 py-2",
        sm: "h-9 px-4 text-xs",
        lg: "h-14 px-10 text-base",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

const Button = React.forwardRef(({ className, variant, size, asChild = false, ...props }, ref) => {
  const Comp = asChild ? Slot : "button"
  return (
    <Comp
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      {...props} />
  );
})
Button.displayName = "Button"

export { Button, buttonVariants }
