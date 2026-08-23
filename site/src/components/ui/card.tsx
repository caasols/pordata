import * as React from "react";

import { cn } from "@/lib/utils";

function Card({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card text-card-foreground shadow-[0_1px_2px_0_rgb(0_0_0/0.04)]",
        className,
      )}
      {...props}
    />
  );
}

export { Card };
