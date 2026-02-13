"use client"

import React, { useCallback, useEffect, useRef, useState } from "react"
import type { EvidenceFile, RunHistoryItem, RunState, RunStatus, Workspace } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface InputPanelProps {
  workspace: RunState["workspace"]
  evidenceFiles: EvidenceFile[]
  status: RunStatus
  gitHub: RunState["gitHub"]
  useSample: boolean
  fastMode: boolean
  designSystemTokens: string
  workspaceId?: string | null
  onUpdateWorkspace: (updates: Partial<Workspace>) => void
  onUpdateGuardrails: (updates: Partial<Workspace["guardrails"]>) => void
  onSetEvidenceFiles: (files: EvidenceFile[]) => void
  onSetUseSample: (value: boolean) => void
  onSetFastMode: (value: boolean) => void
  onSetDesignSystemTokens: (value: string) => void
  onLoadSample: () => void
  onStartRun: () => void
  onCancelRun: () => void
  onConnectGitHub: (token: string, username: string) => void
  onDisconnectGitHub: () => void
  onLoadRunHistory?: () => Promise<RunHistoryItem[]>
  onReplayRun?: (runId: string) => Promise<void>
}

function EvidenceQualityMeter({ files }: { files: EvidenceFile[] }) {
  const hasInterviews = files.some((f) => f.type === "interview")
  const hasTickets = files.some((f) => f.type === "support_tickets")
  const hasMetrics = files.some((f) => f.type === "usage_metrics")
  const hasCompetitors = files.some((f) => f.type === "competitors")
  const hasNps = files.some((f) => f.type === "nps_comments")
  const hasChangelog = files.some((f) => f.type === "changelog")

  const required = [hasInterviews, hasTickets, hasMetrics]
  const optional = [hasCompetitors, hasNps, hasChangelog]
  const score = [...required, ...optional].filter(Boolean).length
  const total = required.length + optional.length
  const pct = Math.round((score / total) * 100)
  const widthClassByScore = ["w-0", "w-1/6", "w-2/6", "w-3/6", "w-4/6", "w-5/6", "w-full"] as const
  const meterWidthClass = widthClassByScore[Math.max(0, Math.min(score, total))]
  const allRequiredMet = required.every(Boolean)
  const missingRequired: string[] = []
  if (!hasInterviews) missingRequired.push("Interviews")
  if (!hasTickets) missingRequired.push("Support Tickets")
  if (!hasMetrics) missingRequired.push("Usage Metrics")

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">Evidence Quality</span>
        <span className="font-mono text-xs text-foreground">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={`${meterWidthClass} h-full rounded-full transition-all duration-500 ${
            allRequiredMet ? "bg-success" : pct > 30 ? "bg-warning" : "bg-destructive"
          }`}
        />
      </div>
      <div className="flex flex-wrap gap-1">
        <QualityTag label="Interviews" met={hasInterviews} required />
        <QualityTag label="Tickets" met={hasTickets} required />
        <QualityTag label="Metrics" met={hasMetrics} required />
        <QualityTag label="Competitors" met={hasCompetitors} />
        <QualityTag label="NPS" met={hasNps} />
        <QualityTag label="Changelog" met={hasChangelog} />
      </div>
      {missingRequired.length > 0 && (
        <p className="text-[10px] text-destructive">
          Missing required: {missingRequired.join(", ")}
        </p>
      )}
    </div>
  )
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || (typeof window !== "undefined" ? window.location.origin : "")

