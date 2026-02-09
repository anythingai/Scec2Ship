"use client"

import type { RunStatus } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

function StatusBadge({ status }: { status: RunStatus }) {
  const config: Record<RunStatus, { label: string; className: string }> = {
    idle: { label: "Ready", className: "bg-secondary text-secondary-foreground border-border" },
    pending: { label: "Pending", className: "bg-secondary text-secondary-foreground border-border" },
    running: { label: "Running", className: "bg-primary/15 text-primary border-primary/30" },
    retrying: { label: "Retrying", className: "bg-warning/15 text-warning border-warning/30" },
    completed: { label: "Completed", className: "bg-success/15 text-success border-success/30" },
    failed: { label: "Failed", className: "bg-destructive/15 text-destructive border-destructive/30" },
    cancelled: { label: "Cancelled", className: "bg-secondary text-muted-foreground border-border" },
  }

  const { label, className } = config[status]

  return (
    <Badge variant="outline" className={className}>
      {status === "running" && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
      )}
      {label}
    </Badge>
  )
}

interface AppHeaderProps {
  status: RunStatus
  runId: string | null
  onReset: () => void
}

export function AppHeader({ status, runId, onReset }: AppHeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-3">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-primary">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="currentColor" />
          </svg>
          <h1 className="text-base font-semibold tracking-tight text-foreground">Growpad</h1>
        </div>
        <div className="h-4 w-px bg-border" />
        <StatusBadge status={status} />
        {runId && (
          <span className="font-mono text-xs text-muted-foreground">{runId}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {(status === "completed" || status === "failed" || status === "cancelled") && (
          <Button variant="outline" size="sm" onClick={onReset} className="text-xs bg-transparent">
            New Run
          </Button>
        )}
      </div>
    </header>
  )
}
