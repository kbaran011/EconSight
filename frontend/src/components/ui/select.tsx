import * as React from "react"
import { cn } from "@/lib/utils"

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

function Select({ className, children, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </select>
  )
}

// Simple shims so existing imports of SelectTrigger / SelectContent / SelectItem / SelectValue work
function SelectTrigger({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div {...props}>{children}</div>
}
function SelectContent({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
function SelectItem({ value, children }: { value: string; children: React.ReactNode }) {
  return <option value={value}>{children}</option>
}
function SelectValue({ placeholder }: { placeholder?: string }) {
  return <span>{placeholder}</span>
}

export { Select, SelectTrigger, SelectContent, SelectItem, SelectValue }
