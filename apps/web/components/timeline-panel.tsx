"use client"

import { useEffect, useRef } from "react"
import type { Stage, LogEntry, RunStatus } from "@/lib/types"
import { ScrollArea } from "@/components/ui/scroll-area"

function StageIcon({ status }: { status: Stage["status"] }) {
  const base = "h-5 w-5 shrink-0"

  switch (status) {
    case "done":
      return (
        <div className={`${base} flex items-center justify-center rounded-full bg-success`}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--success-foreground))" strokeWidth="3">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      )
    case "running":
      return (
        <div className={`${base} flex items-center justify-center rounded-full border-2 border-primary`}>
          <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
        </div>
      )
    case "failed":
      return (
        <div className={`${base} flex items-center justify-center rounded-full bg-destructive`}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--destructive-foreground))" strokeWidth="3">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </div>
      )
    case "retry":
      return (
        <div className={`${base} flex items-center justify-center rounded-full border-2 border-warning`}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="hsl(var(--warning))" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </div>
      )
    case "skipped":
      return (
        <div className={`${base} flex items-center justify-center rounded-full border border-border`}>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted-foreground">
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </div>
      )
    default:
      return (
        <div className={`${base} flex items-center justify-center rounded-full border border-border`}>
          <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
        </div>
      )
  }
}

function StageItem({ stage, isLast }: { stage: Stage; isLast: boolean }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <StageIcon status={stage.status} />
        {!isLast && (
          <div
            className={`mt-1 w-px flex-1 ${
              stage.status === "done"
                ? "bg-success/40"
                : stage.status === "running"
                  ? "bg-primary/40"
                  : "bg-border"
            }`}
          />
        )}
      </div>
      <div className={`flex-1 pb-4 ${isLast ? "pb-0" : ""}`}>
        <div className="flex items-center gap-2">
          <span
            className={`text-sm font-medium ${
              stage.status === "running"
                ? "text-primary"
                : stage.status === "done"
                  ? "text-foreground"
                  : stage.status === "failed"
                    ? "text-destructive"
                    : stage.status === "skipped"
                      ? "text-muted-foreground/50"
                      : "text-muted-foreground"
            }`}
          >
            {stage.label}
          </span>
          {stage.status === "retry" && stage.retryIndex !== undefined && (
            <span className="rounded bg-warning/15 px-1.5 py-0.5 font-mono text-[10px] font-medium text-warning">
              Retry {stage.retryIndex}/2
            </span>
          )}
          {stage.status === "skipped" && (
            <span className="text-[10px] text-muted-foreground/50">skipped</span>
          )}
        </div>
        <p
          className={`mt-0.5 text-xs ${
            stage.status === "skipped" ? "text-muted-foreground/30" : "text-muted-foreground"
          }`}
        >
          {stage.description}
        </p>
        {stage.error && (
          <p className="mt-1 text-xs text-destructive">{stage.error}</p>
        )}
      </div>
    </div>
  )
}

function LogLine({ entry }: { entry: LogEntry }) {
  const time = new Date(entry.timestamp).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })

  const levelColors: Record<string, string> = {
    info: "text-muted-foreground",
    warn: "text-warning",
    error: "text-destructive",
    success: "text-success",
  }

  return (
    <div className="flex gap-2 px-3 py-0.5 font-mono text-[11px] leading-5 hover:bg-secondary/30">
      <span className="shrink-0 text-muted-foreground/50">{time}</span>
      <span className="shrink-0 w-20 text-primary/70 truncate">{entry.stage}</span>
      <span className={levelColors[entry.level] || "text-foreground"}>{entry.message}</span>
    </div>
  )
}

interface KeyEvent {
  icon: string
  text: string
  timestamp: string
  level: "success" | "error" | "warning" | "info"
}

