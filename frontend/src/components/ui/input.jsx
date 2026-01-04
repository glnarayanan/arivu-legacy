import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        "flex h-12 w-full bg-background px-4 py-2 border-2 border-foreground font-mono text-sm placeholder:text-muted-foreground placeholder:uppercase placeholder:tracking-wider focus:outline-none focus:shadow-brutal-sm disabled:cursor-not-allowed disabled:opacity-50 transition-shadow duration-150",
        className
      )}
      ref={ref}
      {...props} />
  );
})
Input.displayName = "Input"

export { Input }