function IntegrationsSection({ disabled, workspaceId }: { disabled: boolean; workspaceId?: string | null }) {
  const [expanded, setExpanded] = useState(false)
  const [integrations, setIntegrations] = useState<Array<{ provider: string; status: string; last_sync?: string }>>([])
  const connectors = [
    { id: "gong", name: "Gong" },
    { id: "intercom", name: "Intercom" },
    { id: "linear", name: "Linear" },
    { id: "posthog", name: "PostHog" },
    { id: "slack", name: "Slack" },
  ]
  useEffect(() => {
    if (!workspaceId || !API_BASE || !expanded) return
    fetch(`${API_BASE}/integrations?workspace_id=${workspaceId}`)
      .then((r) => (r.ok ? r.json() : { integrations: [] }))
      .then((d) => setIntegrations(d.integrations || []))
      .catch(() => setIntegrations([]))
  }, [workspaceId, expanded])
  const statusByProvider = Object.fromEntries(integrations.map((i) => [i.provider, i]))
  return (
    <div className="rounded-md border border-border bg-secondary/40">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        disabled={disabled}
        className="w-full flex items-center justify-between px-3 py-2 text-left disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span className="text-xs font-medium text-foreground">Integrations</span>
        <span className="text-[10px] text-muted-foreground">
          {workspaceId ? (integrations.length ? "View status" : "Expand to load") : "Start run to configure"}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-border px-3 py-2 space-y-1">
          {connectors.map(({ id, name }) => {
            const status = statusByProvider[id]
            return (
              <div key={id} className="flex items-center justify-between text-[10px]">
                <span className="text-foreground">{name}</span>
                <Badge
                  variant="outline"
                  className={`h-5 text-[10px] ${
                    status?.status === "connected"
                      ? "border-success/30 text-success"
                      : status?.status === "configured"
                        ? "border-primary/30 text-primary"
                        : "border-muted-foreground/30 text-muted-foreground"
                  }`}
                >
                  {status?.status || "disconnected"}
                </Badge>
              </div>
            )
          })}
          <p className="text-[10px] text-muted-foreground pt-1">
            POST /integrations/{"{provider}"}/connect with workspace_id. Sync via POST /integrations/{"{provider}"}/sync.
          </p>
        </div>
      )}
    </div>
  )
}

