"use client"

import type { RunSummary } from "@/lib/types"
import { Badge } from "@/components/ui/badge"

interface RunSummaryCardProps {
  summary: RunSummary
  failureMessage: string | null
}

export function RunSummaryCard({ summary, failureMessage }: RunSummaryCardProps) {
  const isPass = summary.passFail === "pass"

  return (
    <div className={`rounded-lg border p-4 ${isPass ? "border-success/30 bg-success/5" : "border-destructive/30 bg-destructive/5"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {isPass ? (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-success">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--success-foreground))" strokeWidth="3">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
          ) : (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-destructive">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--destructive-foreground))" strokeWidth="3">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </div>
          )}
          <span className={`text-sm font-semibold ${isPass ? "text-success" : "text-destructive"}`}>
            Run {isPass ? "Passed" : "Failed"}
          </span>
        </div>
        <Badge
          variant="outline"
          className={`font-mono text-[10px] ${isPass ? "border-success/30 text-success" : "border-destructive/30 text-destructive"}`}
        >
          {summary.duration}
        </Badge>
      </div>

      {failureMessage && (
        <div className="mb-3 rounded bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {failureMessage}
          <p className="mt-1 text-[10px] text-destructive/70">
            Exported failure report and logs. Review the test report for details.
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <MetricBox label="Tests" value={`${summary.testsPassed}/${summary.testsPassed + summary.testsFailed}`} sub="passed" good={summary.testsFailed === 0} />
        <MetricBox label="Retries" value={`${summary.retriesUsed}/2`} sub="used" good={summary.retriesUsed <= 1} />
        <MetricBox label="Confidence" value={`${Math.round(summary.confidenceScore * 100)}%`} sub="score" good={summary.confidenceScore > 0.8} />
        <MetricBox label="Tickets" value={String(summary.totalTickets)} sub={`${summary.totalEstimateHours}h est.`} good />
      </div>

      {summary.filesChanged.length > 0 && (
        <div className="mt-3 space-y-1">
          <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Files Changed</span>
          <div className="space-y-0.5">
            {summary.filesChanged.map((f) => (
              <div key={f} className="flex items-center gap-1.5 rounded bg-secondary/50 px-2 py-1">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted-foreground">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span className="font-mono text-[10px] text-foreground">{f}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function MetricBox({ label, value, sub, good }: { label: string; value: string; sub: string; good: boolean }) {
  return (
    <div className="rounded border border-border bg-secondary/30 px-3 py-2">
      <span className="text-[10px] text-muted-foreground">{label}</span>
      <div className="flex items-baseline gap-1">
        <span className={`text-base font-bold ${good ? "text-foreground" : "text-warning"}`}>{value}</span>
        <span className="text-[10px] text-muted-foreground">{sub}</span>
      </div>
    </div>
  )
}