function extractKeyEvents(logs: LogEntry[], stages: Stage[], retryCount: number): KeyEvent[] {
  const events: KeyEvent[] = []
  let evidenceIngested = false
  let featureChosen = false
  let prdGenerated = false
  let testsFailed = false
  let selfHealApplied = false
  let testsPassed = false
  let artifactsExported = false

  logs.forEach((log) => {
    // Evidence ingested
    if (!evidenceIngested && (log.stage === "INTAKE" || log.message.toLowerCase().includes("evidence"))) {
      evidenceIngested = true
      events.push({
        icon: "✅",
        text: "Evidence ingested",
        timestamp: log.timestamp,
        level: "success",
      })
    }

    // Feature chosen
    if (!featureChosen && (log.stage === "SELECT_FEATURE" || log.message.includes("feature_selected"))) {
      featureChosen = true
      events.push({
        icon: "✅",
        text: "Feature chosen",
        timestamp: log.timestamp,
        level: "success",
      })
    }

    // PRD generated
    if (!prdGenerated && log.stage === "GENERATE_PRD" && log.message.includes("done")) {
      prdGenerated = true
      events.push({
        icon: "✅",
        text: "PRD generated",
        timestamp: log.timestamp,
        level: "success",
      })
    }

    // Tests failed
    if (!testsFailed && log.stage === "VERIFY" && (log.level === "error" || log.message.toLowerCase().includes("fail"))) {
      testsFailed = true
      const testCount = log.message.match(/\d+/)?.[0] || ""
      events.push({
        icon: "❌",
        text: `Tests failed${testCount ? ` (${testCount})` : ""}`,
        timestamp: log.timestamp,
        level: "error",
      })
    }

    // Self-heal applied
    if (!selfHealApplied && (log.stage === "SELF_HEAL" || log.message.includes("self-heal"))) {
      selfHealApplied = true
      events.push({
        icon: "🔁",
        text: `Self-heal patch applied (retry ${retryCount}/2)`,
        timestamp: log.timestamp,
        level: "warning",
      })
    }

    // Tests passed
    if (!testsPassed && log.stage === "VERIFY" && (log.level === "success" || log.message.toLowerCase().includes("pass"))) {
      testsPassed = true
      events.push({
        icon: "✅",
        text: "Tests pass",
        timestamp: log.timestamp,
        level: "success",
      })
    }

    // Artifacts exported
    if (!artifactsExported && log.stage === "EXPORT" && log.message.includes("done")) {
      artifactsExported = true
      events.push({
        icon: "📦",
        text: "Artifact pack exported",
        timestamp: log.timestamp,
        level: "success",
      })
    }
  })

  // Also check stages for completion
  stages.forEach((stage) => {
    if (stage.status === "done" && !events.some((e) => e.text.toLowerCase().includes(stage.label.toLowerCase()))) {
      if (stage.id === "INTAKE" && !evidenceIngested) {
        events.push({
          icon: "✅",
          text: "Evidence ingested",
          timestamp: stage.completedAt || "",
          level: "success",
        })
      } else if (stage.id === "GENERATE_PRD" && !prdGenerated) {
        events.push({
          icon: "✅",
          text: "PRD generated",
          timestamp: stage.completedAt || "",
          level: "success",
        })
      } else if (stage.id === "EXPORT" && !artifactsExported) {
        events.push({
          icon: "📦",
          text: "Artifact pack exported",
          timestamp: stage.completedAt || "",
          level: "success",
        })
      }
    }
    if (stage.status === "failed" && stage.id === "VERIFY" && !testsFailed) {
      events.push({
        icon: "❌",
        text: "Tests failed",
        timestamp: stage.completedAt || "",
        level: "error",
      })
    }
    if (stage.status === "retry" && !selfHealApplied) {
      events.push({
        icon: "🔁",
        text: `Self-heal patch applied (retry ${retryCount}/2)`,
        timestamp: stage.startedAt || "",
        level: "warning",
      })
    }
  })

  return events.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
}

function KeyEventsTimeline({ events }: { events: KeyEvent[] }) {
  if (events.length === 0) return null

  const levelStyles = {
    success: "text-success",
    error: "text-destructive",
    warning: "text-warning",
    info: "text-muted-foreground",
  }

  return (
    <div className="border-b border-border bg-secondary/30 px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground uppercase tracking-wider">Key Events</span>
        <span className="font-mono text-[10px] text-muted-foreground/50">{events.length} milestones</span>
      </div>
      <div className="space-y-1.5">
        {events.map((event, i) => (
          <div key={`${event.timestamp}-${i}`} className="flex items-center gap-2 text-xs">
            <span className="shrink-0 text-base leading-none">{event.icon}</span>
            <span className={`flex-1 font-medium ${levelStyles[event.level]}`}>{event.text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

interface TimelinePanelProps {
  stages: Stage[]
  logs: LogEntry[]
  status: RunStatus
  retryCount: number
}

export function TimelinePanel({ stages, logs, status, retryCount }: TimelinePanelProps) {
  const logEndRef = useRef<HTMLDivElement>(null)
  const keyEvents = extractKeyEvents(logs, stages, retryCount)

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [logs.length])

  return (
    <div className="flex h-full flex-col lg:border-r border-border">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Pipeline</h2>
        {retryCount > 0 && (
          <span className="rounded bg-warning/15 px-2 py-0.5 font-mono text-[10px] font-medium text-warning">
            Retries: {retryCount}/2
          </span>
        )}
      </div>

      {/* Stages */}
      <div className="border-b border-border px-4 py-4">
        {stages.map((stage, i) => (
          <StageItem key={stage.id} stage={stage} isLast={i === stages.length - 1} />
        ))}
      </div>

      {/* Key Events Timeline */}
      {keyEvents.length > 0 && <KeyEventsTimeline events={keyEvents} />}

      {/* Logs */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="text-xs font-medium text-muted-foreground">Execution Log</span>
        <span className="font-mono text-[10px] text-muted-foreground/50">{logs.length} entries</span>
      </div>
      <ScrollArea className="flex-1">
        <div className="py-1">
          {logs.length === 0 && (status === "idle" || status === "pending") && (
            <div className="flex items-center justify-center py-8">
              <span className="text-xs text-muted-foreground/50">Waiting for pipeline to start...</span>
            </div>
          )}
          {logs.map((entry, i) => (
            <LogLine key={`${entry.timestamp}-${i}`} entry={entry} />
          ))}
          <div ref={logEndRef} />
        </div>
      </ScrollArea>
    </div>
  )
}