function WorkspaceInsightsSection({ disabled, workspaceId }: { disabled: boolean; workspaceId: string }) {
  const [expanded, setExpanded] = useState(false)
  const [nightlyLoading, setNightlyLoading] = useState(false)
  const [competitorGap, setCompetitorGap] = useState<{ gaps: Array<{ feature: string; competitors: string[]; priority: string }> } | null>(null)
  const [confidenceAlerts, setConfidenceAlerts] = useState<{ alerts: Array<{ feature: string; message: string }>; count: number } | null>(null)
  useEffect(() => {
    if (!expanded || !workspaceId || !API_BASE) return
    fetch(`${API_BASE}/competitor-gap?workspace_id=${workspaceId}`)
      .then((r) => (r.ok ? r.json() : { gaps: [] }))
      .then((d) => setCompetitorGap(d))
      .catch(() => setCompetitorGap(null))
    fetch(`${API_BASE}/workspaces/${workspaceId}/confidence-alerts`)
      .then((r) => (r.ok ? r.json() : { alerts: [], count: 0 }))
      .then((d) => setConfidenceAlerts(d))
      .catch(() => setConfidenceAlerts(null))
  }, [expanded, workspaceId])
  const runNightlySynthesis = async () => {
    if (!workspaceId || !API_BASE || disabled) return
    setNightlyLoading(true)
    try {
      const res = await fetch(`${API_BASE}/workspaces/${workspaceId}/nightly-synthesis`, { method: "POST" })
      const d = await res.json()
      if (res.ok) {
        toast.success("Nightly synthesis completed", {
          description: `Claims: ${d.claims_count ?? 0}, Features: ${d.top_features_count ?? 0}`,
        })
      } else {
        toast.error("Nightly synthesis failed")
      }
    } catch {
      toast.error("Nightly synthesis failed")
    } finally {
      setNightlyLoading(false)
    }
  }
  return (
    <div className="rounded-md border border-border bg-secondary/40">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        disabled={disabled}
        className="w-full flex items-center justify-between px-3 py-2 text-left disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span className="text-xs font-medium text-foreground">Workspace insights</span>
        <span className="text-[10px] text-muted-foreground">Nightly synthesis, competitor gap, alerts</span>
      </button>
      {expanded && (
        <div className="border-t border-border px-3 py-2 space-y-3">
          <Button
            size="sm"
            variant="outline"
            className="h-7 w-full text-xs"
            onClick={runNightlySynthesis}
            disabled={disabled || nightlyLoading}
          >
            {nightlyLoading ? "Running..." : "Run Nightly Synthesis"}
          </Button>
          {competitorGap && competitorGap.gaps?.length > 0 && (
            <div>
              <span className="text-[10px] font-medium text-muted-foreground">Competitor gap</span>
              <ul className="mt-1 space-y-0.5">
                {competitorGap.gaps.slice(0, 3).map((g, i) => (
                  <li key={i} className="text-[10px]">
                    {g.feature} — {g.competitors?.join(", ")} ({g.priority})
                  </li>
                ))}
              </ul>
            </div>
          )}
          {confidenceAlerts && confidenceAlerts.count > 0 && (
            <div>
              <span className="text-[10px] font-medium text-muted-foreground">Confidence alerts</span>
              <ul className="mt-1 space-y-0.5">
                {confidenceAlerts.alerts.slice(0, 3).map((a, i) => (
                  <li key={i} className="text-[10px] text-foreground">{a.feature}: {a.message}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function QualityTag({ label, met, required }: { label: string; met: boolean; required?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${
        met
          ? "bg-success/10 text-success"
          : required
            ? "bg-destructive/10 text-destructive"
            : "bg-secondary text-muted-foreground"
      }`}
    >
      {met ? (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
          <circle cx="12" cy="12" r="10" />
        </svg>
      )}
      {label}
      {required && !met && <span className="text-destructive">*</span>}
    </span>
  )
}

function FileIcon({ type }: { type: EvidenceFile["type"] }) {
  if (type === "interview")
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    )
  if (type === "support_tickets" || type === "usage_metrics" || type === "nps_comments")
    return (
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-success">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    )
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted-foreground">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

function ForbiddenPathsInput({
  paths,
  onChange,
  disabled,
}: {
  paths: string[]
  onChange: (paths: string[]) => void
  disabled: boolean
}) {
  const [input, setInput] = useState("")

  const addPath = () => {
    const trimmed = input.trim()
    if (trimmed && !paths.includes(trimmed)) {
      onChange([...paths, trimmed])
      setInput("")
    }
  }

  const removePath = (path: string) => {
    onChange(paths.filter((p) => p !== path))
  }

  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">Forbidden Paths</Label>
      <div className="flex gap-1">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="/infra, /payments"
          disabled={disabled}
          className="h-7 bg-secondary/50 text-xs font-mono border-border flex-1"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              addPath()
            }
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addPath}
          disabled={disabled || !input.trim()}
          className="h-7 px-2 text-xs bg-transparent"
        >
          Add
        </Button>
      </div>
      {paths.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {paths.map((p) => (
            <span key={p} className="inline-flex items-center gap-1 rounded bg-destructive/10 px-1.5 py-0.5 font-mono text-[10px] text-destructive">
              {p}
              {!disabled && (
                <button
                  type="button"
                  onClick={() => removePath(p)}
                  className="hover:text-destructive/70 ml-0.5"
                  aria-label={`Remove forbidden path ${p}`}
                  title={`Remove forbidden path ${p}`}
                >
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function InputPanel({
  workspace,
  evidenceFiles,
  status,
  gitHub,
  useSample,
  fastMode,
  designSystemTokens,
  onUpdateWorkspace,
  onUpdateGuardrails,
  onSetEvidenceFiles,
  onSetUseSample,
  onSetFastMode,
  onSetDesignSystemTokens,
  onLoadSample,
  onStartRun,
  onCancelRun,
  onConnectGitHub,
  onDisconnectGitHub,
  onLoadRunHistory,
  onReplayRun,
  workspaceId,
}: InputPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)
  const [showGitHubModal, setShowGitHubModal] = useState(false)
  const [gitHubToken, setGitHubToken] = useState("")
  const [showReplayModal, setShowReplayModal] = useState(false)
  const [runHistory, setRunHistory] = useState<RunHistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const isRunning = status === "running" || status === "retrying"
  const isDisabled = isRunning || status === "completed"
  
  const handleLoadHistory = useCallback(async () => {
    if (!onLoadRunHistory) return
    setLoadingHistory(true)
    try {
      const history = await onLoadRunHistory()
      setRunHistory(history)
      setShowReplayModal(true)
    } catch (err) {
      console.error("Failed to load run history", err)
    } finally {
      setLoadingHistory(false)
    }
  }, [onLoadRunHistory])
  
  const handleReplay = useCallback(async (runId: string) => {
    if (!onReplayRun) return
    setShowReplayModal(false)
    await onReplayRun(runId)
  }, [onReplayRun])

  const handleFiles = useCallback(
    (fileList: FileList) => {
      const newFiles: EvidenceFile[] = Array.from(fileList).map((f) => {
        let type: EvidenceFile["type"] = "interview"
        if (f.name.includes("support_tickets")) type = "support_tickets"
        else if (f.name.includes("usage_metrics")) type = "usage_metrics"
        else if (f.name.includes("competitors")) type = "competitors"
        else if (f.name.includes("nps")) type = "nps_comments"
        else if (f.name.includes("changelog")) type = "changelog"

        return { name: f.name, type, size: f.size, status: "valid", file: f }
      })
      onSetEvidenceFiles([...evidenceFiles, ...newFiles])
    },
    [evidenceFiles, onSetEvidenceFiles]
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      if (e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files)
      }
    },
    [handleFiles]
  )

  const canStart =
    (useSample || evidenceFiles.length > 0) &&
    evidenceFiles.some((f) => f.type === "interview") &&
    evidenceFiles.some((f) => f.type === "support_tickets") &&
    evidenceFiles.some((f) => f.type === "usage_metrics") &&
    workspace.teamName.length > 0 &&
    status === "idle"

  return (
    <div className="flex h-full flex-col lg:border-r border-border">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Input</h2>
        <div className="flex items-center gap-2">
          {onLoadRunHistory && onReplayRun && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLoadHistory}
              disabled={isDisabled || loadingHistory}
              className="h-7 text-xs text-muted-foreground hover:text-foreground"
            >
              {loadingHistory ? "Loading..." : "Replay Run"}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onLoadSample}
            disabled={isDisabled}
            className="h-7 text-xs text-primary hover:text-primary"
          >
            Load Sample
          </Button>
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="space-y-5 p-4">
          {/* Evidence Upload */}
          <div className="space-y-3">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Evidence Bundle
            </Label>
            <div className="flex items-center justify-between rounded-md border border-border bg-secondary/40 px-3 py-2">
              <div>
                <p className="text-xs font-medium text-foreground">Use sample evidence</p>
                <p className="text-[10px] text-muted-foreground">Load curated evidence from /sample-data</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  const next = !useSample
                  onSetUseSample(next)
                  if (next) onLoadSample()
                }}
                disabled={isDisabled}
                aria-label="Toggle sample evidence"
                title="Toggle sample evidence"
                className={`relative h-6 w-11 rounded-full transition-colors ${
                  useSample ? "bg-primary" : "bg-secondary"
                }`}
              >
                <span
                  className={`absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                    useSample ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
            <div
              role="button"
              tabIndex={0}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-5 transition-colors ${
                dragOver
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-muted-foreground/50"
              } ${isDisabled || useSample ? "pointer-events-none opacity-50" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => { if (e.key === "Enter") fileInputRef.current?.click() }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mb-2 text-muted-foreground">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span className="text-xs text-muted-foreground">Drop evidence files or click</span>
              <span className="mt-0.5 text-[10px] text-muted-foreground/60">.md, .csv, .json</span>
            </div>
            <Label htmlFor="evidence-file-upload" className="sr-only">
              Upload evidence files
            </Label>
            <input
              id="evidence-file-upload"
              ref={fileInputRef}
              type="file"
              className="hidden"
              multiple
              accept=".md,.csv,.json"
              title="Upload evidence files"
              aria-label="Upload evidence files"
              onChange={(e) => {
                if (e.target.files) handleFiles(e.target.files)
              }}
            />
          </div>

          {/* Uploaded files */}
          {evidenceFiles.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">{evidenceFiles.length} files</span>
                {!isDisabled && (
                  <button
                    type="button"
                    onClick={() => onSetEvidenceFiles([])}
                    className="text-[10px] text-muted-foreground hover:text-destructive transition-colors"
                  >
                    Clear all
                  </button>
                )}
              </div>
              <div className="space-y-1">
                {evidenceFiles.map((f) => (
                  <div key={f.name} className="flex items-center gap-2 rounded-md bg-secondary/50 px-2.5 py-1.5">
                    <FileIcon type={f.type} />
                    <span className="flex-1 truncate font-mono text-xs text-foreground">{f.name}</span>
                    <Badge
                      variant="outline"
                      className={`text-[10px] px-1.5 py-0 ${
                        f.status === "valid"
                          ? "border-success/30 text-success"
                          : f.status === "invalid"
                            ? "border-destructive/30 text-destructive"
                            : "border-border text-muted-foreground"
                      }`}
                    >
                      {f.status}
                    </Badge>
                  </div>
                ))}
              </div>
              <EvidenceQualityMeter files={evidenceFiles} />
            </div>
          )}

          {/* Workspace Config */}
          <div className="space-y-3">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Workspace
            </Label>
            <div className="space-y-2">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label htmlFor="teamName" className="text-xs text-muted-foreground">Team Name</Label>
                </div>
                <Input
                  id="teamName"
                  value={workspace.teamName}
                  onChange={(e) => onUpdateWorkspace({ teamName: e.target.value })}
                  placeholder="Acme Corp"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="text-xs text-muted-foreground">GitHub Connection</Label>
                  {gitHub.connected && (
                    <Badge variant="outline" className="h-5 text-xs bg-success/10 border-success/30 text-success">
                      {gitHub.username}
                    </Badge>
                  )}
                </div>
                <Button
                  onClick={() => setShowGitHubModal(true)}
                  variant={gitHub.connected ? "secondary" : "outline"}
                  size="sm"
                  className={`w-full h-8 text-xs gap-1.5 ${
                    gitHub.connected
                      ? "bg-success/10 border-success/30 text-success hover:bg-success/20"
                      : "bg-transparent"
                  }`}
                  disabled={isDisabled}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 
.405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12Z" />
                  </svg>
                  {gitHub.connected ? "Disconnect" : "Connect with GitHub"}
                </Button>
              </div>
              <IntegrationsSection disabled={isDisabled} workspaceId={workspaceId} />
              {workspaceId && (
                <WorkspaceInsightsSection disabled={isDisabled} workspaceId={workspaceId} />
              )}
              <div>
                <Label htmlFor="repoUrl" className="text-xs text-muted-foreground">Repository URL</Label>
                <Input
                  id="repoUrl"
                  value={workspace.repoUrl}
                  onChange={(e) => onUpdateWorkspace({ repoUrl: e.target.value })}
                  placeholder="https://github.com/org/repo"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs font-mono border-border"
                />
              </div>
              <div>
                <Label htmlFor="branch" className="text-xs text-muted-foreground">Branch</Label>
                <Input
                  id="branch"
                  value={workspace.branch}
                  onChange={(e) => onUpdateWorkspace({ branch: e.target.value })}
                  placeholder="main"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs font-mono border-border"
                />
              </div>
              <div>
                <Label htmlFor="goalStatement" className="text-xs text-muted-foreground">Goal Statement (optional)</Label>
                <Input
                  id="goalStatement"
                  value={workspace.goalStatement}
                  onChange={(e) => onUpdateWorkspace({ goalStatement: e.target.value })}
                  placeholder="Improve onboarding completion"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
              <div>
                <Label htmlFor="northStar" className="text-xs text-muted-foreground">North Star Metric (optional)</Label>
                <Input
                  id="northStar"
                  value={workspace.okrConfig?.northStarMetric ?? ""}
                  onChange={(e) =>
                    onUpdateWorkspace({
                      okrConfig: {
                        okrs: workspace.okrConfig?.okrs ?? [],
                        northStarMetric: e.target.value || undefined,
                      },
                    })
                  }
                  placeholder="e.g. Weekly Active Users"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
              <div>
                <Label htmlFor="okrs" className="text-xs text-muted-foreground">OKRs (optional, comma-separated)</Label>
                <Input
                  id="okrs"
                  value={(workspace.okrConfig?.okrs ?? []).join(", ")}
                  onChange={(e) =>
                    onUpdateWorkspace({
                      okrConfig: {
                        okrs: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                        northStarMetric: workspace.okrConfig?.northStarMetric,
                      },
                    })
                  }
                  placeholder="e.g. Increase Retention 10%, Reduce Support 20%"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
              <div className="flex items-center justify-between rounded-md border border-border bg-secondary/40 px-3 py-2">
                <div>
                  <p className="text-xs font-medium text-foreground">Approval workflow</p>
                  <p className="text-[10px] text-muted-foreground">Pause before tickets for stakeholder review</p>
                </div>
                <button
                  type="button"
                  title="Toggle approval workflow"
                  aria-label={workspace.approvalWorkflowEnabled ? "Disable approval workflow" : "Enable approval workflow"}
                  onClick={() => onUpdateWorkspace({ approvalWorkflowEnabled: !(workspace.approvalWorkflowEnabled ?? false) })}
                  disabled={isDisabled}
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    workspace.approvalWorkflowEnabled ? "bg-primary" : "bg-secondary"
                  }`}
                >
                  <span
                    className={`absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                      workspace.approvalWorkflowEnabled ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
              <div>
                <Label htmlFor="designSystemTokens" className="text-xs text-muted-foreground">Design system tokens (optional)</Label>
                <Input
                  id="designSystemTokens"
                  value={designSystemTokens}
                  onChange={(e) => onSetDesignSystemTokens(e.target.value)}
                  placeholder="e.g. primary: #3b82f6, radius: 8px"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
              <div>
                <Label htmlFor="approvers" className="text-xs text-muted-foreground">Approvers (optional, comma-separated)</Label>
                <Input
                  id="approvers"
                  value={(workspace.approvers ?? []).join(", ")}
                  onChange={(e) =>
                    onUpdateWorkspace({
                      approvers: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  placeholder="e.g. design_lead, eng_lead"
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
              <div>
                <Label htmlFor="linearUrl" className="text-xs text-muted-foreground">Linear URL (optional)</Label>
                <Input
                  id="linearUrl"
                  value={workspace.linearUrl ?? ""}
                  onChange={(e) => onUpdateWorkspace({ linearUrl: e.target.value || undefined })}
                  placeholder="https://linear.app/..."
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
              <div>
                <Label htmlFor="jiraUrl" className="text-xs text-muted-foreground">Jira URL (optional)</Label>
                <Input
                  id="jiraUrl"
                  value={workspace.jiraUrl ?? ""}
                  onChange={(e) => onUpdateWorkspace({ jiraUrl: e.target.value || undefined })}
                  placeholder="https://...atlassian.net/..."
                  disabled={isDisabled}
                  className="mt-1 h-8 bg-secondary/50 text-xs border-border"
                />
              </div>
            </div>
          </div>

          {/* Guardrails */}
          <div className="space-y-3">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Guardrails
            </Label>
            <div className="space-y-2">
              <div className="flex items-center justify-between rounded-md border border-border bg-secondary/40 px-3 py-2">
                <div>
                  <p className="text-xs font-medium text-foreground">Fast mode</p>
                  <p className="text-[10px] text-muted-foreground">Skip feature selection prompt</p>
                </div>
                <button
                  type="button"
                  onClick={() => onSetFastMode(!fastMode)}
                  disabled={isDisabled}
                  aria-label="Toggle fast mode"
                  title="Toggle fast mode"
                  className={`relative h-6 w-11 rounded-full transition-colors ${
                    fastMode ? "bg-primary" : "bg-secondary"
                  }`}
                >
                  <span
                    className={`absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition-transform ${
                      fastMode ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Max Retries</Label>
                <Select
                  value={String(workspace.guardrails.maxRetries)}
                  onValueChange={(v) => onUpdateGuardrails({ maxRetries: Number(v) })}
                  disabled={isDisabled}
                >
                  <SelectTrigger className="mt-1 h-8 bg-secondary/50 text-xs border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">0 (no retries)</SelectItem>
                    <SelectItem value="1">1</SelectItem>
                    <SelectItem value="2">2 (default)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Mode</Label>
                <Select
                  value={workspace.guardrails.mode}
                  onValueChange={(v) => onUpdateGuardrails({ mode: v as "read_only" | "pr" })}
                  disabled={isDisabled}
                >
                  <SelectTrigger className="mt-1 h-8 bg-secondary/50 text-xs border-border">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="read_only">Read-only (generate diff)</SelectItem>
                    <SelectItem value="pr">PR mode (open pull request)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <ForbiddenPathsInput
                paths={workspace.guardrails.forbiddenPaths}
                onChange={(paths) => onUpdateGuardrails({ forbiddenPaths: paths })}
                disabled={isDisabled}
              />
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Action Button */}
      <div className="border-t border-border p-4">
        {isRunning ? (
          <Button
            onClick={onCancelRun}
            variant="destructive"
            className="w-full"
            size="sm"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            </svg>
            Cancel Run
          </Button>
        ) : (
          <Button
            onClick={onStartRun}
            disabled={!canStart}
            className="w-full bg-primary text-primary-foreground hover:bg-primary/90"
            size="sm"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Run Pipeline
          </Button>
        )}
      </div>

      {/* GitHub OAuth Modal */}
      {/* Replay Run Modal */}
      {showReplayModal && onReplayRun && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-96 max-h-[80vh] flex flex-col">
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-foreground">Replay Completed Run</h3>
              <p className="text-xs text-muted-foreground mt-1">Select a completed run to replay and view its artifacts.</p>
            </div>
            <ScrollArea className="flex-1 min-h-0">
              <div className="space-y-2">
                {runHistory.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">No completed runs found</p>
                ) : (
                  runHistory.map((run) => (
                    <button
                      key={run.run_id}
                      type="button"
                      onClick={() => handleReplay(run.run_id)}
                      className="w-full text-left rounded-md border border-border p-3 hover:bg-secondary transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-mono text-primary truncate">{run.run_id}</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">
                            {run.status === "completed" ? "✅ Completed" : "❌ Failed"} • Retries: {run.retry_count}/2
                          </p>
                          {run.created_at && (
                            <p className="text-[10px] text-muted-foreground/60 mt-0.5">
                              {new Date(run.created_at).toLocaleString()}
                            </p>
                          )}
                        </div>
                        <Badge variant={run.status === "completed" ? "default" : "destructive"} className="ml-2 text-[10px]">
                          {run.status}
                        </Badge>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>
            <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-border">
              <Button variant="outline" size="sm" onClick={() => setShowReplayModal(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {showGitHubModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-96 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Connect GitHub</h3>
              <p className="text-xs text-muted-foreground mt-1">Enter your GitHub personal access token to enable PR creation and code access.</p>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">GitHub Personal Access Token</Label>
              <Input
                type="password"
                value={gitHubToken}
                onChange={(e) => setGitHubToken(e.target.value)}
                placeholder="ghp_..."
                className="mt-1 h-8 text-xs font-mono"
                aria-label="GitHub personal access token"
              />
              <p className="text-xs text-muted-foreground mt-2">Token never stored; used for this session only.</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowGitHubModal(false)
                  setGitHubToken("")
                }}
                className="flex-1 h-8 text-xs bg-transparent"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  if (gitHubToken.trim()) {
                    onConnectGitHub(gitHubToken, "github-user")
                    setShowGitHubModal(false)
                    setGitHubToken("")
                  }
                }}
                disabled={!gitHubToken.trim()}
                className="flex-1 h-8 text-xs"
              >
                Connect
              </Button>
              {gitHub.connected && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    onDisconnectGitHub()
                    setShowGitHubModal(false)
                    setGitHubToken("")
                  }}
                  className="h-8 text-xs"
                >
                  Disconnect
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
